"""Actual packaged callback and strict collector/control checks, CPU only."""
import ast
import base64
import copy
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import time
import numpy as np
from m351_workflow import ROOT,HERE,BASE,sha,atomic,encoded,sync

PKG=BASE/'candidates/M375-video-future-wait-01'
OUT=BASE/'runs/M375-video-wait-support-01'
PWSH=Path(r'C:\Users\30429\.cache\codex-runtimes\codex-primary-runtime\dependencies\native\powershell\pwsh.exe')

def controller():
    source=(HERE/'m374_control.ps1').read_text(encoding='utf-8')
    source=source.replace('M374','M375').replace('m374','m375')
    source=source.replace('M375-layer-future-wait-01','M375-video-future-wait-01').replace('M375-layer-wait-','M375-video-wait-')
    source=source.replace('m375_layer_future_wait_candidate_01','m375_video_wait_candidate_01')
    source=source.replace('latest_m375_layer_wait_','latest_m375_video_wait_')
    source=source.replace('M365-staged-layer-03','M369-light-video-01')
    source=source.replace('run_m375_staged_layer.sh','run_m375_video_wait.sh')
    source=source.replace('M375_ENABLE_STAGED_LAYER','M375_ENABLE_VIDEO_WAIT')
    source=source.replace('__M375_CHECK_SUDO_RC_','__M375_PRECHECK_SUDO_RC_')
    source=source.replace('-TimeoutSeconds 900 ','-TimeoutSeconds 4200 ')
    source=source.replace('-TimeoutSeconds 60 ','-TimeoutSeconds 180 ')
    source=source.replace('/pynq-venv/bin/python3','/pynq-venv/bin/python')
    source=source.replace('M375_CPU_COMPONENT_SYNCHRONIZED','M375_FIXED_VIDEO_WAIT_SYNCHRONIZED')
    anchor='$support=$board.latest_m375_video_wait_support'
    assert source.count(anchor)==1
    source=source.replace(anchor,anchor+"\nif ($prep.status -ne 'PASS_OFFLINE_FIXED_VIDEO_WAIT_PACKAGE_PREPARATION' -or $support.status -ne 'PASS_OFFLINE_FIXED_VIDEO_WAIT_WORKFLOW_READY') { throw 'Preparation/support status incomplete' }\n$supportEvidence=Get-Content -LiteralPath (Join-Path $workspace $support.result) -Raw -Encoding UTF8 | ConvertFrom-Json\nforeach ($entry in $supportEvidence.host_source_sha256.PSObject.Properties) { if ((Get-FileHash -LiteralPath (Join-Path $PSScriptRoot $entry.Name) -Algorithm SHA256).Hash.ToLowerInvariant() -ne $entry.Value) { throw 'Host controller/collector source changed' } }")
    # Collect reads the saved board bytes directly and never executes the gate.
    atomic(HERE/'m375_control.ps1',source.encode('utf-8'))
    result=subprocess.run([str(PWSH),'-NoProfile','-File',str(HERE/'m375_control.ps1'),'-Mode','SelfTest'],capture_output=True,text=True,encoding='utf-8')
    if result.returncode or 'M375_CONTROL_SELF_TEST_PASS' not in result.stdout:raise RuntimeError(result.stdout+result.stderr)
    return result.stdout.strip()

