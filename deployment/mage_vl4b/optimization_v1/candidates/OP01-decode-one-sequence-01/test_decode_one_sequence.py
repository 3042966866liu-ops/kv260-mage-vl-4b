"""Controller contract tests, not model/FPGA numerical evidence."""
import unittest
from types import SimpleNamespace
import numpy as np
from decode_one_sequence import run_sequence


class SequenceTests(unittest.TestCase):
    def cache(self):
        return SimpleNamespace(keys=[np.zeros((852,1),np.float32) for _ in range(36)],
                               values=[np.zeros((852,1),np.float32) for _ in range(36)])

    def factory(self, calls, *, fail_kv=False, nan=False):
        class Diagnostic:
            def decode(self, token, cache):
                calls.append((token,id(cache)))
                for attr in ('keys','values'):
                    setattr(cache,attr,[np.concatenate((x,np.array([[token]],np.float32)))
                                       for x in getattr(cache,attr)])
                if fail_kv:cache.values[35]=cache.values[35][:-1]
                logits=np.full(151936,token,np.float32)
                if nan:logits[0]=np.nan
                return token+1,logits
            def finalize(self):return {'steps':[{'status':'RECORDED'}]}
        return Diagnostic

    def test_continuation_and_exact(self):
        calls=[];a=run_sequence(1291,self.cache(),self.factory(calls))
        self.assertEqual([x[0] for x in calls],[1291,1292,1293])
        self.assertEqual(len(set(x[1] for x in calls)),1)
        b=run_sequence(1291,self.cache(),self.factory([]),reference=a['steps'])
        self.assertTrue(all(x['bit_exact'] for x in b['steps']))
        self.assertEqual(b['steps'][-1]['kv_lengths'],[855]*72)

    def test_mismatch_stops_before_next_step(self):
        a=run_sequence(1291,self.cache(),self.factory([]))
        a['steps'][1]['logits'][0]+=1
        calls=[];evidence=[]
        with self.assertRaisesRegex(RuntimeError,'step 1'):
            run_sequence(1291,self.cache(),self.factory(calls),reference=a['steps'],evidence=evidence)
        self.assertEqual(len(calls),2)
        self.assertEqual(evidence[-1]['status'],'FAIL_NUMERICAL')

    def test_value_cache_growth_is_checked(self):
        with self.assertRaisesRegex(RuntimeError,'increment'):
            run_sequence(1291,self.cache(),self.factory([],fail_kv=True))

    def test_nonfinite_rejected(self):
        with self.assertRaisesRegex(RuntimeError,'logits'):
            run_sequence(1291,self.cache(),self.factory([],nan=True))

    def test_wrong_start_rejected(self):
        with self.assertRaises(ValueError):run_sequence(1290,self.cache(),self.factory([]))

    def test_bounds(self):
        with self.assertRaises(ValueError):run_sequence(1291,self.cache(),self.factory([]),steps=128)
        with self.assertRaises(ValueError):run_sequence(1291,self.cache(),self.factory([]),reference=[])


if __name__=='__main__':unittest.main()
