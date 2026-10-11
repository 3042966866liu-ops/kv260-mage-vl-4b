"""Real array/unchanged CPU math checks; PL/runtime/MMIO explicitly fake."""
import ast,base64,copy,hashlib,json,math,subprocess,sys,tempfile,types
from pathlib import Path
import numpy as np
from m351_workflow import ROOT,BASE,HERE,atomic,encoded,sha,sync
import m415_saved_features as features
import m415_trials as trials
import m415_workflow as workflow
PKG=workflow.PKG
RELEASE=ROOT/'release_staging/kv260-mage-vl-4b-prebuilt-install-20260926-v7'

def reject(fn,labels,label):
    try:fn()
    except (ValueError,RuntimeError,FileNotFoundError):labels.append(label)
    else:raise AssertionError('Rejected condition accepted: '+label)

def cpu_components():
    labels=[]
    video=types.ModuleType('m276_video_runtime');decision=types.ModuleType('m246_knife_binary')
    embedding_path=RELEASE/'deployment/mage_vl4b/m277_m276_fixed_window_board_candidate/m276_video_runtime.py'
    tree=ast.parse(embedding_path.read_text(encoding='utf-8'))
    function=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='latest_input_embeddings')
    source=RELEASE/'deployment/mage_vl4b/m181_m120_video_board_candidate/video_language_runtime.py'
    constants={}
    for n in ast.parse(source.read_text(encoding='utf-8')).body:
        if isinstance(n,ast.Assign) and len(n.targets)==1 and isinstance(n.targets[0],ast.Tuple):
            for target,value in zip(n.targets[0].elts,ast.literal_eval(n.value)):
                if isinstance(target,ast.Name) and target.id in ('HIDDEN','IMAGE_PAD_ID','MAX_CONTEXT','VOCAB'):constants[target.id]=value
        if isinstance(n,ast.Assign) and len(n.targets)==1 and isinstance(n.targets[0],ast.Name) and n.targets[0].id in ('HIDDEN','IMAGE_PAD_ID','MAX_CONTEXT','VOCAB'):
            constants[n.targets[0].id]=ast.literal_eval(n.value)
    assert len(constants)==4
    video.__dict__.update(np=np,**constants)
    exec(compile(ast.Module(body=[function],type_ignores=[]),'unchanged-frozen-latest-input','exec'),video.__dict__)
    decision_path=RELEASE/'deployment/mage_vl4b/m277_m276_fixed_window_board_candidate/m246_knife_binary.py'
    spec=ast.parse(decision_path.read_text(encoding='utf-8'))
    func=next(n for n in spec.body if isinstance(n,ast.FunctionDef) and n.name=='constrained_knife_decision')
    decision.__dict__.update(np=np,math=math,KNIFE_NO_TOKEN_ID=15,KNIFE_YES_TOKEN_ID=16)
    exec(compile(ast.Module(body=[func],type_ignores=[]),'unchanged-frozen-knife-decision','exec'),decision.__dict__)
    ids=json.loads((PKG/'VISUAL_EXPECTED.json').read_bytes())['prompt_token_ids']
    video.tokenize=lambda *args:ids;video.M276_KNIFE_PROMPT='[TELLME_KNIFE_BINARY_V3] Knife visible? Reply exactly 1 for yes or 0 for no:'
    from m368_stage_policy import FAMILIES
    class Model:
        def __init__(self,rt):
            self.runtime=rt;self.grouped_attention_calls=0
            # Explicit sparse embedding fixture; uses the actual frozen embedding function.
            class Embedding:
                def __getitem__(self,indices):return np.zeros((len(indices),2560),np.float32)
            self.embedding=Embedding()
        def _family(self,layer,name,values):return {'output':values.copy()}
        def prefill(self,hidden):
            for layer,name in FAMILIES:self._family(layer,name,np.ones((1,1),np.float32))
            self.grouped_attention_calls+=36
            rt=self.runtime;rt.logical_calls+=778;rt.host_calls+=778
            for i in range(778):rt.attempts.append(dict(layer=None if i>=770 else 0,attempted_shifts=[6],selected_shift=6))
            rt.result['transactions'].extend([dict(method='fake-language') for _ in range(770)]+[dict(method='head-original-execute') for _ in range(8)])
            logits=np.zeros(151936,np.float32);logits[15]=1.0
            kv=types.SimpleNamespace(keys=[np.ones((1,1),np.float32) for _ in range(36)],values=[np.ones((1,1),np.float32) for _ in range(36)])
            return 15,logits,kv
    class Runtime:
        def __init__(self,r):self.result=r;self.logical_calls=self.host_calls=0;self.attempts=[];self.kernel=self.dma=object()
        def evidence(self):return dict(logical_calls=self.logical_calls,host_calls=self.host_calls,scale_retry_count=0,pipeline_retry_launches=0,fused_nonfinite_detections=0,stage_bytes=0,logical_expected_macros=0,expected_macros=0,scale_attempts=copy.deepcopy(self.attempts))
    class Policy:
        def __init__(self,r):self.r=r
        def capture(self,*args):pass
        def begin_sampling(self):pass
        def stop_sampling(self):self.r['sampled_memory']=dict(observer_stopped=True,stop_reason=None)
        def safe(self):return True
    rows=[];modules={name:sys.modules.get(name) for name in ('m276_video_runtime','m246_knife_binary')}
    oldload=trials.load_features
    try:
        sys.modules['m276_video_runtime']=video;sys.modules['m246_knife_binary']=decision
        with tempfile.TemporaryDirectory(dir=BASE/'runs') as tmp:
            here=Path(tmp);r=dict(model_forward_calls=0,transactions=[],saved_feature_identities=[])
            rt=Runtime(r);model=Model(rt);engine=types.SimpleNamespace(language=model,config={'tokenizer':here/'fake-tokenizer'})
            a=np.ones((98,2560),np.float32);b=a.copy();b[-1,-1]=1.01
            hidden=video.latest_input_embeddings(model,ids,a)
            assert hidden.shape==(159,2560) and np.array_equal(hidden[np.flatnonzero(np.array(ids)==video.IMAGE_PAD_ID)],a)
            for layer,name in FAMILIES:rows.append(dict(layer=layer,family=name,input=features.tensor(np.ones((1,1),np.float32)),output={'output':features.tensor(np.ones((1,1),np.float32))}))
            logits=np.zeros(151936,np.float32);logits[15]=1
            expected=dict(input=features.tensor(hidden),families=rows,token=15,logits=features.tensor(logits),grouped_attention_calls=36,keys=[features.tensor(np.ones((1,1),np.float32))]*36,values=[features.tensor(np.ones((1,1),np.float32))]*36,
                logical_calls=778,host_calls=778,retry_count=0,retry_launches=0,nonfinite_detections=0,stage_bytes=0,logical_expected_macros=0,expected_macros=0,
                scale_attempts=[dict(layer=None if i>=770 else 0,attempted_shifts=[6],selected_shift=6) for i in range(778)],language_retries=0,head_retries=0,
                semantic={'token':dict(token_id=15,text='0',knife_verdict='ABSENT',knife_score=decision.constrained_knife_decision(logits)['knife_score'])})
            (here/'VIDEO_EXPECTED.json').write_bytes(encoded({'baseline':expected}));(here/'VISUAL_EXPECTED.json').write_bytes(encoded({'prompt_token_ids':ids}));(here/'PLAN.json').write_bytes(b'{}')
            trials.load_features=lambda *a:([np.ones((98,2560),np.float32)]*2,[])
            restores=[]
            def patch(obj,name,new):restores.append((obj,name,getattr(obj,name)));setattr(obj,name,new)
            trials.run(engine,rt,Policy(r),types.SimpleNamespace(transaction_snapshot=lambda *a:{}),here,here,r,patch,[a,b])
            assert r['original_reference_pass'] and r['decision_consistency_pass'] and r['vision_forward_calls']==0 and r['model_forward_calls']==2 and len(r['samples'])==2 and rt.logical_calls==1556
            for obj,name,old in reversed(restores):setattr(obj,name,old)
            for name in ('original_logits.npy','layer12_candidate_logits.npy'):
                loaded=np.load(here/name,allow_pickle=False);assert features.tensor(loaded)==features.tensor(logits)
                reject(lambda:features.save_array(here/name,loaded),labels,'immutable-'+name)
            altered=logits.copy();altered[16]=2
            q=features.compare_logits(logits,altered,decision.constrained_knife_decision(logits),decision.constrained_knife_decision(altered))
            assert not q['same_constrained_decision'] and q['changed_FP32_words']==1
            for label,bad in [('nonfinite',np.full(151936,np.nan,np.float32)),('short',np.ones(16,np.float32)),('FP64',np.ones(151936,np.float64))]:
                reject(lambda:features.compare_logits(logits,bad,{},{}),labels,label)
            reject(lambda:features.compare_logits(np.zeros_like(logits),np.zeros_like(logits),{},{}),labels,'degenerate')
            changed=rt.evidence();changed['scale_attempts'][0]['selected_shift']=5
            reject(lambda:trials.delta(rt.evidence(),changed),labels,'retry-history-mutation')
            reject(lambda:features.load_features({'M414_raw_sha256':'0'*64},here),labels,'feature-result-identity')
    finally:
        trials.load_features=oldload
        for name,old in modules.items():
            if old is None:sys.modules.pop(name,None)
            else:sys.modules[name]=old
    return dict(actual_frozen_input_embedding_and_constrained_decision=True,actual_new_trial_success_path=True,
        two_real_size_feature_arrays=True,full151936_FP32_logit_arrays=True,original_strict_reference_before_candidate=True,
        fake_PL_runtime_KV_and_memory=True,negative_checks=labels,source_sha256={str(p.relative_to(ROOT)):sha(p) for p in (embedding_path,decision_path,source)})

