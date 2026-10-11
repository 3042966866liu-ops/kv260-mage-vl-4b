"""Real bytearrays/weakrefs, explicit memory and runtime identity test doubles."""
import copy
import unittest
import weakref
from m382_ps_slot import (assess, run_probe, release, SlotOwner, RetainedSlotError,
                          PORT_BYTES, SLOT_BYTES)


def memory(rss=100<<20, available=200<<20, cma=0):
    return dict(process_bytes=dict(VmRSS=rss, VmHWM=rss),
                system_bytes=dict(CmaFree=cma, MemAvailable=available))


class Tests(unittest.TestCase):
    def probe(self, **kwargs):
        owners=[]; evidence={}; counters=lambda:{'area:success':7,'area:fail':0}
        runtime_identity=lambda:True
        run_probe(owners,evidence,lambda:memory(),counters,lambda name:memory(),
                  runtime_identity,settle_s=0,page_bytes=4096,**kwargs)
        return owners,evidence

    def test_real_maximum_slot_touch_release_and_runtime_residency(self):
        owners,e=self.probe()
        self.assertFalse(owners)
        self.assertEqual(sum(x['bytes'] for x in e['ports']),SLOT_BYTES)
        self.assertTrue(all(x['readback'] and x['last_byte_touched'] for x in e['ports']))
        self.assertTrue(e['release']['all_owner_weakrefs_dead'])
        self.assertEqual(e['release']['released_ports'],4)
        self.assertTrue(e['observer_stopped'] and e['objects_released'])
        self.assertTrue(e['load_only_slot_pass'])
        self.assertFalse(e['checkpoints'][0]['decision']['production64MiB_would_admit'])

    def test_zero_cma_is_not_faked_into_production_admission(self):
        r=assess(memory(),100<<20,{'success':7},{'success':7})
        self.assertEqual(r['cma_free_bytes'],0)
        self.assertFalse(r['production64MiB_would_admit'])

    def test_insufficient_remaining_budget_rejected(self):
        with self.assertRaises(MemoryError):
            assess(memory(available=127<<20),100<<20,{'success':7},{'success':7})

    def test_excessive_growth_rejected(self):
        with self.assertRaises(MemoryError):
            assess(memory(rss=165<<20),100<<20,{'success':7},{'success':7})

    def test_unknown_global_cma_change_rejected(self):
        with self.assertRaises(RuntimeError):
            assess(memory(),100<<20,{'success':8},{'success':7})

    def test_invalid_statistics_rejected(self):
        r=memory();r['system_bytes']['CmaFree']=-1
        with self.assertRaises(ValueError):assess(r,100<<20,{'success':7},{'success':7})

    def test_partial_allocation_failure_releases_owned_ports(self):
        owners=[];e={};calls=[0]
        def allocate(size):
            calls[0]+=1
            if calls[0]==3:raise MemoryError('deliberate third allocation failure')
            return bytearray(size)
        with self.assertRaisesRegex(MemoryError,'deliberate'):
            run_probe(owners,e,lambda:memory(),lambda:{'success':7},lambda n:memory(),
                      lambda:True,allocator=allocate,settle_s=0,page_bytes=4096)
        self.assertFalse(owners);self.assertTrue(e['objects_released'])
        self.assertEqual(e['release']['released_ports'],2)

    def test_touch_exception_traceback_retains_owned_port(self):
        owners=[];e={}
        def failed_touch(*args):raise RuntimeError('deliberate readback failure')
        with self.assertRaisesRegex(RetainedSlotError,'external alias'):
            run_probe(owners,e,lambda:memory(),lambda:{'success':7},lambda n:memory(),
                      lambda:True,touch_fn=failed_touch,settle_s=0,page_bytes=4096)
        self.assertEqual(len(owners),1)
        self.assertFalse(e['objects_released'])
        self.assertEqual(e['original_error'],'deliberate readback failure')
        self.assertTrue(e['observer_stopped'])
        self.assertNotIn('load_only_slot_pass',e)

    def test_external_bytearray_alias_retains_slot(self):
        owners=[SlotOwner(bytearray(16))];refs=[weakref.ref(owners[0])]
        alias=owners[0].data
        with self.assertRaises(RetainedSlotError):release(owners,refs)
        self.assertTrue(owners and refs[0]() is not None)
        del alias;self.assertEqual(release(owners,refs)['released_ports'],1)

    def test_external_owner_alias_retains_slot(self):
        owners=[SlotOwner(bytearray(16))];refs=[weakref.ref(owners[0])];alias=owners[0]
        with self.assertRaises(RetainedSlotError):release(owners,refs)
        del alias;self.assertTrue(release(owners,refs)['all_owner_weakrefs_dead'])

    def test_runtime_identity_failure_refuses_allocation(self):
        owners=[];e={};allocations=[]
        def allocate(size):allocations.append(size);return bytearray(size)
        with self.assertRaisesRegex(RuntimeError,'[Rr]untime'):
            run_probe(owners,e,lambda:memory(),lambda:{'success':7},lambda n:memory(),
                      lambda:False,allocator=allocate,settle_s=0,page_bytes=4096)
        self.assertFalse(allocations)


if __name__=='__main__':unittest.main()
