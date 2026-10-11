"""Only new integration/strict saved bytes, with explicitly fake hardware."""
import ast,base64,copy,hashlib,importlib.util,io,json,shutil,subprocess,sys
from unittest.mock import patch
import m351_workflow as w
from m441_host_io08 import atomic
from m441_prepare_layer09 import verify_package,once
import m441_performance_collect09 as c

def fixture():
    board=json.loads((w.ROOT/'deployment/mage_vl4b/BOARD_GATE_RESULT.json').read_bytes())
    old=board['latest_m437_natural_IO_board'];assert w.sha(w.ROOT/old['result'])==old['sha256']
    r=json.loads((w.ROOT/old['result']).read_bytes());chosen=next(s for s in r['samples'] if s['variant']=='B')
    samples=[]
    for oldsample in r['samples']:
        s=copy.deepcopy(chosen)
        for k in ('index','variant','phase','phase_index'):s[k]=oldsample[k]
        s['kernel_build']='0x4D333537' if s['variant']=='A' else '0x4D343431';s['final_snapshot']['ap_return']=int(s['kernel_build'],16)
        samples.append(s)
    perf=json.loads((c.PKG/'PERFORMANCE_PLAN.json').read_bytes())
    r.update(status='PASS_M441P_NATURAL_IO_MEASUREMENTS_COLLECTED',gate_level='same-visual-kernel-complete-request-performance',manifest_sha256=w.sha(c.PKG/'PACKAGE_MANIFEST.json'),build_id='0x4D343431',fpga_transactions=12813,completed_visual_physical=3432,samples=samples,warmup_samples=samples[:4],formal_samples=samples[4:],natural_IO_protocol_sha256=perf['protocol_sha256'],m441_video_numerical_source_sha256=perf['m441_video_sha256'],kernel_switch_minimal_attempts=8,kernel_transitions=[],kernel_switch_environment=[])
    r['final_snapshot']['ap_return']=r['same_overlay_minimal_proof']['snapshot']['ap_return']=0x4d343431
    prior=0x4d343431
    for index,var in ((1,'A'),(2,'B'),(4,'A'),(6,'B'),(8,'A'),(9,'B'),(10,'A'),(12,'B')):
        build=0x4d333537 if var=='A' else 0x4d343431
        before=copy.deepcopy(r['final_snapshot']);before['ap_return']=prior;after=copy.deepcopy(before);after['ap_return']=build
        r['kernel_transitions'].append(dict(index=index,variant=var,from_build=prior,to_build=build,before_snapshot=before,completed_snapshot=after,completed=True,full_output_exact=True,original_buffer_identities_preserved=True,extra_DMA=0,outside_request_timer=True))
        r['kernel_switch_environment'].append(dict(index=index,variant=var,manifest_sha256='2e9cbd00d0d01edf05e171674f71f86a94ce389a0658ce6c5466cebb77220d18' if var=='A' else '56253626a550c9c1358e805e6e3ad9b8b03c2fd9c1ff048be87c64c9f04dd5a0',environment_sha256='a'*64))
        prior=build
    return r,old['sha256']

def emit(r):
    raw=(json.dumps(r,ensure_ascii=False,separators=(',',':'),allow_nan=False)+'\n').encode('utf-8');parts=[raw[i:i+900] for i in range(0,len(raw),900)]
    return 'M441P_RESULT_SHA256='+hashlib.sha256(raw).hexdigest()+'\nM441P_SAVED_GATE_RC='+str(r['gate_return_code'])+'\n'+''.join(f'M441P_RESULT_CHUNK={i}/{len(parts)}:'+base64.b64encode(p).decode()+'\n' for i,p in enumerate(parts))+f'M441P_DONE gate_rc={r["gate_return_code"]} export_rc=0\n'

