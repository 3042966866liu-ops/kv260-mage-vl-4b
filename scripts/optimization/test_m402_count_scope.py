"""Actual frozen M276 stream with explicit fake vision/Linear/board evidence."""
import ast
import copy
import math
from types import SimpleNamespace
import threading
import time
import unittest
import numpy as np
from m351_workflow import ROOT
from m402_count_scope import VideoCountScope

RELEASE=ROOT/'release_staging/kv260-mage-vl-4b-prebuilt-install-20260926-v7'
COUNTER=RELEASE/'deployment/mage_vl4b/m181_m120_video_board_candidate/video_language_runtime.py'
STREAM=RELEASE/'deployment/mage_vl4b/m277_m276_fixed_window_board_candidate/m276_video_runtime.py'
def extract(path,name,namespace):
    tree=ast.parse(path.read_text(encoding='utf-8-sig'))
    found=[n for n in ast.walk(tree) if isinstance(n,ast.FunctionDef) and n.name==name]
    assert len(found)==1
    exec(compile(ast.fix_missing_locations(ast.Module(body=[ast.ImportFrom(module='__future__',names=[ast.alias(name='annotations')],level=0),found[0]],type_ignores=[])),str(path),'exec'),namespace)
    return namespace[name]
def server():
    ns=dict(math=math,MAX_CONTEXT=1024,LANGUAGE_CHAIN_CALLS_PER_T32_BATCH=154,LM_HEAD_CHAIN_CALLS=8,DECODE_CHAIN_CALLS_PER_TOKEN=154)
    return SimpleNamespace(expected_physical_calls=extract(COUNTER,'expected_physical_calls',ns),BUILD_ID='0x4D333537',KERNEL='explicit-fake-kernel')

class Tests(unittest.TestCase):
    def case(self,calls=766,build='0x4D333537',macros=1):
        srv=server();before=dict(logical_calls=0,logical_expected_macros=0,build_id=build)
        after=dict(logical_calls=calls,logical_expected_macros=macros,build_id=build)
        evidence=[before,after];engine=SimpleNamespace(load=lambda:None,_inference_lock=threading.Lock(),board=SimpleNamespace(evidence=lambda:copy.deepcopy(evidence.pop(0))),vision=lambda *a:np.zeros((98,2560),np.float32),language=SimpleNamespace(prefill=lambda h:(15,np.zeros(151936,np.float32),None)),tokenizer=object(),config={'tokenizer':'explicit-fake-tokenizer'})
        decision=dict(text='0',token_id=15,verdict='ABSENT',knife_score=.4,score_kind='explicit-fake-score')
        ns=dict(np=np,time=time,_server=srv,M276_KNIFE_PROMPT='frozen-test-prompt',preprocess=lambda f:dict(pixel_values=0,image_grid_thw=0,patch_positions=0),tokenize=lambda *a:list(range(159)),latest_input_embeddings=lambda *a:np.zeros((159,2560),np.float32),constrained_knife_decision=lambda _:decision)
        stream=extract(STREAM,'stream',ns)
        return srv,engine,stream,SimpleNamespace(frames_rgb_u8=np.zeros((4,448,448,3),np.uint8))
    def test_actual_stream_candidate_proof_and_restore(self):
        srv,e,stream,req=self.case();orig=srv.expected_physical_calls;scope=VideoCountScope(srv,lambda:True,enabled=True)
        events=list(stream(e,req));proof=events[-1][1]['proof']
        self.assertEqual(proof['pl_logical_chain_calls'],766);self.assertEqual(proof['expected_pl_logical_chain_calls'],766)
        scope.close();self.assertIs(srv.expected_physical_calls,orig);self.assertEqual(orig(159,1),778)
        self.assertEqual(scope.report()['accepted_calls'],1);scope.close()
    def test_original_stream_rejects_candidate_without_adapter(self):
        srv,e,stream,req=self.case()
        with self.assertRaises(RuntimeError):list(stream(e,req))
    def test_actual_stream_rejects_wrong_calls_build_and_macros(self):
        for kw in ({'calls':778},{'calls':765},{'build':'0xBAD'},{'macros':0}):
            srv,e,stream,req=self.case(**kw);scope=VideoCountScope(srv,lambda:True,enabled=True)
            with self.assertRaises(RuntimeError):list(stream(e,req))
    def test_other_inputs_default_off_and_reentry_refused(self):
        srv=server()
        with self.assertRaises(RuntimeError):VideoCountScope(srv,lambda:True)
        scope=VideoCountScope(srv,lambda:True,enabled=True)
        for args in ((30,1),(159,2),(True,1),(159,True)):
            with self.assertRaises(RuntimeError):srv.expected_physical_calls(*args)
        self.assertEqual(srv.expected_physical_calls(159,1),766)
        with self.assertRaises(RuntimeError):srv.expected_physical_calls(159,1)
        scope.close()
        with self.assertRaises(RuntimeError):scope.count(159,1)
    def test_unsafe_missing_call_or_foreign_binding_blocks_close(self):
        srv=server();resident=[True];scope=VideoCountScope(srv,lambda:resident[0],enabled=True)
        with self.assertRaises(RuntimeError):scope.close()
        srv.expected_physical_calls(159,1);resident[0]=False
        with self.assertRaises(RuntimeError):scope.close()
        resident[0]=True;bound=srv.expected_physical_calls;srv.expected_physical_calls=lambda *a:766
        with self.assertRaises(RuntimeError):scope.close()
        srv.expected_physical_calls=bound;scope.close()
    def test_counter_identity_change_refused(self):
        srv=server();srv.expected_physical_calls=lambda *a:778
        with self.assertRaises(RuntimeError):VideoCountScope(srv,lambda:True,enabled=True)
    def test_cross_thread_refused(self):
        srv=server();scope=VideoCountScope(srv,lambda:True,enabled=True);errors=[]
        def call():
            try:srv.expected_physical_calls(159,1)
            except RuntimeError:errors.append('refused')
        t=threading.Thread(target=call);t.start();t.join();self.assertEqual(errors,['refused'])
        srv.expected_physical_calls(159,1);scope.close()

if __name__=='__main__':unittest.main()