def checks():
    sys.path.insert(0,str(PKG))
    from test_m375_video_wait import Model,Probe,CONTRACT
    from m375_video_wait import VideoWaitDiagnostic
    from m375_wait_validation import validate
    from m371_profile_summary import pack,unpack
    from m375_collect import decode,prior_validator
    r=Probe(retry=True);model=Model(r);d=VideoWaitDiagnostic(model,r,CONTRACT,enabled=True)
    trials=(PKG/'m375_trials.py').read_text(encoding='utf-8')
    tree=ast.parse(trials)
    run=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='run_trials')
    callback=next(n for n in run.body if isinstance(n,ast.FunctionDef) and n.name=='timed_prefill')
    env=dict(result={},captured={},stage_ms={},original_prefill=d.prefill,time=time)
    exec(compile(ast.Module(body=[callback],type_ignores=[]),'<actual-packaged-timed-prefill>','exec'),env)
    hidden=np.ones((159,2560),np.float32)
    answer=env['timed_prefill'](hidden)
    assert answer is model.answer and env['captured']['input'] is hidden and env['captured']['output'] is answer
    assert env['result']['model_forward_calls']==1 and env['stage_ms']['prefill']>0
    assert r.pipeline_retry_launches==3 and r.stages==154
    assert d.restored
    report=d.report();summary=validate(report,CONTRACT)
    packed=pack(report);decoded,raw=unpack(packed)
    assert decoded==report
    # Explicit collector fixture: old real numerical record + new CPU fake PL wait trace.
    fixture=json.loads((BASE/'runs/M371-candidate-profile-board-01/BOARD_RESULT.json').read_text(encoding='utf-8'))
    for name in ('candidate_prefill_profile','packed_prefill_trace','original_full_profile_counters'):fixture.pop(name,None)
    fixture.update(status='PASS_M375_FIXED_VIDEO_WAIT',manifest_sha256=sha(PKG/'PACKAGE_MANIFEST.json'),
        gate_level='fixed159-video-narrow-future-wait',packed_wait_trace=packed,video_wait_summary=summary,
        wait_bindings_restored=True,ps_prefetch_enabled=False,
        wait_prerequisite_sha256='031cf6e2e506f5296998e6e8dfbeba0e87480f41fc07f023aaf3fc6fc79147a2')
    def export(value):
        raw=encoded(value);parts=[raw[i:i+900] for i in range(0,len(raw),900)];rc=value['gate_return_code']
        return 'M375_RESULT_SHA256='+hashlib.sha256(raw).hexdigest()+'\nM375_SAVED_GATE_RC='+str(rc)+'\n'+''.join(f'M375_RESULT_CHUNK={i}/{len(parts)}:'+base64.b64encode(p).decode('ascii')+'\n' for i,p in enumerate(parts))+f'M375_DONE case=B1 gate_rc={rc} export_rc=0\n'
    good=export(fixture)
    assert decode(good)[2]==fixture
    failures=[]
    mutations={
        'head numerical mismatch':lambda x:x['samples'][0]['numeric_sha_after_timer']['logits'].update(sha256='0'*64),
        'missing physical call':lambda x:x['samples'][0]['counts'].update(host_calls=780),
        'buffer release incomplete':lambda x:x['samples'][0]['released_buffers'].pop(),
        'wrong candidate build':lambda x:x.update(build_id='0x4D395832'),
        'new worker':lambda x:x.update(worker_started=True),
        'prefetch enabled':lambda x:x.update(ps_prefetch_enabled=True),
        'binding not restored':lambda x:x.update(wait_bindings_restored=False),
        'observation recovery failed':lambda x:x.update(wait_recovery_error='fake error'),
        'wrong prerequisite':lambda x:x.update(wait_prerequisite_sha256='0'*64),
        'summary fabricated':lambda x:x['video_wait_summary']['by_family']['gate_up'].update(actual_wait_s=999),
        'trace SHA altered':lambda x:x['packed_wait_trace'].update(raw_sha256='0'*64),
        'trace compressed length wrong':lambda x:x['packed_wait_trace'].update(raw_bytes=1),
        'production promoted':lambda x:x.update(formal_promotion_allowed=True),
    }
    for label,mutate in mutations.items():
        value=copy.deepcopy(fixture);mutate(value)
        try:decode(export(value))
        except (RuntimeError,ValueError):failures.append(label)
        else:raise AssertionError('Invalid PASS accepted: '+label)
    for label,value in (
        ('missing chunk',good.replace('M375_RESULT_CHUNK=0/','M375_OMITTED_CHUNK=0/')),
        ('duplicate ordinal',good.replace('M375_RESULT_CHUNK=1/','M375_RESULT_CHUNK=0/')),
        ('export rc failure',good.replace('export_rc=0','export_rc=1')),
        ('missing DONE',good[:good.rfind('M375_DONE')]),
        ('raw rc mismatch',good.replace('M375_SAVED_GATE_RC=0','M375_SAVED_GATE_RC=1')),
    ):
        try:decode(value)
        except (RuntimeError,ValueError):failures.append(label)
        else:raise AssertionError('Broken collection accepted: '+label)
    failed=copy.deepcopy(fixture);failed.update(status='FAIL',gate_return_code=1,errors=['explicit CPU orchestration failure'],numerical_pass=False)
    assert decode(export(failed))[2]==failed
    transport_negative=prior_validator()['self_test']()
    # Actual stream-loop finally body writes a packed partial observation before preserving failure.
    stream_try=next(n for n in ast.walk(run) if isinstance(n,ast.Try) and any(isinstance(x,ast.For) and ast.unparse(x.iter)=='engine.stream(request)' for x in n.body))
    partial=Probe(fail_parse=True);partial_model=Model(partial);partial_scope=VideoWaitDiagnostic(partial_model,partial,CONTRACT,enabled=True)
    class FailingEngine:
        def stream(self,request):
            partial_scope.prefill(hidden)
            yield ('unexpected',None)
    env=dict(engine=FailingEngine(),request=object(),events=[],diagnostic=partial_scope,result={},pack=pack)
    try:
        exec(compile(ast.Module(body=[copy.deepcopy(stream_try)],type_ignores=[]),'<actual-packaged-request-finally>','exec'),env)
    except ValueError as exc:
        assert str(exc)=='explicit fake parser failure'
    else:raise AssertionError('Original parser exception suppressed')
    assert env['result']['wait_bindings_restored'] and 'wait_recovery_error' not in env['result']
    partial_report,partial_raw=unpack(env['result']['packed_wait_trace'])
    assert partial_scope.restored and partial_report['records'][-1]['exception']=='ValueError'
    try:validate(partial_report,CONTRACT)
    except ValueError:pass
    else:raise AssertionError('Partial failed observation accepted as complete')
    assert len(failures)==18 and transport_negative==8
    return dict(collector_new_negative_checks=len(failures),negative_labels=failures,
                original_transport_negative_checks=transport_negative,
                partial_failure_trace_saved=True,original_parser_error_preserved=True,
                success_trace_bytes=len(raw),success_trace_sha256=hashlib.sha256(raw).hexdigest())

