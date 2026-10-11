"""Real frozen scheduling/Futures; explicit fake PL, parser and memory."""
import copy
from pathlib import Path
import sys
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'deployment/mage_vl4b/optimization_v1/candidates/M373-future-wait-component-01'))
import numpy as np
from m373_test_future_wait import Harness
from m374_layer_wait import LayerWaitDiagnostic,FAMILIES
from m374_wait_validation import validate

class Probe(Harness):
    def _language_chain(self, layer, family):
        return dict(chain_index=FAMILIES.index(family),layer=layer,family=family,groups=1)

def run_layer(runtime,scope=None):
    x=np.arange(159*64,dtype=np.float32).reshape(159,64)
    rows=[]
    for family in FAMILIES:
        if scope is None: output=runtime.language_family_many(0,family,x)
        else:
            with scope.family(0,family,x):output=runtime.language_family_many(0,family,x)
        rows.append(output['probe'])
    return rows

class Tests(unittest.TestCase):
    def report(self):
        runtime=Probe();scope=LayerWaitDiagnostic(runtime,enabled=True)
        actual=scope.run(lambda:run_layer(runtime,scope))
        expected=run_layer(Probe())
        for a,b in zip(actual,expected): np.testing.assert_array_equal(a,b)
        self.assertEqual(runtime.stages,5)
        self.assertNotIn('language_family_many',vars(runtime));self.assertNotIn('_resolve_pending',vars(runtime))
        report=scope.report()
        transactions=[dict(family=f,chain_index=i) for i,f in enumerate(FAMILIES)]
        return report,transactions
    def test_five_frozen_families_same_outputs_and_summary(self):
        report,transactions=self.report();result=validate(report,transactions)
        self.assertEqual(result['summary']['pack']['calls'],25)
        self.assertEqual(result['summary']['parse']['calls'],25)
        self.assertEqual(result['main_thread_closure_error_ns'],0)
    def test_default_disabled_no_mutation(self):
        runtime=Probe()
        with self.assertRaises(ValueError):LayerWaitDiagnostic(runtime)
        self.assertNotIn('language_family_many',vars(runtime))
    def test_parser_failure_restores_and_preserves_exception(self):
        runtime=Probe(fail_parse=True);scope=LayerWaitDiagnostic(runtime,enabled=True)
        with self.assertRaisesRegex(ValueError,'fake parser'):scope.run(lambda:run_layer(runtime,scope))
        self.assertTrue(scope.restored);self.assertFalse(scope.running)
        self.assertNotIn('language_family_many',vars(runtime))
    def test_single_run_bound(self):
        scope=LayerWaitDiagnostic(Probe(),enabled=True);scope.run(lambda:run_layer(scope.runtime,scope))
        with self.assertRaises(RuntimeError):scope.run(lambda:None)
    def test_family_escape_before_original_call(self):
        scope=LayerWaitDiagnostic(Probe(),enabled=True)
        def call():
            with scope.family(1,'q',np.ones((159,64),np.float32)):raise AssertionError('must not call')
        with self.assertRaisesRegex(RuntimeError,'escaped'):scope.run(call)
        self.assertTrue(scope.restored)
    def test_collector_rejects_trace_wait_and_order_mutations(self):
        original,transactions=self.report()
        for mutate in ('summary','trace','identity','order','scope','implementation'):
            report=copy.deepcopy(original)
            if mutate=='summary':report['summary']['parse']['condition_wait_s']+=1
            if mutate=='trace':report['trace']['events'][0]['exclusive_ns']+=1
            if mutate=='identity':report['records'][0]['chain_index']+=10
            if mutate=='order':report['records'][0]['token_start']=96
            if mutate=='scope':report['extra_cma_allocations']=1
            if mutate=='implementation':report['future_result_source_sha256']='0'*64
            with self.assertRaises(ValueError,msg=mutate):validate(report,transactions)

if __name__=='__main__':unittest.main()
