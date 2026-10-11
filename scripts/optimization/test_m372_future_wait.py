"""CPU tests with real Futures and frozen scheduler methods; fake PL/buffers."""
import ast
import importlib.util
from collections import defaultdict
from concurrent.futures import Future, CancelledError
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
import threading
import time
from types import SimpleNamespace
import unittest
import weakref

import numpy as np
from m372_future_wait import FutureWaitObserver, observe_runtime, instrument

ROOT = Path(__file__).resolve().parents[2]
FROZEN = ROOT / 'release_staging/kv260-mage-vl-4b-prebuilt-install-20260926-v7/deployment/mage_vl4b/m242_m241_fixed_text_board_candidate'
CHAIN = dict(chain_index=4, layer=0, family='probe', groups=1)


class Trace:
    def __init__(self):
        self.events = []
    @contextmanager
    def span(self, name, **metadata):
        self.events.append(name)
        yield


def frozen_method(filename, classname, method, namespace):
    path = FROZEN / filename
    node = next(n for c in ast.parse(path.read_text(encoding='utf-8')).body
                if isinstance(c, ast.ClassDef) and c.name == classname
                for n in c.body if isinstance(n, ast.FunctionDef) and n.name == method)
    exec(compile(ast.Module(body=[node], type_ignores=[]), str(path), 'exec'), namespace)
    return namespace[method]


@dataclass
class Pending:
    future: Future
    values: object
    output_buffer: object
    token_start: int
    token_count: int
    initial_shift: int
    attempted_shifts: list


env = dict(np=np, time=time, ThreadPoolExecutor=__import__('concurrent.futures', fromlist=['ThreadPoolExecutor']).ThreadPoolExecutor,
           _PendingBlock=Pending, _output_widths=lambda chain: {'probe':64}, base=SimpleNamespace(MIN_ACTIVATION_SCALE_SHIFT=0))
FAMILY = frozen_method('m238_prefill_runtime.py', 'M238PrefillRuntime', 'language_family_many', env)
RESOLVE = frozen_method('m236_prefill_runtime.py', 'M236PrefillRuntime', '_resolve_pending', env)


class Harness:
    language_family_many = FAMILY
    _resolve_pending = RESOLVE
    def __init__(self, *, retry=False, fail_parse=False):
        self.weight_mode = 'staged-low-cma'
        self.language_layout = object()
        self.output_buffer = np.empty((32,64), np.float32)
        self.output_buffer_alt = np.empty((32,64), np.float32)
        self.family_stage_count = defaultdict(int)
        self.family_output_allocations = defaultdict(int)
        self.family_t32_blocks = defaultdict(int)
        self.family_phase_ms = defaultdict(lambda: defaultdict(float))
        self.phase_ms = defaultdict(float)
        self.phase_calls = defaultdict(int)
        self.pack_prefetch_submissions = self.pack_prefetch_wait_ms = self.pack_prefetch_compute_ms = 0
        self.pipeline_reuse_waits = self.pipeline_submissions = self.pipeline_retry_launches = 0
        self.fused_nonfinite_detections = self.scale_retry_count = 0
        self.scale_attempts = []
        self.accepted = []
        self.retry, self.fail_parse = retry, fail_parse
        self.stages = 0
    def _language_chain(self, *args): return CHAIN
    def _family_key(self, chain): return 'probe'
    def _stage(self, *args):
        self.stages += 1
        return ['fake-weight-bank']*4, 0
    def _initial_scale_shift(self, values): return 1
    def _prepare_block(self, chain, values, start, words, shift):
        return SimpleNamespace(values=values, token_start=start, token_count=len(values), initial_shift=shift, pack_ms=0.0)
    def _launch_prepacked(self, chain, prepared, buffers, output):
        output[:prepared.token_count] = prepared.values + 2
    def _launch_once(self, chain, values, buffers, output, words, shift):
        output[:len(values)] = values + 2
    def _parse_buffer(self, chain, output, targets, start, count, shift):
        if self.fail_parse: raise ValueError('explicit fake parser failure')
        if self.retry and start == 0 and shift == 1: return False
        targets['probe'][start:start+count] = output[:count]
        return True
    def _accept_shift(self, chain, values, initial, attempted, selected):
        self.accepted.append((len(values), tuple(attempted), selected))


