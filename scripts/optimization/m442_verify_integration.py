"""CPU-only tests of the actual frozen M238 scheduling/finite retry methods.

DMA/model/packing are explicit test fixtures, never board evidence. Numerical
packets come from saved actual M441 RTL output bytes, not reference answers.
The accepted scheduling methods run unchanged, with two fixture output owners
and one real parser worker. No runtime constructor or PL library is imported.
"""
from __future__ import annotations
import ast
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor
import copy
from dataclasses import dataclass
import gzip
import hashlib
import json
from pathlib import Path
import platform
import statistics
import sys
import threading
import time
import types
import numpy as np
from m442_output_parser05 import parse_into_and_check
from m442_runtime_adapter import make_candidate_runtime_class
import m442_verify_parser05 as verification


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def load_methods(directory):
    """Compile exact source classes, replacing imports/constructors only."""
    module = types.ModuleType("m442_actual_source_fixture")
    module.__file__ = str(directory / "m238_prefill_runtime.py")
    sys.modules[module.__name__] = module
    ns = module.__dict__
    ns.update(np=np, time=time, ThreadPoolExecutor=ThreadPoolExecutor,
              dataclass=dataclass, Future=object, base=types.SimpleNamespace(MIN_ACTIVATION_SCALE_SHIFT=0))
    ns['M231PrefillRuntime'] = type('M231PrefillRuntime', (), {})
    identities = {}
    for filename in ('m231_prefill_runtime.py', 'm236_prefill_runtime.py', 'm238_prefill_runtime.py'):
        path = directory / filename
        raw = path.read_bytes()
        identities[filename] = digest(raw)
        tree = ast.parse(raw)
        body = []
        for node in tree.body:
            if filename.startswith('m231') and isinstance(node, ast.FunctionDef) and node.name in ('_half_values_strided', '_output_widths'):
                body.append(node)
            elif filename.startswith(('m236', 'm238')) and isinstance(node, ast.ClassDef):
                node.body = [n for n in node.body if not isinstance(n, ast.FunctionDef) or n.name not in ('__init__', 'evidence')]
                body.append(node)
        exec(compile(ast.Module(body=body, type_ignores=[]), str(path), 'exec'), ns)
    return ns, identities


def target_widths(chain):
    widths = {}
    for d in chain['descriptors']:
        name = d.get('module', 'lm_head')
        widths[name] = max(widths.get(name, 0), d['row_start'] + d['valid_rows'])
    return widths


def pipeline(ns, cls, chain, payload, retry):
    """Actual M238 + M236 methods, fake only pack/transaction/construct."""
    instance = object.__new__(cls)
    instance.output_buffer = bytearray(len(payload))
    instance.output_buffer_alt = bytearray(len(payload))
    instance.language_buffers = []
    instance.weight_mode = 'fixture-only'
    instance.phase_ms = defaultdict(float)
    instance.phase_calls = defaultdict(int)
    instance.family_phase_ms = defaultdict(lambda: defaultdict(float))
    for key in ('family_output_allocations', 'family_t32_blocks', 'scale_shift_counts'):
        setattr(instance, key, defaultdict(int))
    for key in ('pack_prefetch_submissions', 'pack_prefetch_wait_ms', 'pack_prefetch_compute_ms',
                'pipeline_reuse_waits', 'pipeline_submissions', 'pipeline_retry_launches',
                'fused_nonfinite_detections', 'logical_calls', 'logical_expected_macros', 'scale_retry_count'):
        setattr(instance, key, 0)
    instance.scale_attempts = []
    local_chain = dict(chain, groups=1, chain_index=0, expected_macros=1, family='fixture')
    instance._language_chain = lambda *args: local_chain
    instance._family_key = lambda chain: 'fixture'
    instance._initial_scale_shift = lambda values: 4
    instance._record_phase = lambda *args: None
    lock = threading.Lock()
    active = set()
    maximum_active = [0]
    active_workers = set()
    maximum_workers = [0]
    launches = []
    original_parse = instance._parse_buffer

    def parse(*args):
        output = args[1]
        with lock:
            assert id(output) not in active
            active.add(id(output))
            maximum_active[0] = max(maximum_active[0], len(active))
            if threading.current_thread() is not threading.main_thread():
                active_workers.add(threading.get_ident())
                maximum_workers[0] = max(maximum_workers[0], len(active_workers))
        try:
            time.sleep(.002)  # Exercise actual Future ownership across reuse.
            return original_parse(*args)
        finally:
            with lock:
                active.remove(id(output))
                active_workers.discard(threading.get_ident())

    def launch(chain, prepared, buffers, output):
        with lock:
            assert id(output) not in active, 'DMA owner overwritten before parser completion'
        output[:] = payload
        if retry:
            # Overflow a written lane, not a structural NaN/padding location.
            np.ndarray((1,), dtype='<u2', buffer=output)[0] = 0x7c00
        launches.append(('initial', prepared.token_start, prepared.initial_shift))

    def relaunch(chain, values, buffers, output, words, shift):
        with lock:
            assert id(output) not in active, 'Retry overlapped existing parser'
        output[:] = payload
        launches.append(('retry', int(values[0, 0]), shift))

    instance._parse_buffer = parse
    instance._launch_prepacked = launch
    instance._launch_once = relaunch
    ns['base'].pack_chain_input = lambda *args, **kwargs: b'fixture-only-input-not-hardware'
    values = np.zeros((159, 64), np.float32)
    values[:, 0] = np.arange(159)
    output = instance.language_family_many(0, 'fixture', values)
    assert not active and not active_workers and maximum_workers[0] == 1
    # The accepted scheduler can retry in the foreground while its single
    # parser worker handles the other DMA buffer. Preserve that contract.
    assert maximum_active[0] <= (2 if retry else 1)
    assert instance.pipeline_submissions == 5 and instance.pack_prefetch_submissions == 5
    assert instance.pipeline_reuse_waits == 3 and instance.logical_calls == 5
    assert instance.pipeline_retry_launches == (5 if retry else 0)
    assert instance.scale_retry_count == (5 if retry else 0)
    assert [x['selected_shift'] for x in instance.scale_attempts] == [3 if retry else 4] * 5
    return output, dict(launches=launches, parser_workers=maximum_workers[0],
                       t32_blocks=5, tail_tokens=31, reuse_waits=3,
                       retries=instance.pipeline_retry_launches,
                       allocations=dict(instance.family_output_allocations))


