"""Freeze a four-window persistent worker from the proven board07 runtime."""
import ast,json,sys
from pathlib import Path
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1]
sys.path.insert(0,str(ROOT/'experiments/augmented_student_20261025'))
from common_joint import read,sha,save,relative,RUNS,OPT
TASK=Path(__file__).resolve().parent
BP='M523-fixed-demo-pruning-128'

def main():
    for name in ('CURRENT_STATE.md','docsMILESTONES.md','DEPLOYMENT_OPERATION_MISTAKES_REVIEW.md','deployment/mage_vl4b/BOARD_GATE_RESULT.json'):(ROOT/name).read_text(encoding='utf-8-sig')
    old=OPT/'candidates/M523-fixed-demo-subset-board-07';oldcap=OPT/'candidates/M523-fixed-demo-subset-control-07'
    pkg=OPT/'candidates/M529-campus-persistent-worker-01';cap=OPT/'candidates/M529-campus-worker-control-01';assert not pkg.exists() and not cap.exists()
    source={}
    for r in read(old/'PACKAGE_MANIFEST.json')['files']:
        file=old/r['path'];assert sha(file)==r['sha256'];raw=file.read_bytes()
        if file.suffix=='.py':raw=raw.decode().replace('m523_fixed_demo_subset07','m529_campus_worker01').encode()
        source[r['path']]=raw
    source['worker_protocol.py']=(TASK/'worker_protocol.py').read_bytes()
    t=source['board_demo_trial.py'].decode()
    a="        assert plan['new_full_forwards_budget']==6 and len(plan['demo_requests'])==4"
    assert t.count(a)==1;t=t.replace(a,"        assert plan['new_full_forwards_budget']==8 and len(plan['demo_requests'])==4")
    a="""        requests=plan['demo_requests'];schedule=[]
        for r in requests:schedule.append(('VALID_B_'+r['id'],'B',r))
        schedule.extend([(label,arm,requests[0]) for label,arm in [('HOT_B1','B'),('HOT_B2','B')]])
        assert len(schedule)==6;expected={('A',k):z for k,z in plan['prior_A_numerical_identity'].items()};samples=[];saved_logits_bytes=0"""
    b="""        from worker_protocol import jobs,emit
        requests=plan['demo_requests']
        def schedule():
            for r in requests:yield 'VALID_B_'+r['id'],'B',r,None
            self.result['fixed4_warmup_complete']=True
            yield from jobs(requests,maximum=4,idle_seconds=300)
        expected={('A',k):z for k,z in plan['prior_A_numerical_identity'].items()};samples=[];saved_logits_bytes=0"""
    assert a in t;t=t.replace(a,b)
    t=t.replace("first_token_forward_budget=6,total_prefill_budget=6","first_token_forward_budget=8,total_prefill_budget=8")
    a='        for label,arm,request in schedule:';assert a in t;t=t.replace(a,'        for label,arm,request,ui_job in schedule():')
    a="            print('FIXED_DEMO_TTFT_SAVED',label,record['first_token_wall_s'],raw,correct,flush=True)";assert a in t
    b=a+"""
            if ui_job is not None:
                proof=dict(status='COMPLETE_FIXED_WINDOW_REAL_BOARD_REQUEST_OWNER_STILL_LIVE',primary_rc=0,ui_job_id=ui_job['id'],case_id=request['id'],frame_sha256=request['frame_sha256'],package_manifest_sha256=plan['base_model_manifest_sha256'],software_delta_manifest_sha256=sha(own/'PACKAGE_MANIFEST.json'),actual_full_vocab=151936,argmax_verified=True,physical_calls=len(native),visual_physical_calls=len(visual_rows),decision=answer,raw_token=raw,TTFT_s=record['first_token_wall_s'],prepare_s=record['prepare_s'],prefill_s=record['prefill_s'],logits_sha256=sha(folder/'first_logits.npy'),source_sample_sha256=sha(folder/'SAMPLE.json'),fixed_expected_correct=correct,completed_request=True,owner_released=False,stable_restored=False,scope='Current completed request; original seven buffers intentionally live for next bounded job')
                save(folder/'UI_RESULT.json',proof);emit('RESULT',proof)
"""
    t=t.replace(a,b)
    start=t.index("        hot=[s for s in samples if not s['validation']]");end=t.index('    def close(self):',start)
    t=t[:start]+"""        assert 4<=len(samples)<=8 and self.learned_head.calls==len(samples)
        self.result.update(total_prefills_returned=len(samples),first_token_samples_returned=len(samples),all4_fixed_demo_B_correct=all(s['answer_correct'] for s in samples),learned_head_calls=self.learned_head.calls,learned_head_total_s=self.learned_head.elapsed_s,ui_jobs_returned=len(samples)-4,production_promoted=False,heldout_quality_proven=False)
"""+t[end:]
    source['board_demo_trial.py']=t.encode()
    text=source['native.py'].decode().replace('limit=24<<20','limit=12<<20')
    a="assert result['model_forwards']==6 and result['total_prefills_returned']==6 and result['input_T32_blocks']==4";assert a in text
    text=text.replace(a,"assert 4<=result['model_forwards']==result['total_prefills_returned']<=8 and result['input_T32_blocks']==4 and result['decode_calls']==0 and result['all4_fixed_demo_B_correct']")
    text=text.replace('COMPLETE_TRAINED_HEAD_V10L18_FIXED_DEMO_PENDING_AUDIT','COMPLETE_M529_FIXED4_PERSISTENT_WORKER_PENDING_SAVED_AUDIT');source['native.py']=text.encode()
    before=ast.parse((old/'native.py').read_text());after=ast.parse(text)
    for name in ('Lifecycle','persist','emit','retain','metadata_reference','safe','must_retain','environment','eligible','finish'):
        node=lambda tree:ast.dump(next(n for n in ast.walk(tree) if isinstance(n,(ast.ClassDef,ast.FunctionDef)) and n.name==name),include_attributes=False)
        assert node(before)==node(after),name
    p=json.loads(source['DEMO_BOARD_PLAN.json']);p.update(status='FROZEN_M529_PERSISTENT_FIXED4_REAL_INFERENCE',new_full_forwards_budget=8,output_root='/home/ubuntu/tellme_results/m529_campus_worker01',required_available_bytes=84<<20,base_model_manifest_sha256=sha(old/'PACKAGE_MANIFEST.json'),persistent_worker=dict(warmup_fixed_cases=4,max_web_jobs=4,per_job_new_nonce=True,only_fixed_four_frames=True,idle_seconds=300,max_physical_scope_unchanged=True,no_Decode=True,no_answer_lookup=True),UI_scope_sha256=sha(TASK/'COMPETITION_SCOPE.json'))
    source['DEMO_BOARD_PLAN.json']=(json.dumps(p,indent=2)+'\n').encode()
    text=source['board_component.py'].decode();a='    return value\n';assert text.count(a)==1
    text=text.replace(a,"    from worker_protocol import tests\n    value['worker_protocol']=tests()\n"+a);source['board_component.py']=text.encode()
    for name,raw in source.items():
        if name.endswith('.py'):compile(raw,name,'exec')
    def seal(folder):
        files=[dict(path=f.relative_to(folder).as_posix(),bytes=f.stat().st_size,sha256=sha(f)) for f in sorted(folder.rglob('*')) if f.is_file()]
        assert all((folder/r['path']).stat().st_nlink==1 for r in files)
        save(folder/'PACKAGE_MANIFEST.json',dict(files=files,file_count=len(files),total_bytes=sum(r['bytes'] for r in files)))
    pkg.mkdir();cap.mkdir()
    for name,raw in source.items():
        file=pkg/name;file.parent.mkdir(parents=True,exist_ok=True);file.open('xb').write(raw)
    seal(pkg)
    for row in read(oldcap/'PACKAGE_MANIFEST.json')['files']:
        text=(oldcap/row['path']).read_text(encoding='utf-8')
        for a,b in [('m523_fixed_demo_subset_package07','m529_campus_worker_package01'),('m523_fixed_demo_subset_control07','m529_campus_worker_control01'),('m523_fixed_demo_subset07','m529_campus_worker01'),('m523_fixed_demo_ingress07','m529_campus_worker_ingress01'),('m523_fixed_demo_subset_import07','m529_campus_worker_import01')]:text=text.replace(a,b)
        if row['path']=='pc_network.ps1':text=text.replace('m523_fixed_demo_subset07','m529_campus_worker01')
        (cap/row['path']).open('x',encoding='utf-8',newline='\n').write(text)
    seal(cap)
    value=read(RUNS/(BP+'-board-protocol-07/RESULT.json'));value.update(status=p['status'],package=relative(pkg),capsule=relative(cap),remote='/dev/shm/m529_campus_worker_package01',control_remote='/dev/shm/m529_campus_worker_control01',manifest_sha256=sha(pkg/'PACKAGE_MANIFEST.json'),capsule_manifest_sha256=sha(cap/'PACKAGE_MANIFEST.json'),runner_sha256=sha(pkg/'run.sh'),ingress_sha256=sha(cap/'ingress.py'),probe_sha256=sha(cap/'probe.py'),source_sha256=sha(__file__),new_full_forwards_budget=8,head_and_fixed_inputs_unchanged=True,model_manifest_sha256=p['base_model_manifest_sha256'])
    assert all(sha(pkg/(n+'.npy'))==sha(old/(n+'.npy')) for n in ('A','B'))
    out=RUNS/'M529-campus-persistent-worker-protocol-01/RESULT.json';save(out,value)
    sys.path.insert(0,str(ROOT/'scripts/optimization'));from m455456_workflow02 import synchronized
    h=sha(out);synchronized('latest_m529_persistent_worker_protocol01',dict(status=value['status'],result=relative(out),sha256=h,board=False),'## M529固定演示COM3持久工作器协议准备\n\nRESULT SHA '+h+'；同M525原10V18L/学习头/四窗口，启动先真实4窗口正确预热，再最多4个网页nonce绑定任务；输入仅512字节数据JSON、固定case和新UUID，300秒idle正常结束，0Decode。每个请求重选VisionSubset清空观察计数，原M527第二前缀计数失败不复用。七owner/失败保留/稳定恢复/四clock安全AST逐项一致，12MiB JSON+6MiB logits+2MiB原生元数据+64MiB保留=84MiB存储准入，需新只读存储。0本次模型/板命令；后续先CPU及A53组件，再固定四窗口+网页真实任务门禁，不能先称网页接通。')
    print(value['status'],h,flush=True)
if __name__=='__main__':main()
