"""New direct-scatter candidate versus the exact accepted parser, CPU only.

Saved actual M441 RTL packets are used, without rerunning a passed FPGA case.
Synthetic edge cases are explicitly separate from the saved actual outputs.
"""
from __future__ import annotations
import ast
import hashlib
import json
import platform
import re
import statistics
import time
from pathlib import Path
import numpy as np
from m442_output_parser03 import parse_into_and_check
from m441_host_io08 import atomic

ROOT = Path(__file__).resolve().parents[2]
BASE = ROOT / 'deployment/mage_vl4b/optimization_v1'
RUN = BASE / 'runs/M442-direct-output-parser-offline-03'
STABLE = ROOT / 'deployment/mage_vl4b/m242_m241_fixed_text_board_candidate'
SOURCE_SHA = {'m231_prefill_runtime.py': 'e7d6aa5a43919405168612b6a5695c14330735f75c87aa269b245e61542750ad',
              'm236_prefill_runtime.py': 'd8061b561fe4d2a089523fde0d3860684244e76bca9646f255f03134fb50be56'}


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def baseline():
    namespace = {'np': np}
    for filename, wanted in SOURCE_SHA.items():
        raw = (STABLE / filename).read_bytes()
        assert digest(raw) == wanted
        tree = ast.parse(raw)
        if filename.startswith('m231'):
            node = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == '_half_values_strided')
        else:
            cls = next(n for n in tree.body if isinstance(n, ast.ClassDef) and n.name == 'M236PrefillRuntime')
            node = next(n for n in cls.body if isinstance(n, ast.FunctionDef) and n.name == '_parse_into_and_check')
            node.decorator_list = []
        exec(compile(ast.Module(body=[node], type_ignores=[]), str(STABLE / filename), 'exec'), namespace)
    return namespace['_parse_into_and_check']


def targets(chain, strided=False):
    widths = {}
    for d in chain['descriptors']:
        name = d.get('module', 'lm_head')
        widths[name] = max(widths.get(name, 0), d['row_start'] + d['valid_rows'])
    # Sentinel rows/columns prove exact writes. Column-strided final storage
    # exercises the view contract independently of contiguous family outputs.
    return {n: np.full((39, (w + 7) * (2 if strided else 1)), np.float32(-123.25), dtype=np.float32)[:, ::2 if strided else 1]
            for n, w in widths.items()}


def compare(reference, chain, payload, shift, count, strided=False):
    a, b = targets(chain, strided), targets(chain, strided)
    before = digest(payload)
    with np.errstate(all='ignore'):
        finite_a = reference(chain, payload, a, 3, count, shift)
        finite_b = parse_into_and_check(chain, payload, b, 3, count, shift)
    assert finite_a == finite_b, (shift, count, 'finite')
    assert all(a[k].tobytes() == b[k].tobytes() for k in a), (shift, count, 'bits')
    assert digest(payload) == before, 'DMA bytes modified'
    # A DMA owner can subsequently overwrite a finished packet, but never while
    # its parser Future is active. Returned target data must remain independent.
    if isinstance(payload, bytearray):
        saved = {k: v.tobytes() for k, v in b.items()}
        original = payload[:]
        payload[:] = b'\xff' * len(payload)
        assert all(v.tobytes() == saved[k] for k, v in b.items())
        payload[:] = original
    return bool(finite_a)


def actual_packets():
    prep = json.loads((BASE / 'runs/M441-W2-W4-simulation-coverage-21/PREPARATION.json').read_bytes())
    out = []
    for name in ('q', 'gate_up', 'mlp_down'):
        case = next(x for x in prep['cases'] if x['name'] == name)
        if name == 'mlp_down':
            result = BASE / 'runs/M441-W2-W4-simulation-recovery-23/mlp_down_RESULT.json'
        else:
            result = BASE / f'runs/M441-W2-W4-simulation-coverage-21/{name}_RESULT.json'
        record = json.loads(result.read_bytes())
        assert record['full_real_numerical'] and all(record['checks'].values())
        evidence = next(x for x in record['evidence'] if x['path'].endswith('autotvout_rx_V_data_V.dat'))
        path = ROOT / evidence['path']
        raw = path.read_bytes()
        assert digest(raw) == evidence['sha256']
        text = raw.decode('utf-8-sig')
        assert text.count('[[transaction]]') == text.count('[[/transaction]]') == 1
        words = re.findall(r'(?m)^\s*(0x[0-9a-fA-F]+|[0-9]+)\s*$', text)
        payload = b''.join(int(w, 16 if w.startswith('0x') else 10).to_bytes(8, 'little') for w in words)
        assert digest(payload) == record['output_sha256']
        assert len(payload) == case['chain']['output_bytes']
        out.append((name, case['chain'], payload, dict(result=result.relative_to(ROOT).as_posix(),
                    result_sha256=digest(result.read_bytes()), source=evidence,
                    payload_sha256=digest(payload))))
    return out