def support():
    verify_package(c.PKG);r,source=fixture();c.check(r);assert c.decode(emit(r))[2]==r
    fail=dict(r,status='FAIL',gate_return_code=1,errors=['explicit fixture']);assert c.decode(emit(fail))[2]==fail
    bads=[]
    for k,v in [('manifest_sha256','0'*64),('build_id','0x4D333537'),('gate_level','natural-IO-complete-request-performance'),('fpga_transactions',12812),('completed_visual_physical',1716),('kernel_switch_minimal_attempts',7),('kernel_transitions',r['kernel_transitions'][:-1]),('kernel_switch_environment',[]),('m441_video_numerical_source_sha256','0'*64),('safe_buffers_released',False),('borrowed_extra_DMA',1),('temperature_measurement_enabled',True),('performance_pass',True),('gate_return_code',False)]:bads.append(emit(dict(r,**{k:v})))
    for k,v in [('to_build',0),('from_build',0),('outside_request_timer',False),('full_output_exact',False),('index',2),('extra_DMA',1),('completed',False)]:
        b=copy.deepcopy(r);b['kernel_transitions'][0][k]=v;bads.append(emit(b))
    for k,v in [('kernel_build','0x4D343431'),('visual_physical_observed',0),('physical_record_SHA_after_timer','0'*64),('language_physical_observed',780)]:
        b=copy.deepcopy(r);b['samples'][0][k]=v;bads.append(emit(b))
    b=copy.deepcopy(r);b['samples'][0]['numerical_SHA_after_timer']['logits']['sha256']='0'*64;bads.append(emit(b))
    bads.extend([emit(r)+emit(r),emit(r).replace('CHUNK=0/','CHUNK=1/'),emit(r).replace('export_rc=0','export_rc=1')])
    for text in bads:
        try:c.decode(text)
        except (ValueError,KeyError,RuntimeError,AssertionError):pass
        else:raise AssertionError('Broken new saved result accepted')
    stage=w.ROOT/'tmp/m441_performance09/component_stage03';stage.mkdir(parents=True,exist_ok=False)
    for p in c.PKG.iterdir():shutil.copyfile(p,stage/p.name)
    for n in ('NUMERIC_FIXTURE.json','ENVIRONMENT_FIXTURE.json'):shutil.copyfile(w.ROOT/'tmp/m43701/component_stage'/n,stage/n)
    test=(w.HERE/'test_m437_trials.py').read_text(encoding='utf-8')
    test=test.replace('import m437_trials as trials','import m441_performance_trials as trials').replace('snap=dict(ap_ctrl=4,ap_return=0x4d333537','snap=dict(ap_ctrl=4,ap_return=0x4d343431')
    test=once(test,"return dict(build_id='0x4D333537',scale_attempts=", "return dict(build_id=f'0x{snap[\"ap_return\"]:08X}',scale_attempts=")
    anchor='        trials.run(engine,runtime,policy,base,here,here,result,patch,[],provider_proxy)'
    switch='''        class FakeSwitch:
            def select(self,variant,index):
                assert result['model_forward_calls']==index-1
                snap['ap_return']=0x4d333537 if variant=='A' else 0x4d343431
                video._server.BUILD_ID=f'0x{snap["ap_return"]:08X}'
                result.setdefault('fake_switch_order',[]).append((variant,index))
        trials.run(engine,runtime,policy,base,here,here,result,patch,[],provider_proxy,FakeSwitch())
        assert ''.join(v for v,i in result['fake_switch_order'])=='ABBAABBABAAB'
        assert all(s['kernel_build']==('0x4D333537' if s['variant']=='A' else '0x4D343431') for s in result['samples'])
        assert all(s['visual_physical_observed']==286 for s in result['samples'])
'''
    test=once(test,anchor,switch.rstrip()).replace("result['completed_visual_physical']==1716","result['completed_visual_physical']==3432")
    atomic(stage/'test_component.py',test.encode('utf-8'),immutable=True)
    cp=subprocess.run([sys.executable,'-B','-X','utf8','-c',"import sys,types;sys.modules['resource']=types.SimpleNamespace(RUSAGE_SELF=0,getrusage=lambda unused:types.SimpleNamespace(ru_majflt=0));sys.path.insert(0,sys.argv[1]);sys.path.append(sys.argv[3]);import test_component;from pathlib import Path;print(test_component.component(Path(sys.argv[2])))",str(stage),str(w.ROOT),str(w.ROOT/'tmp/m43701/component_stage')],capture_output=True,text=True,encoding='utf-8');atomic(stage/'EXECUTION_OUTPUT.txt',(cp.stdout+cp.stderr).encode('utf-8'),immutable=True);assert cp.returncode==0,cp.stdout+cp.stderr
    spec=importlib.util.spec_from_file_location('actual_m441_performance_export',c.PKG/'m441_performance_export.py');ex=importlib.util.module_from_spec(spec);spec.loader.exec_module(ex)
    saved=stage/'BOARD_RESULT_FIXTURE.json';atomic(saved,(json.dumps(r,ensure_ascii=False,separators=(',',':'),allow_nan=False)+'\n').encode('utf-8'),immutable=True);buf=io.StringIO()
    with patch.object(ex,'OUTPUT',saved),patch.object(ex.os,'geteuid',lambda:0,create=True),patch.object(ex.time,'sleep',lambda x:None),patch('sys.stdout',buf):ex.emit_saved()
    assert c.decode(buf.getvalue())[2]==r
    control=w.HERE/'m441_performance_control09.ps1';pwsh='C:/Users/30429/.cache/codex-runtimes/codex-primary-runtime/dependencies/native/powershell/pwsh.exe'
    ctl=subprocess.run([pwsh,'-NoProfile','-File',str(control),'-Mode','SelfTest'],capture_output=True,text=True,encoding='utf-8');assert ctl.returncode==0 and 'M441P_CONTROL_SELFTEST_PASS' in ctl.stdout,ctl.stdout+ctl.stderr
    runner=(c.PKG/'run_m441_performance.sh').read_text();cs=control.read_text();assert 'M441P_ENABLE_INTEGRATED_VIDEO=1' in cs and 'M441P_ENABLE_INTEGRATED_VIDEO:-0' in runner
    # Resolve local and exact pinned external imports; no candidate-wide guess list.
    roots=[c.PKG,w.BASE/'candidates/M368-staged-video-03'];plan=json.loads((c.PKG/'PLAN.json').read_bytes())
    for row in plan['visual_reused_packages']:
        matches=[p.parent for p in (w.BASE/'candidates').glob('*/PACKAGE_MANIFEST.json') if w.sha(p)==row['manifest_sha256']];assert len(matches)==1;roots+=matches
    allowed=set(sys.stdlib_module_names)|{'numpy','torch','pynq','tokenizers'}|set(json.loads((c.PKG/'SOURCE_CLOSURE.json').read_bytes())['modules'])
    for root in roots:verify_package(root);allowed|={p.stem for p in root.glob('*.py')}
    for p in c.PKG.glob('*.py'):
        for n in ast.walk(ast.parse(p.read_text(encoding='utf-8'),feature_version=(3,10))):
            names=[a.name.split('.')[0] for a in n.names] if isinstance(n,ast.Import) else [(n.module or '').split('.')[0]] if isinstance(n,ast.ImportFrom) else []
            assert all(not name or name in allowed for name in names),(p.name,names)
    out=w.BASE/'runs/M441-complete-request-performance-support-09';v=dict(status='PASS_M441_PERFORMANCE_SUPPORT09',manifest_sha256=w.sha(c.PKG/'PACKAGE_MANIFEST.json'),original_stream_AST_and_actual_new_trials_12_requests=True,both_variants_286_visual_and_781_language=True,all_kernel_selection_outside_stream=True,collector_fixture_explicit_not_board=True,fixture_source_sha256=source,negative_collector_checks=len(bads),actual_exporter_decoder=True,controller_deliberate_failure_collects=True,recursive_import_missing=0,hardware_faked=True,board_executed=False,performance_pass=False,files=[dict(path=p.relative_to(w.ROOT).as_posix(),sha256=w.sha(p)) for p in [control,w.HERE/'m441_performance_collect09.py',w.HERE/'m441_kernel_switch09.py',__file__ and w.HERE/'m441_performance_support09.py']])
    atomic(out/'COMPONENT_OUTPUT.txt',(cp.stdout+cp.stderr+ctl.stdout+ctl.stderr).encode('utf-8'),immutable=True);atomic(out/'RESULT.json',w.encoded(v),immutable=True);d=w.sha(out/'RESULT.json')
    w.sync('latest_m441_complete_request_support',dict(status=v['status'],result=(out/'RESULT.json').relative_to(w.ROOT).as_posix(),sha256=d,manifest_sha256=v['manifest_sha256']),f'## M441 完整请求支持09（2026-10-09）\n\nSHA {d}；实际原stream AST与新12次调度、双方286视觉/781语言、核选择在stream外、计时后数值、{len(bads)}破坏回收负例/实际exporter/控制故意失败收集通过；模型/设备/环境明确fake。原数学/生命周期闭包missing0，非板端或性能。')
    print(v['status'],d)

