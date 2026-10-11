import json
from pathlib import Path
import tempfile
import unittest
import numpy as np
from numerical_capture import NumericalCapture
from test_causal_generation import Model


class CaptureTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.out=Path(self.temp.name)/'capture'

    def test_records_without_changing_returns(self):
        model=Model();capture=NumericalCapture(model,self.out,identity={'test':True})
        hidden=np.ones((4,3),np.float32)
        token,logits,cache=capture.prefill(hidden)
        prior=logits.copy();key=cache.keys[0].copy()
        np.testing.assert_array_equal(logits,prior);np.testing.assert_array_equal(cache.keys[0],key)
        returned=capture.decode(token,cache);self.assertEqual(returned[0],1)
        capture.finish('length')
        report=json.loads((self.out/'manifest.json').read_text())
        self.assertEqual([r['kv_length'] for r in report['steps']],[4,5])
        self.assertEqual(report['status'],'RECORDED');self.assertFalse(report['numerical_acceptance'])
        np.testing.assert_array_equal(np.load(self.out/'prefill_hidden.npy'),hidden)
        np.testing.assert_array_equal(np.load(self.out/'step001_logits.npy'),returned[1])
        self.assertEqual(model.prefills,1);self.assertEqual(model.decodes,1)

    def test_no_reuse_or_unbounded_decode(self):
        model=Model();capture=NumericalCapture(model,self.out,identity={},max_steps=1)
        token,_,cache=capture.prefill(np.ones((4,3),np.float32))
        with self.assertRaises(RuntimeError):capture.decode(token,cache)
        with self.assertRaises(RuntimeError):capture.prefill(np.ones((4,3),np.float32))
        with self.assertRaises(FileExistsError):NumericalCapture(model,self.out,identity={})
        self.assertEqual(model.decodes,0)

    def test_model_error_is_retained(self):
        model=Model()
        def fail(hidden):raise RuntimeError('device timeout')
        model.prefill=fail
        capture=NumericalCapture(model,self.out,identity={})
        with self.assertRaisesRegex(RuntimeError,'device timeout'):capture.prefill(np.ones((4,3),np.float32))
        capture.finish('length')
        self.assertEqual(json.loads((self.out/'manifest.json').read_text())['status'],'FAIL')


if __name__=='__main__':unittest.main()
