"""M544 Web worker: identical M543 math/owners; bounded live RGB input and jobs."""
import ast,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
from common_fix import *
sys.path.insert(0,str(ROOT/'scripts/optimization'))
from m455456_workflow02 import synchronized
def main():
    audit=RUNS/'M543-repaired-campus-board-audit-02/RESULT.json';a=read(audit);assert a['primary_rc']==0 and a['validation_correct']==6 and a['all7owners_reverse_released']
    old=OPT/'candidates/M543-repaired-campus-fixed-board-02';oldcap=OPT/'candidates/M543-repaired-campus-control-02'
    assert sha(old/'PACKAGE_MANIFEST.json')==a['package_manifest_sha256']
    contents={r['path']:(old/r['path']).read_bytes() for r in read(old/'PACKAGE_MANIFEST.json')['files']}
    for row in read(old/'PACKAGE_MANIFEST.json')['files']:assert sha(old/row['path'])==row['sha256']
    t=contents['board_demo_trial.py'].decode();before_trial=t
    def change(x,y):
        nonlocal t
        assert t.count(x)==1,x[:100];t=t.replace(x,y)
    change("        budget=plan['new_full_forwards_budget'];assert budget==len(plan['request_schedule']) and len(plan['demo_requests'])==6","        budget=plan['new_full_forwards_budget'];assert budget==13 and len(plan['demo_requests'])==1\n        from live_protocol import Channel\n        session=os.environ['CAMPUS_SESSION_ID'];channel=Channel(sha(own/'PACKAGE_MANIFEST.json'),session);self.live_channel=channel")
    change("        schedule=[(r['label'],r['arm'],by_id[r['request_id']]) for r in plan['request_schedule']]\n        assert len(schedule)==budget and all(arm=='B' for _,arm,_ in schedule)","        def schedule():\n            yield 'VALID_WARMUP','B',requests[0],None\n            for label,arm,request,job,frame in channel.jobs():\n                frames[request['id']]=frame\n                yield label,arm,request,job")
    change('        for label,arm,request in schedule:','        for label,arm,request,ui_job in schedule():')
    change("answer=classify(raw);correct=answer==request['expected_decision']","answer=classify(raw);truth_correct=(answer==request['expected_decision']) if ui_job is None else None;correct=(truth_correct is True) if ui_job is None else answer in ('Yes','No')")
    x="            if label.startswith('VALID_'):expected[key]=numerical\n            elif arm=='B':assert numerical==expected[key],'Candidate hot identity differs from own validation request'\n            else:assert numerical==plan['parent_full_numerical_identity'][request['id']]"
    change(x,"            if ui_job is None:expected[key]=numerical\n            else:assert input_record['frame_raw_sha256']==request['pixel_sha256'], 'Actual received RGB input differs'")
    change('answer_correct=correct,natural_EOS_claimed=False','answer_correct=truth_correct,answer_valid=correct,natural_EOS_claimed=False')
    x="            for name,data in [('SAMPLE.json',record),('INPUT.json',input_record),('NUMERICAL_IDENTITY.json',numerical),('WEIGHT_STAGE_PROFILE.json',weight),('PARSER_PROFILE.json',parse),('FULL_LOGITS_PROOF.json',logits_proof),('PHYSICAL_TRANSACTIONS.json',dict(instrumented=native,manual_visual=visual_rows)),('STRICT_VISUAL_COMPLETION.json',dict(observations=strict))]:save(folder/name,data)"
    y="""            trace_bytes=json.dumps(dict(instrumented=native,manual_visual=visual_rows,strict=strict),sort_keys=True,separators=(',',':')).encode()
            physical_proof=dict(language_head_calls=len(native),visual_calls=len(visual_rows),all_visual_strict=all(r['strict_completed'] for r in strict),full_trace_sha256=hashlib.sha256(trace_bytes).hexdigest())
            for name,data in [('SAMPLE.json',record),('INPUT.json',input_record),('NUMERICAL_IDENTITY.json',numerical),('FULL_LOGITS_PROOF.json',logits_proof),('PHYSICAL_COMPLETION_PROOF.json',physical_proof),('SCHEDULING_SUMMARY.json',dict(weight=weight['summary'],prefetch=weight['prefetch'],parser=record['parse_summary']))]:save(folder/name,data)"""
    change(x,y)
    x="            print('FIXED_DEMO_TTFT_SAVED',label,record['first_token_wall_s'],raw,correct,flush=True)"
    y=x+"""
            if ui_job is not None:
                ui_proof=dict(status='COMPLETE_M544_LIVE_REQUEST_ORIGINAL_OWNERS_STILL_LIVE',primary_rc=0,session=session,ui_job_id=ui_job['id'],case_id=request['id'],frame_sha256=request['frame_sha256'],pixel_sha256=request['pixel_sha256'],package_manifest_sha256=sha(own/'PACKAGE_MANIFEST.json'),base_model_manifest_sha256=plan['base_model_manifest_sha256'],actual_full_vocab=151936,argmax_verified=True,physical_calls=len(native),visual_physical_calls=len(visual_rows),decision=answer,raw_token=raw,TTFT_s=record['first_token_wall_s'],prepare_s=record['prepare_s'],prefill_s=record['prefill_s'],full_logits_sha256=numerical['first_logits'],logits_sha256=numerical['first_logits'],source_sample_sha256=sha(folder/'SAMPLE.json'),completed_request=True,owner_released=False,stable_restored=False,truth_label_not_used_for_live_decision=True)
                save(folder/'UI_RESULT.json',ui_proof);channel.packet('RESULT',ui_proof)
                frames.pop(request['id'],None)
"""
    change(x,y)
    start=t.index("        hot=[s for s in samples if s['label'].startswith('HOT_')]");end=t.index('\n    def close(self):',start)
    t=t[:start]+"""        assert 1<=len(samples)<=budget and self.learned_head.calls==len(samples)
        self.idle()
        self.result.update(total_prefills_returned=len(samples),first_token_samples_returned=len(samples),warmup_correct=samples[0]['answer_correct'] is True,live_jobs_returned=len(samples)-1,learned_head_calls=self.learned_head.calls,learned_head_total_s=self.learned_head.elapsed_s,production_promoted=False,heldout_quality_proven=False,session=session)
"""+t[end:]
    contents['board_demo_trial.py']=t.encode();contents['live_protocol.py']=(ROOT/'apps/campus_guard/live_protocol.py').read_bytes()
    n=contents['native.py'].decode();before_native=n
    n=n.replace("root=Path('/home/ubuntu/tellme_results/m543_demo_repair02');out=root/args.mode","session=os.environ['CAMPUS_SESSION_ID'];assert len(session)==32 and all(c in '0123456789abcdef' for c in session)\n    root=Path('/home/ubuntu/tellme_results/m544_live_sessions')/session;out=root/args.mode")
    n=n.replace('budget=LogBudget(out,timing_module.save,result,limit=1<<20)',"budget=LogBudget(out,timing_module.save,result,limit=read(own/'DEMO_BOARD_PLAN.json')['diagnostic_limit_bytes'])")
    x="        count_plan=read(own/'DEMO_BOARD_PLAN.json');expected_count=count_plan['new_full_forwards_budget']\n        assert expected_count==len(count_plan['request_schedule'])\n        assert result['model_forwards']==result['total_prefills_returned']==result['first_token_samples_returned']==expected_count\n        assert result['input_T32_blocks']==4"
    y="""        count_plan=read(own/'DEMO_BOARD_PLAN.json');expected_max=count_plan['new_full_forwards_budget']
        assert expected_max==1+count_plan['persistent_worker']['max_live_jobs']
        assert 1<=result['model_forwards']==result['total_prefills_returned']==result['first_token_samples_returned']<=expected_max
        assert result['warmup_correct'] and result['model_forwards']==1+result['live_jobs_returned']
        assert result['input_T32_blocks']==4 and result['decode_calls']==0"""
    assert n.count(x)==1;n=n.replace(x,y).replace('COMPLETE_M543_REPAIRED_FIXED_CAMPUS_PENDING_AUDIT','COMPLETE_M544_LIVE_WORKER_NORMAL_STOP_PENDING_AUDIT');contents['native.py']=n.encode()
    def node(s,name):return next(a for a in ast.walk(ast.parse(s)) if isinstance(a,(ast.FunctionDef,ast.ClassDef)) and a.name==name)
    for name in ['Lifecycle','persist','emit','retain','metadata_reference','environment','safe','eligible','must_retain','finish']:
        assert ast.dump(node(before_native,name))==ast.dump(node(n,name)),name
    p=json.loads(contents['DEMO_BOARD_PLAN.json']);p.update(status='FROZEN_M544_CURRENT_REPAIRED_LIVE_RGB_WORKER',new_full_forwards_budget=13,demo_requests=[p['demo_requests'][0]],request_schedule=[dict(label='VALID_WARMUP',arm='B',request_id=p['demo_requests'][0]['id'])],hot_repeat_labels=[],output_root='/home/ubuntu/tellme_results/m544_live_sessions',base_model_manifest_sha256=a['package_manifest_sha256'],parent_fixed_board_audit_sha256=sha(audit),diagnostic_limit_bytes=512<<10,required_available_bytes=(64<<20)+(512<<10)+(1<<20),persistent_worker=dict(warmup_requests=1,max_live_jobs=12,idle_seconds=1200,max_cached_RGB_frames=4,MAX_UART_LINE=1024,raw_RGB_transfer_before_play=True,no_expected_answer_in_live_jobs=True,normal_stop_is_data_only=True),storage_admission_note='New live format keeps SAMPLE/input/identity/full-vocab proof/physical completion SHA/scheduling aggregates only.512KiB diagnostics +1MiB native/metadata +64MiB reserve. Full original M543 detailed diagnostics remain preserved; no existing evidence deletion.')
    contents['DEMO_BOARD_PLAN.json']=(json.dumps(p,ensure_ascii=False,indent=2)+'\n').encode()
    launch=contents['launcher.py'].decode();launch=launch.replace("plan=json.loads((own/'DEMO_BOARD_PLAN.json').read_bytes());out=Path(plan['output_root'])","plan=json.loads((own/'DEMO_BOARD_PLAN.json').read_bytes());session=os.environ['CAMPUS_SESSION_ID'];assert len(session)==32 and all(c in '0123456789abcdef' for c in session);out=Path(plan['output_root'])/session")
    contents['launcher.py']=launch.encode()
    run=contents['run.sh'].decode().replace('test "$#" -eq 2','test "$#" -eq 3\n[[ "$3" =~ ^[0-9a-f]{32}$ ]]\nexport CAMPUS_SESSION_ID="$3"');contents['run.sh']=run.encode()
    comp=contents['board_component.py'].decode().replace('m543_demo_repair_component02.json','m544_live_component01.json')
    assert comp.count('    return value\n')==1;comp=comp.replace('    return value\n',"    from live_protocol import tests\n    value['live_frame_protocol']=tests()\n    return value\n");contents['board_component.py']=comp.encode()
    pkg=OPT/'candidates/M544-campus-live-worker-01';cap=OPT/'candidates/M544-campus-live-control-01';pkg.mkdir(exist_ok=False);cap.mkdir(exist_ok=False)
    for name,raw in contents.items():
        if name.endswith('.py'):compile(raw.decode(),name,'exec')
        f=pkg/name;f.parent.mkdir(parents=True,exist_ok=True);f.open('xb').write(raw)
    def seal(d):
        rows=[dict(path=f.relative_to(d).as_posix(),bytes=f.stat().st_size,sha256=sha(f)) for f in sorted(d.rglob('*')) if f.is_file()]
        assert all((d/r['path']).stat().st_nlink==1 and not (d/r['path']).is_symlink() for r in rows)
        save(d/'PACKAGE_MANIFEST.json',dict(files=rows,file_count=len(rows),total_bytes=sum(r['bytes'] for r in rows)))
    seal(pkg)
    mappings={'m543_demo_repair_package02':'m544_live_worker_package01','m543_demo_repair_control02':'m544_live_worker_control01','m543_demo_repair_ingress02':'m544_live_worker_ingress01','m543_demo_repair_import02':'m544_live_worker_import01','tmp/m543_demo_repair02/':'tmp/m544_live_worker01/'}
    for row in read(oldcap/'PACKAGE_MANIFEST.json')['files']:
        f=oldcap/row['path'];raw=f.read_text(encoding='utf-8-sig')
        for x,y in mappings.items():raw=raw.replace(x,y)
        if f.suffix=='.py':compile(raw,str(f),'exec')
        (cap/row['path']).open('xb').write(raw.encode())
    seal(cap)
    out=RUNS/'M544-campus-live-worker-preparation-01/RESULT.json';r=dict(status='PREPARED_M544_LIVE_RGB_WORKER_CPU_AND_A53_PENDING',package=rel(pkg),capsule=rel(cap),manifest_sha256=sha(pkg/'PACKAGE_MANIFEST.json'),capsule_manifest_sha256=sha(cap/'PACKAGE_MANIFEST.json'),runner_sha256=sha(pkg/'run.sh'),ingress_sha256=sha(cap/'ingress.py'),probe_sha256=sha(cap/'probe.py'),remote='/dev/shm/m544_live_worker_package01',control_remote='/dev/shm/m544_live_worker_control01',source_sha256=sha(Path(__file__)),parent_audit_sha256=sha(audit),owner_and_cleanup_AST_unchanged=True,new_full_forward_budget=13,warmup=1,max_live_jobs=12,required_available_bytes=p['required_available_bytes'],board_actions=0,model_forwards=0)
    save(out,r);h=sha(out)
    # Source identification prepares the actual input; never contains an expected answer.
    parent_plan=read(old/'DEMO_BOARD_PLAN.json');profiles={}
    for video_sha in dict.fromkeys(r['video_sha256'] for r in parent_plan['demo_requests']):
        row=next(r for r in parent_plan['demo_requests'] if r['video_sha256']==video_sha)
        profiles[video_sha]=dict(frame=rel(old/row['frame_path']),frame_sha256=row['frame_sha256'],timestamp_ms=row['timestamp_ms'])
    binding=dict(build='M455 / M542修复头 · 10V18L · M544',package_manifest_sha256=r['manifest_sha256'],model_reference_manifest_sha256=a['package_manifest_sha256'],parent_audit=rel(audit),parent_audit_sha256=sha(audit),canonical_inputs=profiles)
    save(ROOT/'apps/campus_guard/LIVE_BINDING.json',binding)
    synchronized('latest_m544_live_worker_preparation01',dict(status=r['status'],result=rel(out),sha256=h,board=False,promoted=False),'## M544真实网页RGB工作器准备\n\nRESULT SHA '+h+'；继承M543当前实板6/6及27.609秒头/身体原字节、原七owner/guard/cleanup AST相同。数据协议1024字节每行/512字节RGB块，先传图准备、播放时新nonce实际推理，1预热+最多12新任务/1200秒idle后正常收尾；实时任务不传预期答案。新日志512KiB+其他1MiB+原64MiB reserve，未删除任何旧证据。尚需CPU实际预算/协议/A53组件及真实网页E2E，不冒充已接通。')
    print(json.dumps(dict(status=r['status'],sha256=h,manifest_sha256=r['manifest_sha256']),indent=2))
if __name__=='__main__':main()
