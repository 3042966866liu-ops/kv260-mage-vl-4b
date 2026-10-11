"""Only changed layer budget and actual orchestration; explicit DMA/memory doubles."""
import copy, os, textwrap, time, unittest, weakref
from types import SimpleNamespace
from m351_workflow import BASE
import test_m383_sealed_ps_read as prior_fixture
from m385_layer_ps_read import LayerPSReadSession
from m365_stage_policy import assess, SHAPES, FAMILIES
from ps_read_ahead import RetainedPSResourcesError
from test_m382_ps_slot import memory

class Tests(unittest.TestCase):
    def setUp(self):
        prior_fixture.Tests.setUp(self)
        self.current=memory(rss=100<<20)
        self.current['system_bytes']['MemAvailable']=1<<30
        self.policy.baseline_rss=100<<20
        self.policy.initial_counts=dict(self.counts)
        self.policy.buffer_bytes=list(SHAPES)
        self.policy.stop_reason=None
        def capture(label,check):
            if check:assess(self.current,self.policy.baseline_rss,self.counts,self.policy.initial_counts,sealed=self.policy.sealed,buffer_bytes=self.policy.buffer_bytes)
            return copy.deepcopy(self.current)
        self.policy.capture=capture
    def make(self):
        return LayerPSReadSession(self.runtime,self.base,self.plan,enabled=True,policy=self.policy,resident=lambda:self.resident,completed_transaction_snapshot=self.base.transaction_snapshot())
    def test_slot_and_layer_share_existing_budget(self):
        self.current=memory(rss=180<<20)
        self.current['system_bytes']['MemAvailable']=1<<30
        s=self.make();s._memory()
        self.assertEqual(s.memory_checks[-1]['decision']['observed_rss_growth_bytes'],80<<20)
        self.assertEqual(s.memory_checks[-1]['decision']['required_mem_available_bytes'],240<<20)
    def test_budget_rejects_over256(self):
        self.current=memory(rss=357<<20)
        with self.assertRaises(MemoryError):self.make()
    def test_remaining_budget_reserve_rejected(self):
        self.current['system_bytes']['MemAvailable']=319<<20
        with self.assertRaises(MemoryError):self.make()
    def test_counts_reject(self):
        s=self.make();self.counts['success']+=1
        with self.assertRaises(RuntimeError):s._memory()
    def test_latched_stop_rejects(self):
        self.policy.stop_reason='deliberate'
        with self.assertRaises(MemoryError):self.make()
    def test_resident_loss_rejects(self):
        s=self.make();self.resident=False
        with self.assertRaises(RetainedPSResourcesError):s._memory()
    def test_default_off(self):
        with self.assertRaises(ValueError):LayerPSReadSession(None,None,[],policy=self.policy)
    def test_actual_five_window_orchestration_and_release(self):
        chains={name:dict(offset=i*16,size=32,descriptors=[i]) for i,name in enumerate(FAMILIES)}
        self.runtime.language_layout=self.layout
        self.runtime._language_chain=lambda layer,name:chains[name]
        source=(BASE/'candidates/M385-ps-layer-02/m385_ps_layer_gate.py').read_text(encoding='utf-8')
        a=source.index('        plan=[(');b=source.index("        policy.capture('after-layer0'",a)
        result={};observed=[]
        def layer(model,hidden):
            for i,name in enumerate(FAMILIES):
                self.runtime._stage(self.layout,chains[name])
                expected=bytes(range(i*16,i*16+32))
                self.assertTrue(all(bytes(x.array[:32])==expected for x in self.runtime.staged_buffers))
                # Original CMA bytes remain stable while next PS read completes.
                time.sleep(.005)
                self.assertTrue(all(bytes(x.array[:32])==expected for x in self.runtime.staged_buffers))
                observed.append(name)
            return 'explicit fake layer output',None
        namespace=dict(runtime=self.runtime,base=self.base,policy=self.policy,resident=lambda:self.resident,result=result,FAMILIES=FAMILIES,LayerPSReadSession=LayerPSReadSession,weakref=weakref,RetainedPSResourcesError=RetainedPSResourcesError,one_layer=layer,model=None,hidden=SimpleNamespace(copy=lambda:None),allocations=[None]*7)
        before=self.runtime._stage
        exec(compile(textwrap.dedent(source[a:b]),'actual-frozen-layer-PS-scope','exec'),namespace)
        self.assertEqual(observed,FAMILIES)
        self.assertIs(self.runtime._stage,before)
        self.assertTrue(result['session_weakref_dead'])
        p=result['ps_session'];self.assertEqual(p['component']['stages'],5)
        self.assertEqual(p['component']['total_weight_bytes'],640)
        self.assertTrue(p['slot_release']['all_owner_weakrefs_dead'])
        self.assertEqual(p['budget_growth_bytes'],256<<20)
        self.assertFalse(hasattr(self.runtime,'_m351_ps_owner'))
if __name__=='__main__':unittest.main()