class Tests(unittest.TestCase):
    def make(self): return FutureWaitObserver(Trace())
    def call(self, observer, future):
        return observer.wait(future, kind='parse', chain=CHAIN, token_start=0)
    def test_ready_identity_and_no_condition_wait(self):
        f=Future(); payload=object(); f.set_result(payload); o=self.make()
        self.assertIs(self.call(o,f),payload)
        self.assertEqual(o.summary()['parse']['condition_wait_calls'],0)
        self.assertNotIn('wait',vars(f._condition))
    def test_real_condition_wait_and_wakeup(self):
        f=Future(); entered=threading.Event(); original=f._condition.wait
        def original_with_signal(*args,**kwargs):
            entered.set(); return original(*args,**kwargs)
        f._condition.wait=original_with_signal
        def worker():
            if entered.wait(3): f.set_result(17)
            else: f.set_exception(RuntimeError('Test did not enter condition wait'))
        t=threading.Thread(target=worker); t.start(); o=self.make()
        self.assertEqual(self.call(o,f),17); t.join(3); self.assertFalse(t.is_alive())
        row=o.records[0]; self.assertEqual(row['condition_wait_calls'],1)
        self.assertGreater(row['condition_wait_ns'],0)
        self.assertLessEqual(row['condition_wait_ns'],row['result_wall_ns'])
        self.assertIs(f._condition.wait,original_with_signal)
    def test_not_ready_precheck_is_not_wait_proof(self):
        f=Future()
        def races_to_completion(): f.set_result(3); return False
        f.done=races_to_completion; o=self.make()
        self.assertEqual(self.call(o,f),3)
        self.assertFalse(o.records[0]['ready_before'])
        self.assertEqual(o.records[0]['condition_wait_calls'],0)
    def test_future_exception_preserved_and_restored(self):
        f=Future(); exc=ValueError('original'); f.set_exception(exc); o=self.make()
        with self.assertRaises(ValueError) as c: self.call(o,f)
        self.assertIs(c.exception,exc); self.assertNotIn('wait',vars(f._condition))
        self.assertFalse(o.active); self.assertEqual(o.summary()['parse']['exceptions'],1)
    def test_cancelled_future_preserved(self):
        f=Future(); f.cancel(); o=self.make()
        with self.assertRaises(CancelledError): self.call(o,f)
        self.assertNotIn('wait',vars(f._condition))
    def test_condition_exception_preserves_owned_binding(self):
        f=Future(); o=self.make()
        def fail(*args,**kwargs): raise InterruptedError('explicit wait interruption')
        f._condition.wait=fail
        with self.assertRaises(InterruptedError): self.call(o,f)
        self.assertIs(f._condition.wait,fail); self.assertFalse(o.active)
    def test_bound_fail_closed(self):
        o=FutureWaitObserver(Trace(),max_results=1); f=Future(); f.set_result(1)
        self.call(o,f)
        with self.assertRaises(RuntimeError): self.call(o,f)
        self.assertNotIn('wait',vars(f._condition))
    def test_unknown_future_rejected(self):
        class Other(Future): pass
        with self.assertRaises(RuntimeError): self.call(self.make(),Other())
    def test_source_drift_rejected(self):
        with self.assertRaises(RuntimeError): instrument(FAMILY,'language_family_many',self.make(),source='def language_family_many(): pass')
    def test_disabled_before_patch(self):
        h=Harness()
        with self.assertRaises(ValueError):
            with observe_runtime(h,Trace()): pass
        self.assertNotIn('language_family_many',vars(h))
    def test_actual_frozen_scheduler_159_output_and_binding(self):
        x=np.arange(159*64,dtype=np.float32).reshape(159,64)
        a=Harness(); expected=a.language_family_many(0,'probe',x)
        b=Harness()
        with observe_runtime(b,Trace(),enabled=True) as o: actual=b.language_family_many(0,'probe',x)
        np.testing.assert_array_equal(actual['probe'],expected['probe'])
        self.assertEqual(o.summary()['pack']['calls'],5)
        self.assertEqual(o.summary()['parse']['calls'],5)
        self.assertEqual(b.pipeline_reuse_waits,3)
        self.assertEqual(b.accepted,a.accepted); self.assertEqual(b.stages,1)
        self.assertNotIn('language_family_many',vars(b)); self.assertNotIn('_resolve_pending',vars(b))
    def test_actual_frozen_retry_order_and_same_output(self):
        x=np.ones((159,64),np.float32)
        a=Harness(retry=True); expected=a.language_family_many(0,'probe',x)
        b=Harness(retry=True)
        with observe_runtime(b,Trace(),enabled=True) as o: actual=b.language_family_many(0,'probe',x)
        np.testing.assert_array_equal(actual['probe'],expected['probe'])
        self.assertEqual(b.accepted,a.accepted); self.assertEqual(b.pipeline_retry_launches,1)
        self.assertEqual(b.stages,1); self.assertEqual(o.summary()['parse']['calls'],5)
    def test_actual_parser_failure_no_hooks_left(self):
        h=Harness(fail_parse=True)
        with self.assertRaisesRegex(ValueError,'fake parser'):
            with observe_runtime(h,Trace(),enabled=True): h.language_family_many(0,'probe',np.ones((33,64),np.float32))
        self.assertNotIn('language_family_many',vars(h)); self.assertNotIn('_resolve_pending',vars(h))
    def test_owned_runtime_methods_restored_by_identity(self):
        h=Harness(); first=h.language_family_many; second=h._resolve_pending
        h.language_family_many=first; h._resolve_pending=second
        with observe_runtime(h,Trace(),enabled=True): pass
        self.assertIs(h.language_family_many,first); self.assertIs(h._resolve_pending,second)
    def test_second_source_rejected_before_first_mutation(self):
        h=Harness(); h._resolve_pending=lambda *args:None
        with self.assertRaises(RuntimeError):
            with observe_runtime(h,Trace(),enabled=True): pass
        self.assertNotIn('language_family_many',vars(h))
    def test_no_payload_or_future_retained_by_records(self):
        class Payload: pass
        payload=Payload(); ref=weakref.ref(payload); f=Future(); f.set_result(payload); o=self.make()
        self.call(o,f); del f,payload
        self.assertIsNone(ref())
    def test_actual_pinned_trace_exclusive_closure(self):
        path=ROOT/'deployment/mage_vl4b/optimization_v1/candidates/M371-candidate-prefill-profile-01/decode_trace.py'
        spec=importlib.util.spec_from_file_location('m372_test_pinned_trace',path)
        module=importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
        trace=module.DecodeTrace(); f=Future(); f.set_result(True); observer=FutureWaitObserver(trace)
        with trace.span('prefill_call'): self.call(observer,f)
        rows=trace.report()['events']; root=rows[0]
        self.assertEqual(sum(x['exclusive_ns'] for x in rows),root['inclusive_ns'])
        self.assertEqual(observer.summary()['parse']['condition_wait_calls'],0)


if __name__ == '__main__': unittest.main()
