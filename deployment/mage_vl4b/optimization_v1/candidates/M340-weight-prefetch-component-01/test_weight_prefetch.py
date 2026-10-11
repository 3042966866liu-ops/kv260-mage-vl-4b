import ast
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import tempfile
from threading import Event
from types import SimpleNamespace
import unittest

import numpy as np
from weight_prefetch import WeightPrefetchSession, RetainedBuffersError

ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / 'deployment/mage_vl4b/m175_m120_fixed_text_candidate/runtime/board_runtime.py'


class Buffer:
    def __init__(self, size):
        self.array = np.zeros(size, np.uint8)
        self.syncs = 0
        self.freed = False
    def __setitem__(self, key, value):
        if self.freed: raise RuntimeError('Write after free')
        self.array[key] = value
    def sync_to_device(self): self.syncs += 1
    def freebuffer(self): self.freed = True


class PrefetchTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        text = SOURCE.read_text(encoding='utf-8')
        tree = ast.parse(text)
        node = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == 'copy_window_to_buffer')
        ns = {'np': np, 'Path': Path}
        exec(ast.get_source_segment(text, node), ns)
        cls.copy = staticmethod(ns['copy_window_to_buffer'])

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.layout = SimpleNamespace(root=Path(self.temp.name), manifest={'files': [{'path':f'weights{i}.bin'} for i in range(4)]})
        for i in range(4): (self.layout.root/f'weights{i}.bin').write_bytes(bytes((n+i)%256 for n in range(512)))
        self.plan = [(self.layout, dict(offset=i*32, size=(i+1)*32, descriptors=[i])) for i in range(3)]
        self.runtime = SimpleNamespace(weight_mode='staged-low-cma', staged_buffers=[Buffer(128) for _ in range(4)],
            maximum_weight_window_bytes=128, allocate=lambda shape, dtype: Buffer(shape[0]),
            kernel=None, dma=None, stage_bytes=0, stage_ms=0.0, _stage=lambda *a: ('original',0))
        self.active = False
        self.base = SimpleNamespace(LOW_END=1 << 31, physical_address=lambda b: 0x100000,
            copy_window_to_buffer=self.copy, chain_window=lambda layout,c:(c['offset']//16,c['size']),
            transaction_snapshot=lambda *a: dict(ap_ctrl=0 if self.active else 4,mm2s_dmasr=0 if self.active else 2,s2mm_dmasr=2))

    def make(self, **kwargs): return WeightPrefetchSession(self.runtime,self.base,self.plan,cma_free_bytes=512+(64<<20),**kwargs)

    def test_exact_staging_reuse_sync_and_accounting(self):
        original = self.runtime._stage
        session = self.make()
        with session:
            identities = []
            for layout, chain in self.plan:
                buffers, words = self.runtime._stage(layout,chain)
                identities.append(id(buffers))
                for i,b in enumerate(buffers):
                    expected = Buffer(128)
                    self.copy(layout.root/f'weights{i}.bin',chain['offset'],chain['size'],expected)
                    np.testing.assert_array_equal(b.array[:chain['size']],expected.array[:chain['size']])
                    self.assertGreaterEqual(b.syncs,1)
                self.assertEqual(words,chain['offset']//16)
            self.assertEqual(identities[0],identities[2])
            self.assertNotEqual(identities[0],identities[1])
        self.assertIs(self.runtime._stage, original)
        self.assertEqual(self.runtime.stage_bytes, 4*(32+64+96))
        self.assertEqual(session.record['stages'],3)
        self.assertFalse(any(b.freed for b in self.runtime.staged_buffers))

    def test_background_owns_other_bank_only(self):
        ready, permit = Event(), Event()
        self.addCleanup(permit.set)
        real = self.base.copy_window_to_buffer
        def controlled(path, offset, size, buffer):
            if offset == 32:
                ready.set()
                if not permit.wait(3): raise RuntimeError('Test worker not released')
            return real(path,offset,size,buffer)
        self.base.copy_window_to_buffer=controlled
        with self.make() as session:
            banks,_ = session.stage(*self.plan[0])
            before=[b.array.copy() for b in banks]
            self.assertTrue(ready.wait(3))
            self.active=True
            for b, saved in zip(banks,before): np.testing.assert_array_equal(b.array,saved)
            with self.assertRaises(RetainedBuffersError): session.stage(*self.plan[1])
            self.active=False
            permit.set()
            session.stage(*self.plan[1]);session.stage(*self.plan[2])

    def test_unexpected_chain_stops_and_restores(self):
        original=self.runtime._stage
        with self.assertRaisesRegex(RuntimeError,'Unexpected chain'):
            with self.make(): self.runtime._stage(self.layout,dict(self.plan[0][1],size=16))
        self.assertIs(self.runtime._stage,original)

    def test_short_read_propagates_no_silent_fallback(self):
        (self.layout.root/'weights0.bin').write_bytes(b'')
        with self.assertRaisesRegex(RuntimeError,'short staged'):
            with self.make() as session: session.stage(*self.plan[0])

    def test_memory_failure_precedes_allocation(self):
        self.runtime.allocate=lambda *a,**kw: self.fail('Allocation reached')
        with self.assertRaises(MemoryError): WeightPrefetchSession(self.runtime,self.base,self.plan,cma_free_bytes=0)

    def test_partial_allocation_is_freed(self):
        owned=[]
        def allocate(shape,dtype):
            if len(owned)==2: raise MemoryError('simulated allocation failure')
            owned.append(Buffer(shape[0]));return owned[-1]
        self.runtime.allocate=allocate
        with self.assertRaises(MemoryError):
            with self.make(): pass
        self.assertTrue(all(b.freed for b in owned))

    def test_dma_failure_retains_owned_bank(self):
        session=self.make();session.__enter__()
        owned=list(session.extra)
        self.active=True
        with self.assertRaises(RetainedBuffersError): session.close()
        self.assertFalse(any(b.freed for b in owned))
        self.assertFalse(session.closed)
        self.active=False;session.close()
        self.assertTrue(all(b.freed for b in owned))

    def test_incomplete_plan_fails(self):
        with self.assertRaisesRegex(RuntimeError,'complete frozen plan'):
            with self.make() as session: session.stage(*self.plan[0])

    def test_worker_timeout_retains_until_worker_stops(self):
        permit=Event();started=Event();self.addCleanup(permit.set)
        real=self.base.copy_window_to_buffer
        def blocked(*args):
            started.set()
            if not permit.wait(3): raise RuntimeError('Test release missing')
            return real(*args)
        self.base.copy_window_to_buffer=blocked
        session=self.make(timeout_s=0.01);session.__enter__()
        self.assertTrue(started.wait(3))
        owned=list(session.extra)
        with self.assertRaises(RetainedBuffersError): session.stage(*self.plan[0])
        with self.assertRaises(RetainedBuffersError): session.close()
        self.assertFalse(any(b.freed for b in owned))
        permit.set();session.future.result(timeout=3);session.close()
        self.assertTrue(all(b.freed for b in owned))

    def test_real_maximum_window_bytes(self):
        size=6963200
        block=bytes(range(256))*(size//256)+bytes(range(size%256))
        for i in range(4): (self.layout.root/f'weights{i}.bin').write_bytes(block)
        self.runtime.maximum_weight_window_bytes=size
        self.runtime.staged_buffers=[Buffer(size) for _ in range(4)]
        plan=[(self.layout,dict(offset=0,size=size,descriptors=[0])),
              (self.layout,dict(offset=16,size=size-16,descriptors=[1]))]
        with WeightPrefetchSession(self.runtime,self.base,plan,cma_free_bytes=4*size+(64<<20)) as session:
            for layout,chain in plan:
                buffers,_=session.stage(layout,chain)
                for buffer in buffers:
                    self.assertEqual(buffer.array[:chain['size']].tobytes(),block[chain['offset']:chain['offset']+chain['size']])
        self.assertEqual(self.runtime.stage_bytes,4*(2*size-16))


if __name__=='__main__': unittest.main()