def main():
    if OUT.exists():raise RuntimeError('Immutable support exists')
    control=controller()
    evidence=checks()
    # A separate successful fixture above already exercised exact full scope + positive/negative collection.
    manifest=json.loads((PKG/'PACKAGE_MANIFEST.json').read_text(encoding='utf-8'))
    for row in manifest['files']:assert sha(PKG/row['path'])==row['sha256']
    host_names=('m375_control.ps1','m375_workflow.py','m375_collect.py','m369_collect.py','m371_profile_summary.py','m375_wait_validation.py')
    result=dict(status='PASS_OFFLINE_FIXED_VIDEO_WAIT_WORKFLOW_READY',build_id='0x4D333537',
        manifest_sha256=sha(PKG/'PACKAGE_MANIFEST.json'),host_source_sha256={n:sha(HERE/n) for n in host_names},
        actual_packaged_timed_prefill_154_families_770_each=True,actual_frozen_scheduler_three_sync_retries=True,
        cpu_fake_PL_parser_model=True,collector_fake_wait_with_original_numeric_fixture=True,
        checks=evidence,collector_new_negative_checks=18,original_transport_negative_checks=8,
        original_parser_error_preserved=True,controller_failure_always_collect_and_collect_failure_stop=control,
        extra_cma_allocations=0,new_workers=0,ps_prefetch_enabled=False,board_run=False,numerical_pass=False,performance_pass=False,
        next_step='Prepared only. Explicit Check/Upload then one Run when requested; no repeated layer/profile/old8 performance.')
    atomic(OUT/'RESULT.json',encoded(result),immutable=True);digest=sha(OUT/'RESULT.json')
    sync('latest_m375_video_wait_support',dict(status=result['status'],sha256=digest,result=(OUT/'RESULT.json').relative_to(ROOT).as_posix(),manifest_sha256=result['manifest_sha256'],board_run=False),
        f'## M375 窄视频等待收集/控制离线准备完成（2026-10-03）\n\nBuild0x4D333537；真实冻结调度/真实Future及新包实际timed_prefill回调执行154family、770pack/770parse、3同步重试，明确PL/解析/模型替身。新collector完整原数值记录+fake等待阳性、18新负例与8原传输负例通过；原异常不吞、控制故意失败仍收集且收集失败停止。支持SHA {digest}，manifest {result["manifest_sha256"]}。按用户本轮只准备：0COM3/上传/Overlay/forward，实际视频等待仍未知。下一步若执行，只一次原视频窄等待观察。')
    print(json.dumps(dict(status=result['status'],sha256=digest,manifest_sha256=result['manifest_sha256'],board_run=False)))

if __name__=='__main__':main()
