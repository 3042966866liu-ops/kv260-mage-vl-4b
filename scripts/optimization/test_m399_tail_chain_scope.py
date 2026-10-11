"""Real last31 NPY identities/bytes; explicit fake Linear, DMA and memory."""
import copy
import json
from pathlib import Path
from types import SimpleNamespace
import tempfile
import unittest
import numpy as np
from m351_workflow import ROOT
from m368_video_contract import tensor
from m398_reference_capture import SHAPES
from m399_tail_chain_scope import TailChainScope,RetainedChainOwnerError,PLAN,digest

TEMP=ROOT/'tmp/m399/component-tests'

class Tests(unittest.TestCase):
    def fixture(self,d,kind=None):
        path=Path(d);files={};arrays={}
        used={p[1] for p in PLAN}|{n for p in PLAN for n in p[2].values()}
        for name,shape in SHAPES.items():
            if name in used:
                a=np.full(shape,np.float32(.03125),dtype=np.float32);arrays[name]=a
                np.save(path/(name+'.npy'),a,allow_pickle=False)
                files[name]=dict(path=str(path/(name+'.npy')),file_bytes=(path/(name+'.npy')).stat().st_size,file_sha256=digest(path/(name+'.npy')),tensor=tensor(a),original_token_start=128)
            else:files[name]=dict(unused_metadata_explicit_fake=True)
        reference=dict(status='PASS_M398_ORIGINAL_TAIL_REFERENCE',gate_return_code=0,reference_capture_pass=True,tail_candidate_executed=False,candidate_numerical_pass=False,
                       reference_capture=dict(closed=True,retained=False,binding_callback_removed=True,candidate_tail_not_executed=True,file_count=12,fixtures=files))
        raw=path/'load-memory.json';raw.write_text(json.dumps(reference),encoding='utf-8')
        called=[];safe=[True];resident=[True]
        def family(layer,name,values):
            assert layer==35 and values.shape==SHAPES[next(p[1] for p in PLAN if p[0]==name)] and not values.flags.writeable
            called.append(name)
            if kind=='consumer' and name=='gate_up':raise RuntimeError('FAKE_CONSUMER_ERROR')
            if kind=='busy' and name=='attention_out':safe[0]=False
            if kind=='change' and name=='attention_out':raw.write_text(raw.read_text(encoding='utf-8')+' ',encoding='utf-8')
            names=next(p[2] for p in PLAN if p[0]==name)
            out={'model.language_model.layers.35.'+k:arrays[n].copy() for k,n in names.items()}
            if kind=='numerical' and name=='gate_up':next(iter(out.values()))[0,0]=np.nextafter(np.float32(.03125),np.float32(1))
            if kind=='keys' and name=='gate_up':out={}
            return out
        policy=SimpleNamespace(safe=lambda:safe[0],capture=lambda *a:None)
        return SimpleNamespace(_family=family),policy,lambda:resident[0],raw,digest(raw),called,safe,reference
    def cleanup_fake_maps(self,scope):
        # Only test-owned mmap files. No real DMA/worker exists in this test.
        for a in scope.maps.values():a._mmap.close()
        scope.maps.clear()
    def test_full_three_last31_chains_and_close(self):
        with tempfile.TemporaryDirectory(dir=TEMP) as d:
            model,policy,resident,path,sha,calls,safe,reference=self.fixture(d)
            scope=TailChainScope(model,policy,resident,path,sha,enabled=True)
            rows=scope.run();self.assertEqual(calls,['attention_out','gate_up','mlp_down']);self.assertEqual(len(rows),3)
            self.assertTrue(all(r['full_output_bitwise_equal'] and r['tokens']==31 and r['original_token_start']==128 for r in rows))
            scope.close();scope.close();r=scope.report();self.assertTrue(r['closed'] and r['reference_maps_released']);self.assertEqual(r['reference_files_checked'],7)
            self.assertIsNone(scope.model);self.assertEqual(r['extra_DMA'],0)
            with self.assertRaises(RetainedChainOwnerError):scope.run()
    def test_disabled_and_wrong_raw(self):
        with tempfile.TemporaryDirectory(dir=TEMP) as d:
            m,p,f,path,h,*_=self.fixture(d)
            with self.assertRaisesRegex(RuntimeError,'disabled'):TailChainScope(m,p,f,path,h)
            with self.assertRaisesRegex(RuntimeError,'raw SHA'):TailChainScope(m,p,f,path,'0'*64,enabled=True)
    def test_consumer_numerical_keys_or_identity_fault_stops_and_retains(self):
        for kind in ('consumer','numerical','keys','change','busy'):
            with self.subTest(kind=kind),tempfile.TemporaryDirectory(dir=TEMP) as d:
                m,p,f,path,h,calls,safe,r=self.fixture(d,kind)
                scope=TailChainScope(m,p,f,path,h,enabled=True)
                try:
                    with self.assertRaises(RetainedChainOwnerError):scope.run()
                    self.assertTrue(scope.retained);self.assertFalse(scope.closed);self.assertNotIn('mlp_down',calls);self.assertTrue(scope.maps)
                    with self.assertRaises(RetainedChainOwnerError):scope.close()
                    self.assertIs(scope.model,m)
                finally:self.cleanup_fake_maps(scope)
    def test_path_file_hash_shape_and_token_mapping_faults(self):
        for key,value in (('path','/wrong/golden.npy'),('file_sha256','0'*64),('original_token_start',0),('shape',[1,4096])):
            with self.subTest(key=key),tempfile.TemporaryDirectory(dir=TEMP) as d:
                m,p,f,path,h,calls,safe,r=self.fixture(d)
                target=r['reference_capture']['fixtures']['attention_out_input_tail']
                if key=='shape':target['tensor'][key]=value
                else:target[key]=value
                path.write_text(json.dumps(r),encoding='utf-8');scope=TailChainScope(m,p,f,path,digest(path),enabled=True)
                try:
                    with self.assertRaises(RetainedChainOwnerError):scope.run()
                    self.assertEqual(calls,[]);self.assertTrue(scope.retained)
                finally:self.cleanup_fake_maps(scope)
    def test_no_candidate_or_unclosed_reference_accepted(self):
        for place,key,value in (('raw','tail_candidate_executed',True),('raw','candidate_numerical_pass',True),('capture','closed',False),('capture','retained',True),('capture','file_count',11)):
            with self.subTest(key=key),tempfile.TemporaryDirectory(dir=TEMP) as d:
                m,p,f,path,h,calls,safe,r=self.fixture(d)
                (r if place=='raw' else r['reference_capture'])[key]=value;path.write_text(json.dumps(r),encoding='utf-8')
                with self.assertRaises(RuntimeError):TailChainScope(m,p,f,path,digest(path),enabled=True)
                self.assertEqual(calls,[])
    def test_close_cannot_ignore_postuse_reference_change(self):
        with tempfile.TemporaryDirectory(dir=TEMP) as d:
            m,p,f,path,h,calls,safe,r=self.fixture(d);scope=TailChainScope(m,p,f,path,h,enabled=True)
            try:
                scope.run();path.write_text(path.read_text(encoding='utf-8')+' ',encoding='utf-8')
                with self.assertRaises(RuntimeError):scope.close()
                self.assertFalse(scope.closed);self.assertTrue(scope.retained);self.assertTrue(scope.maps);self.assertIs(scope.model,m)
            finally:self.cleanup_fake_maps(scope)

if __name__=='__main__':
    TEMP.mkdir(parents=True,exist_ok=True);assert TEMP.resolve().is_relative_to(ROOT.resolve());unittest.main()
