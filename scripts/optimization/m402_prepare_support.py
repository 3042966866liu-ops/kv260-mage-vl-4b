"""Offline controller/collector path checks; all model-result fixtures are fakes."""
import ast
import base64
import contextlib
import copy
import importlib.util
import io
import json
import subprocess
import tempfile
from pathlib import Path
from unittest.mock import patch
from m351_workflow import ROOT,HERE,BASE,sha,atomic,encoded,sync
from m402_prepare_video import PKG,OLD,SCOPE

def namespace(path):
    ns={'__file__':str(path),'__name__':'offline_explicit_fixture'}
    exec(compile(path.read_bytes(),str(path),'exec'),ns)
    return ns

def envelope(r):
    raw=encoded(r)
    import hashlib
    pieces=[raw[i:i+900] for i in range(0,len(raw),900)]
    return 'M402_RESULT_SHA256='+hashlib.sha256(raw).hexdigest()+'\nM402_SAVED_GATE_RC='+str(r['gate_return_code'])+'\n'+''.join(f'M402_RESULT_CHUNK={i}/{len(pieces)}:'+base64.b64encode(p).decode('ascii')+'\n' for i,p in enumerate(pieces))

def fake_result():
    r=json.loads((BASE/'runs/M398-tail-reference-board-01/BOARD_RESULT.json').read_bytes())
    r.update(manifest_sha256=sha(PKG/'PACKAGE_MANIFEST.json'),gate_level=SCOPE,status='PASS_M402_TAIL_VIDEO_NUMERICAL',tail_candidate_executed=True,candidate_numerical_pass=True,candidate_full_model_executed=True)
    r.pop('reference_capture');r.pop('reference_capture_pass');r.pop('tail_capture_prerequisite_sha256')
    expected=json.loads((PKG/'VIDEO_EXPECTED.json').read_bytes())
    r['video_result']=copy.deepcopy(expected['baseline']);r['transactions']=copy.deepcopy(expected['transactions'])
    r['logical_calls']=766;r['host_calls']=767;r['fpga_transactions']=768
    r['candidate_semantic']=copy.deepcopy(expected['baseline']['semantic']);r['candidate_semantic']['proof']['build_id']=r['build_id']
    for name,payload in r['events']:
        if name=='complete':payload['proof']=copy.deepcopy(r['candidate_semantic']['proof'])
    r['source_precheck_before_hardware_import']=json.loads((BASE/'runs/M401-tail-text-board-02/BOARD_RESULT.json').read_bytes())['source_precheck_before_hardware_import']
    r['tail_scope']=dict(plan=dict(tokens=159,tail_start=128,tail_count=31,original_logical=778,logical=766),selected=[dict(layer=35,original_token_start=128,local_token_start=0,token_count=31,original_dma_slot=0,candidate_dma_slot=0)],invoked=True,closed=True,retained=False,binding_callback_removed=True,extra_dma_allocations=0,ps_prefetch=False,parser_workers=1,silu_workspace=False)
    from m402_count_scope import SOURCE_SHA
    r['count_source_precheck']=dict(original_source_sha256=SOURCE_SHA,original159_calls=778,original30_calls=162,code_equal=True)
    r['count_scope']=dict(proof=r['count_source_precheck'],accepted_calls=1,original_expected=778,candidate_expected=766,closed=True,binding_restored=True,board_evidence_changed=False)
    r['count_scope_weakref_dead']=True
    r.update(text_prerequisite_sha256='e4ffe98c1deed4863701a783a90f2b1272cbbd7eb71136f37e0a38238d52da85',text_closure_sha256='0e3e6e2241fec9fb520f2334a84006b11991f052d58165f28c367506c25b914b',layer_prerequisite_sha256='bca7bf2b4c6de4a4e861448162ce9a97da32e82fd68bf7af0dcf9c8eedde089c',layer_closure_sha256='64acc9f2174e95c241b26f91cb328f732105d766751c0092d0ce0c8a3d608043',original_reference_sha256='ca4a8d45e5e73190ee476958886cc97eafb42f6476d1c440fcbae9d99b2400ef')
    return r

