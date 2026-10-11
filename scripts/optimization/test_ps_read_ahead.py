"""Real fixture I/O; explicit fake buffers/MMIO/memory, never PL evidence."""
import ast
import os
from io import BytesIO
from concurrent.futures import Future
from pathlib import Path
import tempfile
from threading import Event
import time
from types import SimpleNamespace
import unittest
from unittest.mock import patch

import numpy as np
import ps_read_ahead as component
from ps_read_ahead import PSReadAheadSession, RetainedPSResourcesError, read_exact_into, RESERVE

ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / 'deployment/mage_vl4b/m175_m120_fixed_text_candidate/runtime/board_runtime.py'
FIXTURE_PARENT = None
SAFE = dict(ap_ctrl=4, mm2s_dmasr=4098, s2mm_dmasr=4098)

class Buffer:
    def __init__(self, size):
        self.array = np.zeros(size, np.uint8)
        self.syncs = self.writes = 0
        self.on_sync = self.on_copy = None
    def __len__(self): return len(self.array)
    def __setitem__(self, key, value):
        if self.on_copy: self.on_copy()
        self.array[key] = value
        self.writes += 1
    def sync_to_device(self):
        if self.on_sync: self.on_sync()
        self.syncs += 1
    def freebuffer(self): raise AssertionError('Component must not free original bank')

class ClassRuntime:
    def _stage(self, *args): return 'class-original'

class PSReadAheadTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # CPython/Windows lstat and fstat expose different ctime semantics.
        # This explicit test-only adapter keeps the production Linux identity
        # check unchanged. Actual Linux executes all seven fields on board.
        if os.name == 'nt':
            strict = component.file_identity
            adapter = patch.object(component, 'file_identity', lambda s: strict(s)[:4] + strict(s)[5:])
            adapter.start()
            cls.addClassCleanup(adapter.stop)
        text = SOURCE.read_text(encoding='utf-8')
        node = next(n for n in ast.parse(text).body if isinstance(n, ast.FunctionDef) and n.name == 'copy_window_to_buffer')
        namespace = {'np': np, 'Path': Path}
        exec(ast.get_source_segment(text, node), namespace)
        cls.original_copy = staticmethod(namespace['copy_window_to_buffer'])

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(dir=FIXTURE_PARENT)
        self.layout = SimpleNamespace(root=Path(self.temp.name), manifest={'files': []})
        for port in range(4):
            name = 'weights' + str(port) + '.bin'
            (self.layout.root / name).write_bytes(bytes((i+port)%256 for i in range(1024)))
            self.layout.manifest['files'].append(dict(path=name, bytes=1024))
        self.plan = [(self.layout, dict(offset=i*32, size=(i+1)*32, descriptors=[i])) for i in range(3)]
        self.runtime = SimpleNamespace(weight_mode='staged-low-cma', staged_buffers=[Buffer(128) for _ in range(4)],
            maximum_weight_window_bytes=128, kernel=None, dma=None, stage_bytes=0, stage_ms=0.0,
            _stage=lambda *args: ('original', 0), allocate=lambda *args, **kwargs: self.fail('Additional CMA allocation called'))
        self.active = False
        self.memory = {'CmaFree': RESERVE+1024, 'MemAvailable': RESERVE+1024}
        self.base = SimpleNamespace(chain_window=lambda layout,c:(c['offset']//16,c['size']),
            transaction_snapshot=lambda *args: dict(SAFE) if not self.active else dict(SAFE, mm2s_dmasr=0))
        self.sessions, self.permits = [], []

    def tearDown(self):
        self.active = False
        self.memory = {'CmaFree': 1 << 30, 'MemAvailable': 1 << 30}
        for permit in self.permits: permit.set()
        for session in self.sessions:
            if session.future is not None:
                try: session.future.result(timeout=5)
                except BaseException: pass
            session.close()
            self.assertTrue(session.closed)
            self.assertEqual(session.record['open_files'], 0)
            self.assertEqual(session.record['live_views'], 0)
            self.assertEqual(session.slot, [])
        self.assertFalse(hasattr(self.runtime, '_m351_ps_owner'))
        self.temp.cleanup()

    def make(self, **kw):
        args = dict(enabled=True, memory_reader=lambda:dict(self.memory), completed_transaction_snapshot=SAFE)
        args.update(kw)
        s = PSReadAheadSession(self.runtime,self.base,self.plan,**args)
        self.sessions.append(s)
        return s

    def entered(self, **kw):
        s=self.make(**kw);s.__enter__();return s

    def test_disabled_before_any_access(self):
        with self.assertRaisesRegex(ValueError,'disabled'): PSReadAheadSession(None,None,None)

    def test_fresh_dma_zero_is_rejected(self):
        with self.assertRaisesRegex(ValueError,'Completed'):
            self.make(completed_transaction_snapshot=dict(SAFE,mm2s_dmasr=0))

    def test_memory_precheck_rejects(self):
        self.memory['MemAvailable']=RESERVE+511
        with self.assertRaises(MemoryError): self.make()
        self.memory['MemAvailable']=1<<30;self.memory['CmaFree']=RESERVE-1
        with self.assertRaises(MemoryError): self.make()

    def test_invalid_geometry_and_shard_order(self):
        self.runtime.maximum_weight_window_bytes=6963201
        with self.assertRaises(ValueError): self.make()
        self.runtime.maximum_weight_window_bytes=128
        self.layout.manifest['files'].reverse()
        with self.assertRaisesRegex(ValueError,'order'): self.make()

    def test_exact_original_copy_single_bank_accounting(self):
        original=self.runtime._stage
        with self.make() as s:
            for layout,c in self.plan:
                buffers,words=s.stage(layout,c)
                self.assertIs(buffers,self.runtime.staged_buffers)
                self.assertEqual(words,c['offset']//16)
                for port,b in enumerate(buffers):
                    expected=Buffer(128)
                    self.original_copy(layout.root/f'weights{port}.bin',c['offset'],c['size'],expected)
                    self.assertEqual(b.array[:c['size']].tobytes(),expected.array[:c['size']].tobytes())
            self.assertEqual(s.record['extra_cma_allocation_calls'],0)
            self.assertEqual(s.record['ps_payload_bytes'],512)
        self.assertIs(self.runtime._stage,original)
        self.assertEqual(self.runtime.stage_bytes,4*(32+64+96))
        self.assertTrue(all(b.syncs==3 for b in self.runtime.staged_buffers))

    def test_worker_does_not_touch_active_bank_or_retry_weights(self):
        ready,permit=Event(),Event();self.permits.append(permit)
        s=self.make(); real=s._read
        def controlled(index):
            if index==1:
                ready.set()
                if not permit.wait(5): raise RuntimeError('Test release missing')
            return real(index)
        s._read=controlled;s.__enter__();s.stage(*self.plan[0])
        self.assertTrue(ready.wait(3))
        before=[b.array.copy() for b in self.runtime.staged_buffers]
        self.active=True;permit.set();s.future.result(timeout=3)
        # Simulated multiple T32/retry consumers all retain the original bank.
        for unused in range(3):
            for b,old in zip(self.runtime.staged_buffers,before): self.assertEqual(b.array.tobytes(),old.tobytes())
        self.active=False;s.stage(*self.plan[1]);s.stage(*self.plan[2]);s.close()

    def test_next_read_only_after_all_four_syncs(self):
        s=self.make();real=s._read;observed=[]
        def checked(index):
            if index: observed.append(tuple(b.syncs for b in self.runtime.staged_buffers))
            return real(index)
        s._read=checked
        with s:
            for item in self.plan: s.stage(*item)
        self.assertEqual(observed,[(1,1,1,1),(2,2,2,2)])

    def test_busy_device_retains_until_explicit_recovery(self):
        s=self.entered();self.active=True
        with self.assertRaises(RetainedPSResourcesError): s.stage(*self.plan[0])
        with self.assertRaises(RetainedPSResourcesError): s.close()
        self.assertIs(self.runtime._m351_ps_owner,s)
        self.assertEqual(len(s.slot),4)
        self.assertFalse(s.closed)
        self.active=False;s.close()

    def test_unexpected_plan_has_no_fallback(self):
        s=self.entered()
        with self.assertRaisesRegex(RuntimeError,'unexpected'): s.stage(self.layout,dict(self.plan[0][1],size=16))
        self.assertEqual(s.record['stages'],0)
        self.assertTrue(all(b.writes==0 for b in self.runtime.staged_buffers))
        with self.assertRaises(RuntimeError): s.stage(*self.plan[0])

    def test_file_identity_change_before_read(self):
        s=self.make();(self.layout.root/'weights0.bin').write_bytes(b'changed')
        s.__enter__()
        with self.assertRaisesRegex(RuntimeError,'identity'): s.stage(*self.plan[0])

    def test_file_identity_change_after_ready(self):
        s=self.entered();s.future.result(timeout=3)
        (self.layout.root/'weights1.bin').write_bytes(b'changed')
        with self.assertRaisesRegex(RuntimeError,'before copy'): s.stage(*self.plan[0])
        self.assertTrue(all(b.writes==0 for b in self.runtime.staged_buffers))

    def test_file_identity_change_during_read(self):
        real=component.read_exact_into
        def changed(stream,*args,**kwargs):
            result=real(stream,*args,**kwargs)
            (self.layout.root/'weights0.bin').write_bytes(b'changed')
            return result
        with patch.object(component,'read_exact_into',side_effect=changed):
            s=self.entered()
            with self.assertRaisesRegex(RuntimeError,'during read'):s.stage(*self.plan[0])

    def test_worker_identity_corruption_rejected(self):
        s=self.entered();done=s.future.result(timeout=3)
        replacement=Future();replacement.set_result(dict(done,index=99));s.future=replacement
        with self.assertRaisesRegex(RuntimeError,'mismatch'):s.stage(*self.plan[0])
        self.assertTrue(all(b.writes==0 for b in self.runtime.staged_buffers))

    def test_memory_postallocation_rejects_and_releases_slot(self):
        counts=[0]
        def memory_reader():
            counts[0]+=1
            return dict(CmaFree=RESERVE if counts[0]<3 else 0,MemAvailable=1<<30)
        s=self.make(memory_reader=memory_reader)
        with self.assertRaises(MemoryError):s.__enter__()
        self.assertTrue(s.closed);self.assertEqual(s.slot,[])

    def test_manifest_size_and_regular_file_rejected(self):
        self.layout.manifest['files'][0]['bytes']=1025
        with self.assertRaisesRegex(ValueError,'identity'):self.make()
        self.layout.manifest['files'][0]['bytes']=1024
        p=self.layout.root/'weights0.bin';p.unlink();p.mkdir()
        with self.assertRaisesRegex(ValueError,'identity'):self.make()

    def test_memory_rechecked_before_copy(self):
        s=self.entered();s.future.result(timeout=3);self.memory['CmaFree']=0
        with self.assertRaises(MemoryError): s.stage(*self.plan[0])
        self.assertTrue(all(b.writes==0 for b in self.runtime.staged_buffers))

    def test_copy_failure_prevents_next_submission(self):
        s=self.entered()
        def fail(): raise OSError('copy error')
        self.runtime.staged_buffers[1].on_copy=fail
        with self.assertRaisesRegex(OSError,'copy'): s.stage(*self.plan[0])
        self.assertEqual(s.record['submissions'],1);self.assertEqual(self.runtime.stage_bytes,0)
        self.assertEqual(self.runtime.staged_buffers[2].writes,0)

    def test_sync_failure_prevents_next_submission(self):
        s=self.entered()
        def fail(): raise OSError('sync error')
        self.runtime.staged_buffers[2].on_sync=fail
        with self.assertRaisesRegex(OSError,'sync'): s.stage(*self.plan[0])
        self.assertEqual(s.record['submissions'],1);self.assertEqual(s.index,0)

    def test_worker_timeout_retains_resources(self):
        ready,permit=Event(),Event();self.permits.append(permit)
        s=self.make(timeout_s=.02);real=s._read
        def blocked(index):
            ready.set()
            if not permit.wait(5): raise RuntimeError('Test release missing')
            return real(index)
        s._read=blocked;s.__enter__();self.assertTrue(ready.wait(3))
        with self.assertRaises(RetainedPSResourcesError): s.stage(*self.plan[0])
        with self.assertRaises(RetainedPSResourcesError): s.close()
        self.assertEqual(len(s.slot),4);self.assertIs(self.runtime._m351_ps_owner,s)
        permit.set();s.future.result(timeout=3);s.close()

    def test_completed_worker_error_closes_files_and_views(self):
        with patch.object(component,'read_exact_into',side_effect=OSError('read error')):
            s=self.entered()
            with self.assertRaisesRegex(OSError,'read error'): s.stage(*self.plan[0])
        s.close();self.assertEqual(s.record['open_files'],0);self.assertEqual(s.record['live_views'],0)

    def test_incomplete_plan_rejected_and_method_restored(self):
        old=self.runtime._stage
        with self.assertRaisesRegex(RuntimeError,'complete'):
            with self.make() as s: s.stage(*self.plan[0])
        self.assertIs(self.runtime._stage,old)

    def test_class_method_binding_restored(self):
        saved=self.runtime
        self.runtime=ClassRuntime();vars(self.runtime).update({k:v for k,v in vars(saved).items() if k!='_stage'})
        with self.make() as s:
            for item in self.plan:s.stage(*item)
        self.assertNotIn('_stage',vars(self.runtime));self.assertEqual(self.runtime._stage(),'class-original')

    def test_maximum_real_window_and_nonzero_offset(self):
        size=6963200
        for port,row in enumerate(self.layout.manifest['files']):
            page=bytes((i+port)%256 for i in range(256))*16
            with (self.layout.root/row['path']).open('wb',buffering=0) as f:
                remain=size+16
                while remain:
                    chunk=page[:min(len(page),remain)];f.write(chunk);remain-=len(chunk)
            row['bytes']=size+16
        self.runtime.maximum_weight_window_bytes=size
        self.runtime.staged_buffers=[Buffer(size) for unused in range(4)]
        self.memory={'CmaFree':1<<30,'MemAvailable':1<<30}
        self.plan=[(self.layout,dict(offset=16,size=size,descriptors=[0]))]
        with self.make() as s:
            buffers,words=s.stage(*self.plan[0]);self.assertEqual(words,1)
            self.assertEqual(sum(len(v) for v in s.slot),27852800)
            for port,b in enumerate(buffers):
                expected=Buffer(size)
                self.original_copy(self.layout.root/f'weights{port}.bin',16,size,expected)
                self.assertEqual(b.array.tobytes(),expected.array.tobytes())

    def test_invalid_timeout_and_window_bounds(self):
        for value in (0,float('nan'),float('inf')):
            with self.assertRaises(ValueError): self.make(timeout_s=value)
        self.plan=[(self.layout,dict(offset=1024,size=16))]
        with self.assertRaises(ValueError): self.make()

class ReadLoopTests(unittest.TestCase):
    def run_read(self, stream, size=9):
        slot=bytearray(size);view=memoryview(slot)
        try: row=read_exact_into(stream,view,2,deadline=time.monotonic()+3)
        finally: view.release()
        return slot,row

    def test_positive_short_reads_continue(self):
        class Short(BytesIO):
            def readinto(self, view):
                part=view[:min(2,len(view))]
                try:return super().readinto(part)
                finally:part.release()
        slot,row=self.run_read(Short(bytes(range(20))))
        self.assertEqual(slot,bytes(range(2,11)));self.assertEqual(row['read_calls'],5)

    def test_eof_and_invalid_progress_rejected(self):
        with self.assertRaises(RuntimeError):self.run_read(BytesIO(b'ab'))
        for count in (None,-1,10,True):
            class Bad(BytesIO):
                def readinto(self, view):return count
            with self.assertRaises(RuntimeError):self.run_read(Bad(bytes(range(20))))

    def test_eintr_recovers_and_is_bounded(self):
        class Interrupt(BytesIO):
            attempts=0
            def readinto(self,view):
                self.attempts+=1
                if self.attempts<=2:raise InterruptedError()
                return super().readinto(view)
        slot,row=self.run_read(Interrupt(bytes(range(20))))
        self.assertEqual(row['interruptions'],2);self.assertEqual(slot,bytes(range(2,11)))
        class Forever(BytesIO):
            def readinto(self,view):raise InterruptedError()
        with self.assertRaisesRegex(RuntimeError,'EINTR'):self.run_read(Forever())

    def test_deadline_and_io_error_propagate(self):
        v=memoryview(bytearray(4))
        try:
            with self.assertRaises(TimeoutError):read_exact_into(BytesIO(b'1234'),v,0,deadline=0)
            class Fail(BytesIO):
                def readinto(self,view):raise OSError('I/O failure')
            with self.assertRaises(OSError):self.run_read(Fail())
        finally:v.release()

if __name__=='__main__':unittest.main(verbosity=2)
