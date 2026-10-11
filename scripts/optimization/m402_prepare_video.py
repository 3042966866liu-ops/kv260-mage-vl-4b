"""Assemble isolated fixed159 tail gate. Offline only; not an upload authorization."""
import ast
import json
from m351_workflow import ROOT,HERE,BASE,sha,atomic,encoded

OLD=BASE/'candidates/M401-tail-text-02'
PKG=BASE/'candidates/M402-tail-video-01'
SCOPE='sealed-DMA-fixed159-full36-layer-tail-prefill'
TEXT_RAW='e4ffe98c1deed4863701a783a90f2b1272cbbd7eb71136f37e0a38238d52da85'
TEXT_CLOSURE='0e3e6e2241fec9fb520f2334a84006b11991f052d58165f28c367506c25b914b'

def once(s,a,b):
    if s.count(a)!=1:raise AssertionError((a,s.count(a)))
    return s.replace(a,b)

def main():
    assert sha(OLD/'PACKAGE_MANIFEST.json')=='9942d0920a298a7625a9691984be03feaed31afed3194648da693cbf02a82d25'
    prerequisites={'runs/M401-tail-text-closure-02/RESULT.json':TEXT_CLOSURE,
        'runs/M401-tail-text-board-02/BOARD_RESULT.json':TEXT_RAW,
        'runs/M402-tail-video-contract-01/RESULT.json':'32b2f8f8af4afd3203d37867a76aeed05cae354cc7a842fb4d1f2fdf58ddc3b6'}
    for name,digest in prerequisites.items():assert sha(BASE/name)==digest
    for n in ('CURRENT_STATE.md','docsMILESTONES.md','deployment/mage_vl4b/BOARD_GATE_RESULT.json'):
        text=(ROOT/n).read_text(encoding='utf-8-sig');assert TEXT_CLOSURE in text and prerequisites['runs/M402-tail-video-contract-01/RESULT.json'] in text
    manifest=json.loads((OLD/'PACKAGE_MANIFEST.json').read_bytes())
    for r in manifest['files']:assert sha(OLD/r['path'])==r['sha256']
    payload={r['path']:(OLD/r['path']).read_bytes() for r in manifest['files'] if r['path']!='SHA256SUMS'}
    gate=payload.pop('m401_tail_text_gate.py').decode('utf-8')
    gate=gate.replace('M401','M402').replace('m401_tail_text_02','m402_tail_video_01').replace('m401_export_result','m402_export_result')
    gate=gate.replace('--enable-tail-text','--enable-tail-video').replace('enable_tail_text','enable_tail_video').replace('sealed-DMA-fixed30-full36-layer-tail-prefill',SCOPE)
    gate=once(gate,'slots = []; layer_scope = None','slots = []; layer_scope = count_scope = None')
    gate=once(gate,"from m368_video_contract import tensor,check_call_contract,validate_stream","from m402_video_contract import tensor,check_call_contract,validate_stream\nfrom m402_count_scope import VideoCountScope,validate as validate_count")
    gate=once(gate,"        if os.geteuid() != 0: raise RuntimeError('Same-terminal root required')",f"""        text_path=Path('/home/ubuntu/m401_tail_text_02/B1/load-memory.json')
        if sha256(text_path)!='{TEXT_RAW}':raise RuntimeError('Actual fixed-text prerequisite SHA differs')
        text_prior=json.loads(text_path.read_text(encoding='utf-8'))
        if text_prior['status']!='PASS_M401_TAIL_TEXT_NUMERICAL' or text_prior['gate_return_code'] or not text_prior['safe_buffers_released'] or not text_prior['stable_overlay_reloaded']:raise RuntimeError('Fixed-text closure rejected')
        result['text_prerequisite_sha256']=sha256(text_path)
        result['text_closure_sha256']=sha256(HERE/'M401_TEXT_CLOSURE.json')
        if result['text_closure_sha256']!='{TEXT_CLOSURE}':raise RuntimeError('Fixed-text host closure differs')
        if os.geteuid() != 0: raise RuntimeError('Same-terminal root required')""")
    gate=once(gate,'        policy=StagePolicy(result,lambda:runtime,base)',"        if m276_video_runtime._server is not video_server:raise RuntimeError('Actual stream server binding differs')\n        result['count_source_precheck']=validate_count(video_server.expected_physical_calls)\n        policy=StagePolicy(result,lambda:runtime,base)")
    ref=BASE/'candidates/M398-tail-reference-01/m398_tail_reference_gate.py'
    video=ref.read_text(encoding='utf-8');start=video.index('        from m368_head_observer import bind as bind_head');end=video.index('        result[\'boot_unchanged\']',start)
    region=video[start:end].replace('M398','M402').replace('m368_head_observer','m366_head_observer')
    region=once(region,"            if capture_scope is None:raise RuntimeError('Original capture scope missing')\n            capture_scope.family(layer,name,values,output)\n",'')
    region=once(region,'            nonlocal capture_scope','            nonlocal layer_scope')
    region=once(region,'            capture_scope=LastLayerReferenceCapture(model,policy,resident,EVIDENCE,enabled=True)', '            layer_scope=LastLayerTailScope(model,policy,resident,tokens=159,enabled=True)')
    region=region.replace('capture_scope','layer_scope').replace('RetainedReferenceOwnerError','RetainedTailOwnerError')
    region=once(region,"            layer_scope.close()\n            result['reference_capture']=layer_scope.report()\n            del prefill_function", "            del prefill_function\n            layer_scope.close()\n            result['tail_scope']=layer_scope.report()")
    region=region.replace("result['tail_candidate_executed']=False","result['tail_candidate_executed']=True")
    region=once(region,"        policy.capture('before-original-video-stream',True);policy.begin_sampling()", "        if m276_video_runtime._server is not video_server:raise RuntimeError('Stream server identity changed')\n        count_scope=VideoCountScope(video_server,resident,enabled=True)\n        count_ref=weakref.ref(count_scope)\n        policy.capture('before-original-video-stream',True);policy.begin_sampling()")
    region=once(region,"        policy.capture('after-original-video-stream',True);policy.stop_sampling()", "        policy.capture('after-original-video-stream',True);policy.stop_sampling()\n        count_scope.close();result['count_scope']=count_scope.report();count_scope=None\n        if count_ref() is not None:raise RetainedTailOwnerError('Closed count owner retained')\n        result['count_scope_weakref_dead']=True")
    region=region.replace("row['logical_calls']!=778","row['logical_calls']!=766").replace('PASS_M402_ORIGINAL_TAIL_REFERENCE','PASS_M402_TAIL_VIDEO_NUMERICAL')
    region=once(region,"        result['reference_capture_pass']=True\n        result['candidate_numerical_pass']=False", "        result['candidate_numerical_pass']=True\n        result['candidate_full_model_executed']=True\n        expected_transactions=expected['transactions']\n        if len(result['transactions'])!=len(expected_transactions):raise RuntimeError('Retained transaction count differs')\n        for actual,wanted in zip(result['transactions'],expected_transactions):\n            for key,value in wanted.items():\n                if key not in ('snapshot','elapsed_s') and actual[key]!=value:raise RuntimeError('Retained transaction identity differs: '+key)\n        del token,logits,kv,frames,request\n        captured.clear()")
    begin=gate.index('        from m366_head_observer import bind as bind_head');stop=gate.index("        result['boot_unchanged']",begin)
    gate=gate[:begin]+region+gate[stop:]
    gate=once(gate,'unsafe=unsafe or layer_scope is not None','unsafe=unsafe or layer_scope is not None or count_scope is not None')
    gate=gate.replace('PASS_M402_TAIL_TEXT_NUMERICAL','PASS_M402_TAIL_VIDEO_NUMERICAL')
    gate=once(gate,"experiment_scope='Original full runtime/seven DMA retained; fixed30 complete36-layer Prefill and full LM head; final batch selector only; no vision/video, no PS prefetch/extra DMA; production policy unchanged'", "experiment_scope='Original fixed159 video/full36 Prefill/head; only final-layer last31 attention_out/gate_up/mlp_down; complete QKV/Attention/KV; sealed seven DMA; no other optimization; production policy unchanged'")
    gate=once(gate,"'Fixed30 complete36-layer/head numerical closure only; next separately prepare fixed159 video. No performance unlocked.'", "'Fixed159 candidate numerical/lifetime closure only; separate lightweight performance gate after raw SHA and three-record synchronization.'")
    assert 'capture_scope' not in gate and 'LastLayerReferenceCapture' not in gate and "row['logical_calls']!=766" in gate
    payload['m402_tail_video_gate.py']=gate.encode('utf-8')
    entry=payload.pop('m401_text_entry.py').decode('utf-8').replace('M401','M402').replace('--enable-tail-text','--enable-tail-video').replace('m401_tail_text_gate_02','m402_tail_video_gate_01').replace('m401_tail_text_gate.py','m402_tail_video_gate.py')
    payload['m402_video_entry.py']=entry.encode('utf-8')
    for old,new in [('m401_export_result.py','m402_export_result.py'),('run_m401_tail_text.sh','run_m402_tail_video.sh')]:
        s=payload.pop(old).decode('utf-8').replace('M401','M402').replace('m401_tail_text_02','m402_tail_video_01').replace('m401_export_result','m402_export_result').replace('m401_text_entry','m402_video_entry').replace('--enable-tail-text','--enable-tail-video').replace('TAIL_TEXT','TAIL_VIDEO').replace('sealed-DMA-fixed30-full36-layer-tail-prefill',SCOPE)
        payload[new]=s.encode('utf-8')
    assembly=payload.pop('m401_assemble.py').decode('utf-8').replace('M401','M402').replace('/home/ubuntu/m401_tail_text_candidate_01','/home/ubuntu/m401_tail_text_candidate_02').replace('8f6e63c18bda343ce365bebab2cb48466d0268472062578527c7580c9d8d687e',sha(OLD/'PACKAGE_MANIFEST.json'))
    payload['m402_assemble.py']=assembly.encode('utf-8')
    contract=payload['m368_video_contract.py'].decode('utf-8').replace('778','766')
    payload['m402_video_contract.py']=contract.encode('utf-8')
    payload['m402_count_scope.py']=(HERE/'m402_count_scope.py').read_bytes()
    payload['M401_TEXT_CLOSURE.json']=(BASE/'runs/M401-tail-text-closure-02/RESULT.json').read_bytes()
    payload['VIDEO_EXPECTED.json']=(BASE/'runs/M402-tail-video-contract-01/EXPECTED_VIDEO.json').read_bytes()
    for name in ('LAYER_EXPECTED.json',):payload.pop(name)
    # Pin the derived reference with its already synchronized contract SHA.
    plan=json.loads((BASE/'runs/M402-tail-video-contract-01/RESULT.json').read_bytes())
    import hashlib
    assert hashlib.sha256(payload['VIDEO_EXPECTED.json']).hexdigest()==plan['expected_video_sha256']
    references=[]
    for name,data in payload.items():
        if not name.endswith('.py'):continue
        tree=ast.parse(data.decode('utf-8'),feature_version=(3,10))
        if name not in ('m402_tail_video_gate.py','m402_video_entry.py'):continue
        for node in ast.walk(tree):
            if isinstance(node,ast.BinOp) and isinstance(node.op,ast.Div) and isinstance(node.left,ast.Name) and node.left.id=='HERE' and isinstance(node.right,ast.Constant) and isinstance(node.right.value,str):
                assert node.right.value in payload or node.right.value=='PACKAGE_MANIFEST.json',(name,node.right.value)
                references.append([name,node.right.value])
    PKG.mkdir(parents=True,exist_ok=True)
    for name,data in payload.items():atomic(PKG/name,data,immutable=True)
    rows=[dict(path=p.name,bytes=p.stat().st_size,sha256=sha(p)) for p in sorted(PKG/n for n in payload)]
    atomic(PKG/'SHA256SUMS',''.join(r['sha256']+'  '+r['path']+'\n' for r in rows).encode('ascii'),immutable=True)
    rows.append(dict(path='SHA256SUMS',bytes=(PKG/'SHA256SUMS').stat().st_size,sha256=sha(PKG/'SHA256SUMS')))
    atomic(PKG/'PACKAGE_MANIFEST.json',encoded(dict(schema='M402-fixed159-last-layer-tail-v1',files=rows,file_count=len(rows),total_bytes=sum(r['bytes'] for r in rows))),immutable=True)
    print(json.dumps(dict(status='ASSEMBLED_REQUIRES_ACTUAL_PATH_AND_RECOVERY_TESTS',manifest_sha256=sha(PKG/'PACKAGE_MANIFEST.json'),file_count=len(rows),total_bytes=sum(r['bytes'] for r in rows),references=references,board_run=False)))

if __name__=='__main__':main()