def receipt():
    logs=w.ROOT/'tmp/m441_performance09';a=logs/'assembly.log';s=logs/'upload_syntax.log'
    assert 'M441P_ALL_PAYLOAD_SHA_VERIFIED_NO_GATE' in a.read_text(encoding='utf-8-sig') and '__M441P_ASSEMBLY_RC_0__' in a.read_text(encoding='utf-8-sig') and '__M441P_SYNTAX_RC_0__' in s.read_text(encoding='utf-8-sig')
    out=w.BASE/'runs/M441-complete-request-performance-transfer-09';v=dict(status='PASS_M441_PERFORMANCE_TRANSFER_ONLY09',manifest_sha256=w.sha(c.PKG/'PACKAGE_MANIFEST.json'),logs=[dict(path=p.relative_to(w.ROOT).as_posix(),sha256=w.sha(p)) for p in sorted(logs.glob('*.log'))],all_payload_SHA_verified=True,root_bash_n=True,board_executed=False,performance_pass=False)
    atomic(out/'RESULT.json',w.encoded(v),immutable=True);d=w.sha(out/'RESULT.json')
    w.sync('latest_m441_complete_request_transfer',dict(status=v['status'],result=(out/'RESULT.json').relative_to(w.ROOT).as_posix(),sha256=d,manifest_sha256=v['manifest_sha256']),f'## M441 完整请求传输09（2026-10-09）\n\nSHA {d}；manifest先发900B逐文件SHA和完整root组装/bash-n通过。未执行；下一步一次固定4＋8，已有attempt只Collect。')
    print(v['status'],d)

if __name__=='__main__':
    if sys.argv[1:]==['receipt']:receipt()
    else:support()
