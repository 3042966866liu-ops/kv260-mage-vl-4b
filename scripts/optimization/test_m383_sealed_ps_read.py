"""New adapter only: real fixture reads/bytearrays, explicit DMA/memory doubles."""
import os,tempfile,unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
from test_ps_read_ahead import Buffer,SAFE
from test_m382_ps_slot import memory
from m383_sealed_ps_read import SealedPSReadSession
from m382_ps_slot import RetainedSlotError
from ps_read_ahead import PSReadAheadSession,RESERVE
import ps_read_ahead as original
class Tests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.root=Path(self.temp.name)
        for i in range(4):(self.root/f'weights{i}.bin').write_bytes(bytes(range(128)))
        self.layout=SimpleNamespace(root=self.root,manifest=dict(files=[dict(path=f'weights{i}.bin',bytes=128) for i in range(4)]))
        self.plan=[(self.layout,dict(offset=0,size=64,descriptors=[0]))]
        self.runtime=SimpleNamespace(weight_mode='staged-low-cma',staged_buffers=[Buffer(128) for i in range(4)],maximum_weight_window_bytes=128,kernel=None,dma=None,stage_bytes=0,stage_ms=0,_stage=lambda *a:'original')
        self.base=SimpleNamespace(chain_window=lambda l,c:(c['offset']//16,c['size']),transaction_snapshot=lambda *a:dict(SAFE))
        self.current=memory();self.counts={'success':7};self.resident=True
        self.policy=SimpleNamespace(sealed=True,snapshot=lambda:self.current,counters=lambda:dict(self.counts))
        if os.name=='nt':
            strict=original.file_identity;self.adapter=patch.object(original,'file_identity',lambda s:strict(s)[:4]+strict(s)[5:]);self.adapter.start();self.addCleanup(self.adapter.stop)
        self.addCleanup(self.temp.cleanup)
    def make(self,**kw):
        args=dict(enabled=True,policy=self.policy,resident=lambda:self.resident,completed_transaction_snapshot=SAFE)
        args.update(kw);return SealedPSReadSession(self.runtime,self.base,self.plan,**args)
    def test_default_disabled(self):
        with self.assertRaisesRegex(ValueError,'disabled'):self.make(enabled=False)
    def test_original_guard_still_rejects_actual_low_cma(self):
        self.assertEqual(RESERVE,64<<20)
        with self.assertRaises(MemoryError):PSReadAheadSession(self.runtime,self.base,self.plan,enabled=True,memory_reader=lambda:dict(CmaFree=0,MemAvailable=1<<30),completed_transaction_snapshot=SAFE)
    def test_seal_required(self):
        self.policy.sealed=False
        with self.assertRaises(ValueError):self.make()
    def test_actual_read_copy_and_owner_release(self):
        before=self.runtime._stage;s=self.make()
        with s:s.stage(*self.plan[0])
        report=s.report();self.assertIs(self.runtime._stage,before)
        self.assertTrue(all(bytes(b.array[:64])==bytes(range(64)) and b.syncs==1 for b in self.runtime.staged_buffers))
        self.assertEqual(report['slot_release']['released_ports'],4)
        self.assertTrue(report['slot_release']['all_owner_weakrefs_dead'])
        self.assertFalse(report['independent_memory_checks'][0]['decision']['production64MiB_would_admit'])
        self.assertFalse(hasattr(self.runtime,'_m351_ps_owner'))
    def test_actual_counts_changed_rejected(self):
        s=self.make();self.counts['success']=8
        with self.assertRaises(RuntimeError):s._memory()
    def test_capacity_growth_rejected(self):
        s=self.make();self.current=memory(rss=165<<20)
        with self.assertRaises(MemoryError):s._memory()
    def test_resident_loss_rejected(self):
        s=self.make();self.resident=False
        with self.assertRaises(RuntimeError):s._memory()
    def test_external_slot_alias_retained(self):
        s=self.make();s.__enter__();s.stage(*self.plan[0]);alias=s.slot[0]
        with self.assertRaises(RetainedSlotError):s.close()
        self.assertTrue(s.slot_owners);del alias;s.close();self.assertEqual(s.report()['slot_release']['released_ports'],4)
if __name__=='__main__':unittest.main()
