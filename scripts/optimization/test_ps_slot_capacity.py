import unittest
from ps_slot_capacity import (eligibility, require_capacity, CapacityRejected, materialize_slot,
                              never_submitted_release, PORT_BYTES, SLOT_BYTES, RESERVE_BYTES)


class CapacityTests(unittest.TestCase):
    def mem(self, cma=RESERVE_BYTES, available=RESERVE_BYTES+SLOT_BYTES):
        return {'system_bytes':dict(CmaFree=cma,MemAvailable=available)}

    def test_exact_thresholds_and_each_one_byte_below(self):
        self.assertTrue(require_capacity(self.mem(),before_slot=True)['meets_load_only_threshold'])
        for m in (self.mem(cma=RESERVE_BYTES-1),self.mem(available=RESERVE_BYTES+SLOT_BYTES-1)):
            with self.assertRaises(CapacityRejected):require_capacity(m,before_slot=True)
        self.assertTrue(require_capacity(self.mem(available=RESERVE_BYTES),before_slot=False)['meets_load_only_threshold'])
        with self.assertRaises(CapacityRejected):require_capacity(self.mem(available=RESERVE_BYTES-1),before_slot=False)

    def test_missing_invalid_memory_rejected(self):
        for value in (None,True,-1,1.5):
            with self.assertRaises(ValueError):eligibility(self.mem(cma=value),before_slot=True)
        with self.assertRaises(ValueError):eligibility({'system_bytes':{}},before_slot=True)

    def test_maximum_four_port_allocation_touch_readback(self):
        slots=[]; proof={}
        materialize_slot(slots,proof,page_bytes=4096)
        self.assertEqual([len(s) for s in slots],[PORT_BYTES]*4)
        self.assertEqual(proof['payload_bytes'],SLOT_BYTES)
        self.assertTrue(proof['all_ports_materialized'])
        for s in slots:
            self.assertTrue(all(s[o]==0xA5 for o in range(0,PORT_BYTES,4096)))
            self.assertEqual(s[-1],0x5A)
        slots.clear()

    def test_partial_allocation_failure_preserves_caller_ownership(self):
        calls=[]
        def allocate(n):
            calls.append(n)
            if len(calls)==2:raise MemoryError('injected')
            return bytearray(n)
        slots=[]
        with self.assertRaises(MemoryError):materialize_slot(slots,{},page_bytes=4096,allocator=allocate)
        self.assertEqual(len(slots),1)
        slots.clear()

    def test_existing_slot_and_invalid_pages_rejected(self):
        with self.assertRaises(ValueError):materialize_slot([bytearray(1)],{},page_bytes=4096)
        for n in (0,-1,True):
            with self.assertRaises(ValueError):materialize_slot([],{},page_bytes=n)

    def test_never_submitted_is_distinct_from_completed_dma(self):
        snap=dict(ap_ctrl=4,ap_return=0,mm2s_dmasr=0,s2mm_dmasr=0,mm2s_error=False,s2mm_error=False,
                  kernel_read_error='',return_read_error='',dma_read_error='')
        self.assertTrue(never_submitted_release(snap,0,0,[],7))
        for k,v in [('ap_ctrl',0),('mm2s_dmasr',4098),('s2mm_dmasr',4098),('mm2s_error',True)]:
            self.assertFalse(never_submitted_release(dict(snap,**{k:v}),0,0,[],7))
        for h,l,b,a in [(1,0,[],7),(0,1,[],7),(0,0,['blocked'],7),(0,0,[],6)]:
            self.assertFalse(never_submitted_release(snap,h,l,b,a))


if __name__=='__main__':unittest.main(verbosity=2)
