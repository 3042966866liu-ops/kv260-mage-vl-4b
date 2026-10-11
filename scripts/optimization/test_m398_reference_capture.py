"""Actual original36-layer control + real-size synthetic math; fake PL/Attention."""
import tempfile
from pathlib import Path
from types import SimpleNamespace
import unittest
import numpy as np
from m351_workflow import ROOT
from m398_reference_capture import LastLayerReferenceCapture,RetainedReferenceOwnerError,SHAPES,PAYLOAD_BYTES
import test_m397_last_layer_tail as fixture

TEMP=ROOT/'tmp/m398/component-tests'

class Tests(unittest.TestCase):
    def case(self,d):
        f=fixture.Tests();model,module,original=f.model_case(159)
        p=SimpleNamespace(safe=lambda:f.safe,capture=lambda *a:None)
        scope=LastLayerReferenceCapture(model,p,lambda:True,d,enabled=True)
        family=model._family
        def observed(layer,name,value):
            # Frozen M238 targets are np.full C-order; synthetic indexed output
            # is explicitly normalized to that fake-backend contract here.
            out={k:np.ascontiguousarray(v) for k,v in family(layer,name,value).items()}
            scope.family(layer,name,value,out);return out
        model._family=observed
        return f,model,module,original,scope
    def test_actual_full36_loop_capture_matches_original(self):
        with tempfile.TemporaryDirectory(dir=TEMP) as d:
            self.assertEqual(Path(d).resolve().parent,TEMP.resolve())
            f,m,module,original,scope=self.case(d)
            hidden=np.random.default_rng(4).standard_normal((159,2560),dtype=np.float32)*np.float32(.1)
            g=fixture.Tests();model,_,base=g.model_case(159);family=model._family
            model._family=lambda layer,name,value:{k:np.ascontiguousarray(v) for k,v in family(layer,name,value).items()}
            expected=base(model,hidden)
            fn=scope.bind(module);actual=fn(m,hidden)
            self.assertEqual(actual[1].tobytes(),expected[1].tobytes())
            for name in ('keys','values'):self.assertEqual([x.tobytes() for x in getattr(actual[2],name)],[x.tobytes() for x in getattr(expected[2],name)])
            self.assertEqual(set(scope.fixtures),set(SHAPES));self.assertEqual(scope.report()['payload_bytes'],PAYLOAD_BYTES)
            for key,shape in SHAPES.items():
                a=np.load(Path(d)/(key+'.npy'),allow_pickle=False)
                self.assertEqual(a.shape,shape);self.assertEqual(a.dtype,np.float32)
            self.assertEqual(np.load(Path(d)/'logits.npy').tobytes(),expected[1].tobytes())
            self.assertEqual(np.load(Path(d)/'final_norm.npy').tobytes(),g.last_hidden.tobytes())
            for fam,input_key in [('attention_out','attention_out_input_tail'),('gate_up','gate_up_input_tail'),('mlp_down','mlp_down_input_tail')]:
                self.assertEqual(np.load(Path(d)/(input_key+'.npy')).tobytes(),g.records[fam][0][128:].tobytes())
            scope.close();scope.close();self.assertTrue(scope.report()['binding_callback_removed'])
            self.assertLess(scope.report()['file_bytes'],16<<20)
            with self.assertRaises(RetainedReferenceOwnerError):fn(m,hidden)
    def test_disabled_by_default(self):
        with self.assertRaises(RuntimeError):LastLayerReferenceCapture(None,None,None,TEMP)
    def test_existing_fixture_refused(self):
        with tempfile.TemporaryDirectory(dir=TEMP) as d:
            (Path(d)/'hidden_tail.npy').write_bytes(b'existing')
            with self.assertRaises(RuntimeError):self.case(d)
    def test_failed_final_consumer_retains_owner_and_files(self):
        with tempfile.TemporaryDirectory(dir=TEMP) as d:
            f,m,module,original,scope=self.case(d);family=m._family
            def fault(layer,name,value):
                if layer==35 and name=='mlp_down':raise RuntimeError('FAKE_PL_ERROR')
                return family(layer,name,value)
            m._family=fault
            with self.assertRaises(RetainedReferenceOwnerError):scope.bind(module)(m,np.ones((159,2560),np.float32))
            self.assertTrue(scope.retained);self.assertIs(scope.model,m);self.assertEqual(f.head_calls,0)
            with self.assertRaises(RetainedReferenceOwnerError):scope.close()
            self.assertFalse(scope.report()['binding_callback_removed'])
            self.assertTrue((Path(d)/'attended_full.npy').exists())
    def test_bad_layout_or_nonfinite_refused_without_file(self):
        with tempfile.TemporaryDirectory(dir=TEMP) as d:
            f,m,module,original,scope=self.case(d)
            for a in (np.zeros((30,2560),np.float32),np.ones((31,2560),np.float64),np.full((31,2560),np.nan,np.float32)):
                with self.assertRaises(RuntimeError):scope.save('hidden_tail',a)
            self.assertEqual(scope.fixtures,{})
            scope.close()
    def test_unsafe_barrier_and_wrong_source_refused(self):
        with tempfile.TemporaryDirectory(dir=TEMP) as d:
            f,m,module,original,scope=self.case(d);module.__file__=__file__
            with self.assertRaises(RuntimeError):scope.bind(module)
            f.safe=False
            with self.assertRaises(RetainedReferenceOwnerError):scope.close()
            self.assertIs(scope.model,m)

if __name__=='__main__':
    TEMP.mkdir(parents=True,exist_ok=True)
    unittest.main()
