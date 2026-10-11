"""Explicitly enabled CPU capability gate. No model, asset, DMA or Overlay."""
import argparse
import hashlib
import io
import json
import os
from pathlib import Path
import platform
import sys
import threading
import time
import traceback
import unittest

HERE = Path(__file__).resolve().parent
OUT = Path('/home/ubuntu/m373_future_wait_evidence_01')
PRIOR = '4a5b4ad459f06f0814ba7bc2b41f377718ac3828c5c311191b60eec62c82946c'

def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('manifest_sha')
    parser.add_argument('--enable-fixture-gate', action='store_true')
    args = parser.parse_args()
    if not args.enable_fixture_gate: raise RuntimeError('Disabled by default')
    if os.geteuid() != 0 or platform.system() != 'Linux': raise RuntimeError('Linux root required')
    OUT.mkdir(mode=0o700, exist_ok=False)
    started = time.monotonic()
    row = dict(status='FAIL_FUTURE_WAIT_CPU_COMPONENT', gate_level='CPU-Future-Condition-capability',
        target_build_id='0x4D333537', prior_raw_sha256=PRIOR, manifest_sha256=args.manifest_sha,
        overlay_loaded=False, real_assets_read=False, model_forward_calls=0, fpga_transactions=0,
        extra_pynq_allocations=0, ps_prefetch_enabled=False, memory_capacity_proven=False,
        numerical_pass=False, performance_pass=False, formal_promotion_allowed=False,
        platform=dict(uname=list(platform.uname()), python=sys.version, executable=sys.executable, euid=os.geteuid()),
        scope='Real Python Future/Condition and NumPy; frozen scheduler methods with explicit fake PL/parser/buffers. No model correctness or measured model wait.', errors=[])
    try:
        if sha(HERE/'PACKAGE_MANIFEST.json') != args.manifest_sha: raise RuntimeError('Manifest differs')
        manifest = json.loads((HERE/'PACKAGE_MANIFEST.json').read_text(encoding='utf-8'))
        names = set()
        for entry in manifest['files']:
            name = entry['path']
            if Path(name).name != name or name in names: raise RuntimeError('Unapproved path')
            names.add(name)
            if (HERE/name).stat().st_size != entry['bytes'] or sha(HERE/name) != entry['sha256']: raise RuntimeError('Payload differs')
        if len(names) != manifest['file_count'] or sum(x['bytes'] for x in manifest['files']) != manifest['total_bytes']: raise RuntimeError('Count/bytes differ')
        if {p.name for p in HERE.iterdir()} != names | {'PACKAGE_MANIFEST.json'}: raise RuntimeError('Unexpected package member')
        if sha(HERE/'M372_PREREQUISITE.json') != PRIOR: raise RuntimeError('Prior evidence differs')
        import m373_test_future_wait as tests
        from m372_future_wait import FutureWaitObserver
        import numpy as np
        stream = io.StringIO()
        result = unittest.TextTestRunner(stream=stream, verbosity=2).run(unittest.defaultTestLoader.loadTestsFromModule(tests))
        row.update(tests_run=result.testsRun, test_output=stream.getvalue(), numpy_version=np.__version__)
        if result.testsRun != 17 or not result.wasSuccessful(): raise RuntimeError('Capability checks failed')
        # A separate genuine blocking wait in the real trace, with no numerical fakes.
        from decode_trace import DecodeTrace
        future = tests.Future(); trace = DecodeTrace(); entered = threading.Event()
        original = future._condition.wait
        def signaled_wait(*a, **k):
            entered.set()
            return original(*a, **k)
        future._condition.wait = signaled_wait
        def complete():
            if entered.wait(3): future.set_result(17)
            else: future.set_exception(RuntimeError('No wait entered before fixture deadline'))
        worker = threading.Thread(target=complete, name='m373-fixture-completion')
        worker.start(); observer = FutureWaitObserver(trace)
        try:
            with trace.span('fixture_root'):
                value = observer.wait(future, kind='parse', chain=tests.CHAIN, token_start=0)
        finally:
            worker.join(3)
        events = trace.report()['events']
        row['blocking_probe'] = dict(value=value, records=observer.records, summary=observer.summary(),
            future_result_source_sha256=observer.future_result_source_sha256,
            condition_binding_restored=future._condition.wait is signaled_wait,
            trace_exclusive_closure_ns=sum(x['exclusive_ns'] for x in events)-events[0]['inclusive_ns'],
            trace_events=events)
        del future._condition.wait
        row['lifecycle'] = dict(active_workers=[t.name for t in threading.enumerate() if t is not threading.main_thread()])
        if row['lifecycle']['active_workers'] or value != 17 or not row['blocking_probe']['condition_binding_restored']: raise RuntimeError('Lifecycle/binding not closed')
        summary = row['blocking_probe']['summary']['parse']
        if summary['condition_wait_calls'] != 1 or not 0 < summary['condition_wait_s'] <= summary['result_wall_s']: raise RuntimeError('Actual wait not observed')
        if row['blocking_probe']['trace_exclusive_closure_ns'] != 0: raise RuntimeError('Trace closure failed')
        if time.monotonic()-started > 20: raise RuntimeError('20-second budget exceeded')
        row['status'] = 'PASS_FUTURE_WAIT_CPU_COMPONENT_ONLY'
    except BaseException as exc:
        row['errors'].append(type(exc).__name__+': '+str(exc)); row['traceback'] = traceback.format_exc()
    row.update(elapsed_s=time.monotonic()-started, gate_return_code=1 if row['errors'] else 0)
    raw = (json.dumps(row, ensure_ascii=True, indent=2)+'\n').encode('utf-8')
    part = OUT/'BOARD_RESULT.part'
    with part.open('wb') as f: f.write(raw); f.flush(); os.fsync(f.fileno())
    os.replace(part, OUT/'BOARD_RESULT.json')
    print('M373_COMPONENT_RESULT status='+row['status'], flush=True)
    return row['gate_return_code']

if __name__ == '__main__': raise SystemExit(main())