def synthetic(rows, valid, bits=None):
    width = 4 * rows
    payload = bytearray(32 * width * 4)
    lanes = np.ndarray((32 * width,), dtype='<u2', buffer=payload, strides=(4,))
    if bits is None:
        lanes[:] = np.arange(lanes.size, dtype=np.uint16) % 0x7c00
    else:
        lanes[:] = np.resize(bits, lanes.size)
    chain = dict(output_bytes=len(payload), descriptors=[dict(rows_per_shard=rows,
                 output_bytes=len(payload), valid_rows=valid, module='fixture', row_start=5)])
    return chain, payload


def main():
    if (RUN / 'RESULT.json').exists():
        raise RuntimeError('Existing attempt; inspect saved bytes, do not rerun')
    RUN.mkdir(parents=True, exist_ok=True)
    reference = baseline()
    candidate_path = Path(__file__).with_name('m442_output_parser03.py')
    packets = actual_packets()
    comparisons = []
    for name, chain, payload, identity in packets:
        for shift in range(11):
            for count in (1, 31, 32):
                assert compare(reference, chain, payload, shift, count)
                comparisons.append([name, shift, count])
    # All 65,536 half bit patterns, including NaN payloads, +/-Inf and signed
    # zero. Compare full target bytes and the finite return; no tolerance.
    chain, payload = synthetic(512, 2048, np.arange(65536, dtype=np.uint16))
    for shift in range(11):
        assert compare(reference, chain, payload, shift, 32) is False
    edge_count = 0
    for valid in (1, 7, 8, 9, 31, 32, 33, 127, 128):
        chain, payload = synthetic(32, valid)
        for shift in (0, 4, 10):
            for count in (1, 31, 32):
                assert compare(reference, chain, payload, shift, count, strided=True)
                edge_count += 1
    # False -> retry -> overwrite identical final slice, as the existing owner
    # resolves its parser Future before another writer reuses the DMA buffer.
    chain, bad = synthetic(32, 128, np.array([0x7c00], dtype=np.uint16))
    _, good = synthetic(32, 128)
    a, b = targets(chain), targets(chain)
    with np.errstate(all='ignore'):
        assert reference(chain, bad, a, 3, 31, 4) is False
        assert parse_into_and_check(chain, bad, b, 3, 31, 4) is False
        assert reference(chain, good, a, 3, 31, 3) is True
        assert parse_into_and_check(chain, good, b, 3, 31, 3) is True
    assert a['fixture'].tobytes() == b['fixture'].tobytes()
    rejected = []
    for label, mutation in (
        ('wrong_size', lambda c, p, t: c.update(output_bytes=len(p) - 8)),
        ('invalid_rows', lambda c, p, t: c['descriptors'][0].update(rows_per_shard=7)),
        ('overrun', lambda c, p, t: c['descriptors'][0].update(valid_rows=129)),
        ('small_target', lambda c, p, t: t.update(fixture=np.empty((2, 128), np.float32))),
        ('DMA_alias', lambda c, p, t: t.update(fixture=np.frombuffer(p, np.float32).reshape(32, 128))),
    ):
        c, p = synthetic(32, 128)
        t = targets(c)
        mutation(c, p, t)
        saved = {k: v.tobytes() for k, v in t.items()}
        try:
            parse_into_and_check(c, p, t, 0, 32, 4)
        except (ValueError, RuntimeError):
            assert all(v.tobytes() == saved[k] for k, v in t.items())
            rejected.append(label)
        else:
            raise AssertionError(label + ' accepted')
    timings = []
    for name, chain, payload, identity in packets:
        a, b = targets(chain), targets(chain)
        for _ in range(3):
            reference(chain, payload, a, 3, 32, 4)
            parse_into_and_check(chain, payload, b, 3, 32, 4)
        times = [[], []]
        for i in range(20):
            for mode in ((0, 1) if i % 2 == 0 else (1, 0)):
                start = time.perf_counter_ns()
                (reference if mode == 0 else parse_into_and_check)(chain, payload, a if mode == 0 else b, 3, 32, 4)
                times[mode].append((time.perf_counter_ns() - start) / 1e6)
        timings.append(dict(name=name, baseline_ms=times[0], candidate_ms=times[1],
                            baseline_median_ms=statistics.median(times[0]),
                            candidate_median_ms=statistics.median(times[1]),
                            speedup=statistics.median(times[0])/statistics.median(times[1])))
    result = dict(status='PASS_OFFLINE_DIRECT_OUTPUT_PARSER', board=False, complete_request_speedup_proven=False,
                  platform=platform.platform(), numpy=np.__version__, candidate_sha256=digest(candidate_path.read_bytes()),
                  baseline_source_sha256=SOURCE_SHA, actual_packets=[p[3] for p in packets],
                  actual_comparisons=len(comparisons), exhaustive_all_half_bits_shifts=11,
                  partial_strided_sentinel_comparisons=edge_count, retry_bit_exact=True,
                  payload_unmodified_and_reuse_independent=True, rejected=rejected,
                  full_FP32_intermediate_arrays=0, timings=timings)
    atomic(RUN / 'RESULT.json', (json.dumps(result, indent=2) + '\n').encode(), immutable=True)
    print(json.dumps({k:v for k,v in result.items() if k not in ('timings','actual_packets')}, indent=2))
    print(json.dumps([{k:v for k,v in t.items() if not isinstance(v,list)} for t in timings], indent=2))


if __name__ == '__main__':
    main()