def main():
    components=cpu_components();m=json.loads((PKG/'PACKAGE_MANIFEST.json').read_bytes())
    for row in m['files']:assert sha(PKG/row['path'])==row['sha256']
    for p in PKG.glob('*.py'):ast.parse(p.read_text(encoding='utf-8'),feature_version=(3,10))
    s=(PKG/'m415_gate.py').read_text(encoding='utf-8')
    assert s.index('head_AST_checked_before_overlay')<s.index('import pynq') and 'Unexpected second visual forward' not in s and 'forbids visual forward' in s
    # Actual frozen head AST transformation, no hardware, before resource allocation.
    sys.path.insert(1,str(BASE/'candidates/M368-staged-video-03'))
    import m368_head_observer
    closure=json.loads((PKG/'SOURCE_CLOSURE.json').read_bytes())
    head=RELEASE/closure['modules']['m230_prefill_runtime']
    tree=ast.parse(head.read_text(encoding='utf-8'));cls=next(n for n in tree.body if isinstance(n,ast.ClassDef) and n.name=='M230PrefillRuntime')
    fn=next(n for n in cls.body if isinstance(n,ast.FunctionDef) and n.name=='_execute')
    actual_source=ast.get_source_segment(head.read_text(encoding='utf-8'),fn)
    m368_head_observer.instrument_source(actual_source)
    failure=dict(status='FAIL',gate_level='saved-feature-fixed159-language-quality',build_id='0x4D333537',manifest_sha256=sha(PKG/'PACKAGE_MANIFEST.json'),gate_return_code=1,performance_pass=False,formal_promotion_allowed=False,errors=['Explicit fixture failure'])
    def wire(r):
        data=encoded(r);parts=[data[i:i+900] for i in range(0,len(data),900)]
        return '\n'.join(['M415_RESULT_SHA256='+hashlib.sha256(data).hexdigest(),'M415_SAVED_GATE_RC='+str(r['gate_return_code'])]+[f'M415_RESULT_CHUNK={i}/{len(parts)}:'+base64.b64encode(v).decode('ascii') for i,v in enumerate(parts)])
    text=wire(failure);assert workflow.decode(text)[2]==failure
    rejects=[]
    for key,value in [('manifest_sha256','0'*64),('build_id','0x4D395832'),('gate_return_code',0),('performance_pass',True),('formal_promotion_allowed',True),('expanded_24_layers',True),('vision_forward_calls',1),('semantic_accuracy_proven',True),('errors',[])]:
        bad=dict(failure,**{key:value});reject(lambda:workflow.decode(wire(bad)),rejects,key)
    for label,bad in [('duplicate',text+'\n'+text),('missing',text.rsplit('\n',1)[0]),('SHA',text.replace('M415_RESULT_SHA256=','M415_RESULT_SHA256=0')),('runner-rc',text+'\nM415_DONE gate_rc=0 export_rc=0')]:
        reject(lambda:workflow.decode(bad),rejects,label)
    pwsh='C:/Users/30429/.cache/codex-runtimes/codex-primary-runtime/dependencies/native/powershell/pwsh.exe'
    checked=subprocess.run([pwsh,'-NoProfile','-File',str(HERE/'m415_control.ps1'),'-Mode','SelfTest'],capture_output=True,text=True,encoding='utf-8')
    if checked.returncode or 'M415_CONTROL_SELF_TEST_PASS' not in checked.stdout:raise RuntimeError(checked.stdout+checked.stderr)
    checked=subprocess.run(['wsl.exe','-d','Ubuntu-24.04','--','/bin/bash','-n','/mnt/c/Users/30429/Desktop/TeLLMe_FPGA_2026/'+(PKG/'run_m415.sh').relative_to(ROOT).as_posix()],capture_output=True)
    if checked.returncode:raise RuntimeError((checked.stdout+checked.stderr).decode('utf-8',errors='replace'))
    r=dict(status='PASS_M415_SAVED_FEATURE_COMPONENT_AND_RECOVERY_SUPPORT',manifest_sha256=sha(PKG/'PACKAGE_MANIFEST.json'),
        components=components,recovery_negative_checks=rejects,actual_frozen_head_AST_check=True,head_source_sha256=sha(head),
        control_failure_collection_selftest=True,bash_syntax=True,Python310_syntax=True,board_run=False,hardware_or_actual_quality_proven=False,
        source_sha256={name:sha(HERE/name) for name in ('m415_saved_features.py','m415_trials.py','m415_workflow.py','m415_control.ps1','m415_support.py')})
    out=BASE/'runs/M415-saved-feature-support-01/RESULT.json';atomic(out,encoded(r),immutable=True)
    sync('latest_m415_saved_feature_support',dict(status=r['status'],result=out.relative_to(ROOT).as_posix(),sha256=sha(out),manifest_sha256=r['manifest_sha256']),
         f'## M415 保存特征语言组件/回收检查（2026-10-06）\n\nSHA {sha(out)}；冻结原embedding/受限判断函数和实际新两次trial成功分支执行、98×2560/151936实际尺寸数组、完整原参考先行、文件有界保存及{len(components["negative_checks"])}负例；PL/runtime/KV/memory明确fake。{len(rejects)}回收拒绝检查、冻结实际head AST、Python3.10、bash-n和故意控制失败仍收集通过。未上板/质量/性能，manifest {r["manifest_sha256"]}，下一步同COM3上传/一次Run。')
    print('M415_SUPPORT_SYNC',sha(out),len(components['negative_checks']),len(rejects))
if __name__=='__main__':main()
