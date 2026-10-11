"""Actual CPU runner with synthetic arrays/explicit fake platform and memory."""
import ast
import contextlib
import hashlib
import importlib.util
import io
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
import numpy as np
from m351_workflow import ROOT,HERE,BASE,sha,encoded

def load():
    original=ROOT/'release_staging/kv260-mage-vl-4b-prebuilt-install-20260926-v7/deployment/mage_vl4b/m181_m120_video_board_candidate/video_language_runtime.py'
    text=original.read_text(encoding='utf-8');tree=ast.parse(text);node=next(x for x in tree.body if isinstance(x,ast.FunctionDef) and x.name=='silu')
    import sys,types
    stub=types.ModuleType('original_silu');exec('import numpy as np\n'+ast.get_source_segment(text,node),stub.__dict__);sys.modules['original_silu']=stub
    spec=importlib.util.spec_from_file_location('actual_draft_m391_gate',HERE/'m391_silu_gate.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
    return m

class Tests(unittest.TestCase):
    def setUp(self):
        self.module=load();root=ROOT/'tmp/m391/test-fixtures';root.mkdir(parents=True,exist_ok=True)
        self.tmp=tempfile.TemporaryDirectory(dir=root);self.base=Path(self.tmp.name).resolve();assert self.base.parent==root.resolve()
        self.pkg=self.base/'package';self.pkg.mkdir();self.fixture=self.base/'capture';self.fixture.mkdir()
        self.result=self.base/'result';self.m=self.module;self.m.HERE=self.pkg;self.m.OUT=self.result;self.m.CAPTURE=self.fixture/'load-memory.json'
        arrays={}
        for i,n in enumerate(('gate','up')):
            a=np.random.default_rng(123+i).standard_normal((159,9728),dtype=np.float32);p=self.fixture/(n+'.npy');np.save(p,a,allow_pickle=False)
            arrays[n]=dict(path=str(p),file_sha256=sha(p),file_bytes=p.stat().st_size,tensor=dict(shape=list(a.shape),dtype=str(a.dtype),bytes=a.nbytes,sha256=hashlib.sha256(a.tobytes()).hexdigest()))
        self.capture=dict(status='PASS_M390_ACTUAL_GATE_UP_CAPTURE',capture_pass=True,actual_gate_up_fixtures=arrays)
        self.m.CAPTURE.write_bytes(encoded(self.capture));self.spec=dict(capture_raw_sha256=sha(self.m.CAPTURE),fixtures=arrays)
        self.write_spec()
    def write_spec(self):
        (self.pkg/'INPUT_IDENTITY.json').write_bytes(encoded(self.spec));self.manifest=dict(files=[dict(path='INPUT_IDENTITY.json',bytes=(self.pkg/'INPUT_IDENTITY.json').stat().st_size,sha256=sha(self.pkg/'INPUT_IDENTITY.json'))],file_count=1,total_bytes=(self.pkg/'INPUT_IDENTITY.json').stat().st_size)
        (self.pkg/'PACKAGE_MANIFEST.json').write_bytes(encoded(self.manifest))
    def run_gate(self):
        with patch.object(self.m.os,'geteuid',return_value=0,create=True),patch.object(self.m,'memory',return_value=dict(MemAvailable=3*1024**3,CmaFree=123,VmRSS=456)),contextlib.redirect_stdout(io.StringIO()):
            code=self.m.main(sha(self.pkg/'PACKAGE_MANIFEST.json'),True)
        return code,json.loads((self.result/'RESULT.json').read_text(encoding='utf-8'))
    def tearDown(self):self.tmp.cleanup()
    def test_actual_real_geometry_math_timing_and_release(self):
        code,r=self.run_gate();self.assertEqual(code,0,r['errors']);self.assertTrue(r['numerical_pass']);self.assertTrue(r['workspace_object_and_buffer_released']);self.assertEqual(len(r['batches']),48);self.assertEqual(len(r['groups']),12);self.assertEqual(len(r['memory']),9)
        for n in ('gate','up'):self.assertEqual(sha(Path(self.spec['fixtures'][n]['path'])),self.spec['fixtures'][n]['file_sha256'])
        with patch.object(self.m.os,'geteuid',return_value=0,create=True),self.assertRaises(RuntimeError):self.m.main(sha(self.pkg/'PACKAGE_MANIFEST.json'),True)
    def test_disabled_does_not_create_result(self):
        with self.assertRaises(RuntimeError):self.m.main('x',False)
        self.assertFalse(self.result.exists())
    def test_capture_identity_before_read(self):
        self.spec['capture_raw_sha256']='0'*64;self.write_spec();code,r=self.run_gate();self.assertEqual(code,1);self.assertIn('capture raw differs',r['errors'][0])
    def test_fixture_sha_before_np_load(self):
        p=Path(self.spec['fixtures']['gate']['path']);p.write_bytes(p.read_bytes()+b'x');code,r=self.run_gate();self.assertEqual(code,1);self.assertIn('fixture file differs',r['errors'][0])
    def test_shape_rejected_even_matching_file(self):
        p=Path(self.spec['fixtures']['gate']['path']);np.save(p,np.ones((30,9728),np.float32));self.spec['fixtures']['gate'].update(file_sha256=sha(p),file_bytes=p.stat().st_size)
        self.capture['actual_gate_up_fixtures']=self.spec['fixtures'];self.m.CAPTURE.write_bytes(encoded(self.capture));self.spec['capture_raw_sha256']=sha(self.m.CAPTURE);self.write_spec()
        code,r=self.run_gate();self.assertEqual(code,1);self.assertIn('shape/dtype/finite',r['errors'][0])
    def test_payload_extra_refusal(self):
        (self.pkg/'extra').write_bytes(b'x');code,r=self.run_gate();self.assertEqual(code,1);self.assertIn('whitelist',r['errors'][0])

if __name__=='__main__':unittest.main()