def run(directory):
    started = time.perf_counter()
    plan = json.loads((directory / 'PLAN.json').read_bytes())
    ns, sources = load_methods(directory)
    assert sources == plan['baseline_sources']
    accepted = ns['M238PrefillRuntime']
    old_parser = accepted._parse_into_and_check
    candidate = make_candidate_runtime_class(accepted)
    assert accepted._parse_into_and_check is old_parser
    assert candidate.language_family_many is accepted.language_family_many
    assert candidate._resolve_pending is accepted._resolve_pending
    assert candidate._parse_into_and_check is parse_into_and_check
    comparisons = 0
    edge_checks = 0
    timings = []
    pipeline_checks = []
    packets = []
    for entry in plan['actual_packets']:
        payload = gzip.decompress((directory / entry['payload']).read_bytes())
        assert len(payload) == entry['chain']['output_bytes']
        assert digest(payload) == entry['identity']['payload_sha256']
        packets.append((entry, payload))
        for shift in range(11):
            for count in (1, 31, 32):
                assert verification.compare(old_parser, entry['chain'], payload, shift, count)
                comparisons += 1
        for retry in (False, True):
            a, a_stats = pipeline(ns, accepted, entry['chain'], payload, retry)
            b, b_stats = pipeline(ns, candidate, entry['chain'], payload, retry)
            assert a_stats == b_stats
            assert all(a[name].tobytes() == b[name].tobytes() for name in a)
            pipeline_checks.append(dict(name=entry['name'], retry=retry, **b_stats))
    chain, payload = verification.synthetic(512, 2048, np.arange(65536, dtype=np.uint16))
    for shift in range(11):
        assert verification.compare(old_parser, chain, payload, shift, 32) is False
    for valid in (1, 7, 8, 9, 31, 32, 33, 127, 128):
        chain, payload = verification.synthetic(32, valid)
        for shift in (0, 4, 10):
            for count in (1, 31, 32):
                assert verification.compare(old_parser, chain, payload, shift, count, strided=True)
                edge_checks += 1
    # Actual family-sized targets; block 128 has a 31-token tail. Balanced
    # fixed pairs, no sample deletion, no changing count after observing data.
    for entry, payload in packets:
        chain = entry['chain']
        for count in (32, 31):
            begin = 0 if count == 32 else 128
            outputs = [{n: np.full((159, w), np.nan, dtype=np.float32) for n, w in target_widths(chain).items()} for _ in range(2)]
            functions = (old_parser, parse_into_and_check)
            for _ in range(3):
                for mode in range(2):
                    assert functions[mode](chain, payload, outputs[mode], begin, count, 4)
            times = [[], []]
            for pair in range(20):
                for mode in ((0, 1) if pair % 2 == 0 else (1, 0)):
                    t = time.perf_counter_ns()
                    assert functions[mode](chain, payload, outputs[mode], begin, count, 4)
                    times[mode].append((time.perf_counter_ns() - t) / 1e6)
            assert all(outputs[0][n].tobytes() == outputs[1][n].tobytes() for n in outputs[0])
            timings.append(dict(name=entry['name'], tokens=count, baseline_ms=times[0], candidate_ms=times[1],
                                baseline_median_ms=statistics.median(times[0]), candidate_median_ms=statistics.median(times[1]),
                                speedup=statistics.median(times[0]) / statistics.median(times[1])))
    return dict(status='PASS_OFFLINE_M442_PARSER_AND_ACTUAL_SCHEDULER',
                evidence_scope='CPU numerical parsing plus actual scheduler with explicit fake hardware/packing',
                board=False, full_request_speedup_proven=False,
                platform=platform.platform(), numpy=np.__version__, elapsed_s=time.perf_counter()-started,
                actual_packet_comparisons=comparisons, all_fp16_bits_shifts=11, partial_strided_checks=edge_checks,
                baseline_sources=sources, candidate_sha256=digest((directory/'m442_output_parser05.py').read_bytes()),
                accepted_class_unmodified=True, inherited_scheduling_unmodified=True,
                pipeline_checks=pipeline_checks, timings=timings,
                driver_and_math_changed=False, full_fp32_intermediate_arrays=0,
                lm_head_and_vision_parser_changed=False)


if __name__ == '__main__':
    from m441_host_io08 import atomic
    directory = Path(sys.argv[1]).resolve()
    output = Path(sys.argv[2]).resolve()
    if output.exists():
        raise RuntimeError('Existing integration attempt; inspect only')
    result = run(directory)
    atomic(output, (json.dumps(result, indent=2)+'\n').encode(), immutable=True)
    print(json.dumps(dict(status=result['status'], seconds=result['elapsed_s'], pipeline_cases=len(result['pipeline_checks']),
                         timings=[{k:v for k,v in t.items() if not isinstance(v,list)} for t in result['timings']]), indent=2))