def main():
    workflow=(HERE/'m401_workflow02.py').read_text(encoding='utf-8').replace("PKG=BASE/'candidates/M401-tail-text-02'","PKG=BASE/'candidates/M402-tail-video-01'").replace("OLD=BASE/'candidates/M401-tail-text-01'","OLD=BASE/'candidates/M401-tail-text-02'").replace('M401','M402').replace('m40102','m402').replace('m401_tail_text','m402_tail_video').replace('m401_collect02','m402_collect').replace('m401_tail_text','m402_tail_video').replace('tail_text','tail_video').replace('tail-text-transfer-02','tail-video-transfer-01').replace('精确M401-01','精确M401-02').replace('固定30文本','固定159视频')
    atomic(HERE/'m402_workflow.py',workflow.encode('utf-8'))
    control=(HERE/'m401_control02.ps1').read_text(encoding='utf-8').replace("$local='deployment/mage_vl4b/optimization_v1/candidates/M401-tail-text-02'","$local='deployment/mage_vl4b/optimization_v1/candidates/M402-tail-video-01'").replace('M401-tail-text-01/PACKAGE_MANIFEST.json','M401-tail-text-02/PACKAGE_MANIFEST.json').replace('M401-tail-text-board-02','M402-tail-video-board-01').replace('M401','M402').replace('m40102','m402').replace('m401_workflow02','m402_workflow').replace('m401_tail_text_candidate_02','m402_tail_video_candidate_01').replace('m401_tail_text','m402_tail_video').replace('m401_export_result','m402_export_result').replace('m401_assemble','m402_assemble').replace('tail_text','tail_video').replace('TAIL_TEXT','TAIL_VIDEO')
    # Restore exact prior local manifest name after replacing the new namespace.
    control=control.replace('candidates/M402-tail-text-02/PACKAGE_MANIFEST.json','candidates/M401-tail-text-02/PACKAGE_MANIFEST.json')
    atomic(HERE/'m402_control.ps1',control.encode('utf-8'))
    for n in ('m402_workflow.py','m402_collect.py','m402_prepare_video.py','m402_count_scope.py'):ast.parse((HERE/n).read_bytes(),feature_version=(3,10))
    entry=namespace(PKG/'m402_video_entry.py')
    entry['SOURCE']=ROOT/'release_staging/kv260-mage-vl-4b-prebuilt-install-20260926-v7/deployment/mage_vl4b/m242_m241_fixed_text_board_candidate/m241_video_language_runtime.py'
    proof=entry['precheck'](sha(PKG/'PACKAGE_MANIFEST.json'))
    from m402_collect import decode
    import m402_collect as collector
    r=fake_result();assert decode(envelope(r))[2]==r
    mutations=[lambda q:q.update(gate_return_code=True),lambda q:q.update(performance_pass=True),lambda q:q.update(scope_weakref_dead=False),lambda q:q.update(count_scope_weakref_dead=False),lambda q:q['count_scope'].update(binding_restored=False),lambda q:q['count_scope'].update(board_evidence_changed=True),lambda q:q.update(host_calls=781),lambda q:q.update(fpga_transactions=782),lambda q:q.update(ps_prefetch_enabled=True),lambda q:q.update(extra_pynq_allocations=1),lambda q:q.update(original_parser_workers=2),lambda q:q['tail_scope']['selected'][0].update(token_count=1),lambda q:q['transactions'].pop(),lambda q:q['transactions'][0].update(input_bytes=1),lambda q:q['video_result']['keys'].pop(),lambda q:q.update(text_closure_sha256='0'*64),lambda q:q['source_precheck_before_hardware_import'].update(deterministic_source_equal=False),lambda q:q.update(vision_forward_calls=2),lambda q:q['sampled_memory'].update(observer_stopped=False),lambda q:q.update(stable_overlay_reloaded=False)]
    for mutate in mutations:
        q=copy.deepcopy(r);mutate(q)
        try:decode(envelope(q))
        except (ValueError,KeyError,AssertionError):pass
        else:raise AssertionError('Explicit fake bad result accepted')
    early=dict(case='B1',build_id='0x4D333537',gate_level=SCOPE,manifest_sha256=sha(PKG/'PACKAGE_MANIFEST.json'),status='FAIL',gate_return_code=1,errors=['EXPLICIT_FAKE_PRE_RESOURCE_FAILURE'],source_precheck_before_hardware_import=proof,memory_capacity_proven=False,performance_pass=False,formal_promotion_allowed=False,fpga_transactions=0)
    assert decode(envelope(early))[2]==early
    temp_root=ROOT/'tmp/m402/offline';temp_root.mkdir(parents=True,exist_ok=True)
    with tempfile.TemporaryDirectory(dir=temp_root) as d:
        d=Path(d);log=d/'saved.log';atomic(log,envelope(r).encode('utf-8'))
        calls=[]
        def record_write(path,raw,**kw):calls.append(('atomic',str(path),kw));assert path==BASE/'runs/M402-tail-video-board-01/BOARD_RESULT.json';assert raw==encoded(r);assert kw=={'immutable':True}
        def record_sync(key,value,message):calls.append(('sync',key));assert key=='latest_m402_tail_video_board';assert value['result']=='deployment/mage_vl4b/optimization_v1/runs/M402-tail-video-board-01/BOARD_RESULT.json';assert not value['performance_pass'] and value['candidate_numerical_pass']
        with patch.object(collector,'atomic',record_write),patch.object(collector,'sync',record_sync),contextlib.redirect_stdout(io.StringIO()):collector.collect(log)
        assert [c[0] for c in calls]==['atomic','sync']
        # Actual saved-byte exporter, no root or board claims from these fakes.
        (d/'B1').mkdir();atomic(d/'B1/load-memory.json',encoded(early))
        exporter=namespace(PKG/'m402_export_result.py');exporter['Path']=lambda _:d;exporter['os']=SimpleRoot();exporter['time']=NoWait()
        output=io.StringIO()
        with contextlib.redirect_stdout(output):exporter['emit_saved']('B1')
        assert decode(output.getvalue())[2]==early
    ps=Path(r'C:\Users\30429\.cache\codex-runtimes\codex-primary-runtime\dependencies\native\powershell\pwsh.exe')
    selftest=subprocess.run([str(ps),'-NoProfile','-File',str(HERE/'m402_control.ps1'),'-Mode','SelfTest'],capture_output=True,text=True,encoding='utf-8');assert selftest.returncode==0,selftest.stdout+selftest.stderr
    names=json.loads(subprocess.check_output([str(ps),'-NoProfile','-File',str(HERE/'m402_control.ps1'),'-Mode','List'],text=True,encoding='utf-8'))
    oldrows={r['path']:r for r in json.loads((OLD/'PACKAGE_MANIFEST.json').read_bytes())['files']}
    rows=json.loads((PKG/'PACKAGE_MANIFEST.json').read_bytes())['files']
    assert names==['PACKAGE_MANIFEST.json']+[r['path'] for r in rows if oldrows.get(r['path'])!=r]
    with tempfile.TemporaryDirectory(dir=temp_root) as d:
        d=Path(d);prior=d/'old';new=d/'new';prior.mkdir();new.mkdir()
        for p in OLD.iterdir():atomic(prior/p.name,p.read_bytes())
        for n in names:atomic(new/n,(PKG/n).read_bytes())
        assembler=namespace(PKG/'m402_assemble.py');assert assembler['OLD'].as_posix()=='/home/ubuntu/m401_tail_text_candidate_02';assert assembler['OLD_SHA']==sha(OLD/'PACKAGE_MANIFEST.json')
        assembler['HERE']=new;assembler['OLD']=prior;assembler['main'](sha(PKG/'PACKAGE_MANIFEST.json'))
        assert all(sha(new/r['path'])==r['sha256'] for r in rows)
    # Keep actual model and lifecycle checks separate, capture return codes.
    checked={}
    for n in ('test_m402_count_scope.py','test_m402_video_wrapper.py'):
        run=subprocess.run([sys.executable,'-X','utf8','-B',str(HERE/n)],capture_output=True,text=True,encoding='utf-8');assert run.returncode==0,run.stdout+run.stderr
        checked[n]=dict(returncode=0,output=run.stdout+run.stderr,sha256=sha(HERE/n))
    source_names=('m402_prepare_video.py','m402_prepare_support.py','m402_collect.py','m402_count_scope.py','m402_workflow.py','m402_control.ps1','test_m402_count_scope.py','test_m402_video_wrapper.py','m398_collect.py')
    value=dict(status='PASS_OFFLINE_FIXED159_TAIL_PACKAGE_AND_RECOVERY_ONLY',manifest_sha256=sha(PKG/'PACKAGE_MANIFEST.json'),source_sha256={n:sha(HERE/n) for n in source_names},source_precheck=proof,actual_wrapper_tests=4,actual_stream_count_tests=7,collector_negative_tests=len(mutations),actual_collect_destination_and_sync_order=True,actual_early_failure_export=True,actual_assembly=True,actual_control_selftest=selftest.stdout.strip(),controller_delta=names,tests=checked,same_SHA_hardware_checks=47,production_policy_unchanged=True,board_run=False,numerical_pass=False,performance_pass=False,next_step='One COM3 authorization check, bounded manifest-first transfer and one fixed159 numerical gate only; existing logs/result require saved-only collection.')
    for kind in ('preparation','support'):
        out=BASE/f'runs/M402-tail-video-{kind}-01/RESULT.json';atomic(out,encoded(value|{'record_kind':kind}),immutable=True)
        sync('latest_m402_tail_video_'+kind,dict(status=value['status'],result=out.relative_to(ROOT).as_posix(),sha256=sha(out),manifest_sha256=value['manifest_sha256']),f'## M402 固定159视频独立包与实际路径检查（2026-10-04）\n\n{sha(out)}；manifest `{value["manifest_sha256"]}`。4实际冻结wrapper/7实际M276 stream计数与恢复/20回收拒绝、实际原子保存目标与三记录顺序、早期失败导出、精确M401-02 assembly及PS SelfTest通过。Linear/Attention/板端计数/内存明确替身；只离线支持，无视频或性能PASS。47同SHA硬件及视频预算复用，新增DMA0，生产政策保持。下一步同COM3授权后固定159视频一次，已有log/result只Collect。')
    print(json.dumps(dict(status=value['status'],manifest_sha256=value['manifest_sha256'],board_run=False,negative_tests=len(mutations))))

class SimpleRoot:
    @staticmethod
    def geteuid():return 0
class NoWait:
    @staticmethod
    def sleep(_):pass

if __name__=='__main__':
    import sys
    main()
