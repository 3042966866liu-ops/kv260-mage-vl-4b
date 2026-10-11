"""Freeze a bounded original-video layer0 capture; no new math candidate."""
import ast
import json
import shutil
import sys
from m351_workflow import ROOT,HERE,BASE,sha,atomic,encoded,sync
from m377_prepare import once

OLD = BASE/'candidates/M387-ps-video-01'
PKG = BASE/'candidates/M390-gate-up-capture-01'


def main():
    if PKG.exists():raise RuntimeError('Immutable package exists')
    board=json.loads((ROOT/'deployment/mage_vl4b/BOARD_GATE_RESULT.json').read_text(encoding='utf-8'))
    prior=board['latest_m389_silu_workspace_preparation']
    video=board['latest_m387_ps_video_closure']
    for r in (prior,video):
        assert sha(ROOT/r['result'])==r['sha256']
        assert all(r['sha256'] in (ROOT/n).read_text(encoding='utf-8-sig') for n in ('CURRENT_STATE.md','docsMILESTONES.md'))
    assert video['status']=='PASS_FIXED159_VIDEO_PS_PLAN_ONLY'
    manifest=json.loads((OLD/'PACKAGE_MANIFEST.json').read_text(encoding='utf-8'))
    assert sha(OLD/'PACKAGE_MANIFEST.json')=='2613ed813ca8d873076b0a6443309242f9c0594e655e57dcfe4d1859839f4fbb'
    assert all(sha(OLD/r['path'])==r['sha256'] for r in manifest['files'])
    gate=(OLD/'m387_ps_video_gate.py').read_text(encoding='utf-8')
    gate=gate.replace('M387','M390').replace('m387','m390')
    gate=gate.replace('from m390_video_ps_read import VideoPSReadSession','from m390_capture_boundary import GateUpCapture,CaptureBoundary')
    gate=gate.replace('from ps_read_ahead import RetainedPSResourcesError\n','').replace('from m382_ps_slot import RetainedSlotError\n','')
    gate=gate.replace('/home/ubuntu/m390_ps_video_01','/home/ubuntu/m390_gate_up_capture_01')
    gate=gate.replace('enable-ps-video','enable-capture').replace('enable_ps_video','enable_capture')
    gate=gate.replace('sealed-DMA-PS-fixed159-video-numerical','sealed-DMA-fixed159-layer0-gate-up-capture')
    gate=gate.replace('PASS_M390_PS_VIDEO_NUMERICAL','PASS_M390_ACTUAL_GATE_UP_CAPTURE')
    gate=gate.replace('Original complete runtime objects retained; independent fixed159-token diagnostic including36 layers/head, one ordinary PS slot, no extra CMA; original visual plus language and head; production policy unchanged','Original complete runtime retained, no PS prefetch; original visual and layer0 q/kv/attention_out/gate_up only; no mlp_down, later layer or head')
    gate=gate.replace('        result[\'PS_text_prerequisite_sha256\']=sha256(text_path)', '        result[\'historical_text_prerequisite_sha256\']=sha256(text_path)')
    # Insert the new synchronized preparation identity before any board action.
    gate=once(gate,"        if os.geteuid() != 0:",
        "        video_path=Path('/home/ubuntu/m387_ps_video_01/B1/load-memory.json')\n"
        "        if sha256(video_path)!='0d36bf91329a1f2e433bfad64905b61836aa75e36c85a54432c028551609d348':raise RuntimeError('Same source actual video prerequisite differs')\n"
        "        if os.geteuid() != 0:")
    a=gate.index('        model=engine.language;families=[];captured={};original_family=model._family')
    z=gate.index('        original_preprocess=m276_video_runtime.preprocess',a)
    replacement='''        model=engine.language;captured={}
        capture=GateUpCapture(model._family,expected['baseline']['families'],policy,EVIDENCE)
        patch(model,'_family',capture)
        original_prefill=model.prefill
        def observed_prefill(hidden):
            if captured:raise RuntimeError('Unexpected second prefill')
            captured['input']=tensor(hidden)
            if captured['input']!=expected['baseline']['input'] or hidden.shape!=(159,2560):raise RuntimeError('Original159 video input differs')
            policy.capture('before-language-capture',True)
            result['model_forward_calls']=1
            result['ps_prefetch_enabled']=False
            result['original_parser_workers']=1
            result['extra_pynq_allocations']=len(allocations)-7
            original_prefill(hidden)
            raise RuntimeError('Original prefill returned instead of bounded capture')
        patch(model,'prefill',observed_prefill)
'''
    gate=gate[:a]+replacement+gate[z:]
    a=gate.index('        events=[]\n        for event,payload in engine.stream(request):')
    z=gate.index("        result['boot_unchanged']",a)
    replacement='''        events=[];boundary_reached=False
        try:
            for event,payload in engine.stream(request):
                events.append((event,payload))
                if event=='stage':policy.capture('stream-stage:'+payload['name'],True)
                print('M390_EVENT '+event,flush=True)
        except CaptureBoundary:
            boundary_reached=True
        policy.capture('after-bounded-video-capture',True);policy.stop_sampling()
        evidence=runtime.evidence()
        result['boundary_reached']=boundary_reached
        result['captured_families']=capture.families
        result['actual_gate_up_fixtures']=capture.fixtures
        result['attempted_after_boundary']=capture.attempted_after_boundary
        result['input']=captured.get('input')
        result['events']=events
        result['decoder']=engine.vision.decoder_evidence()
        result['partial_call_contract']={k:evidence[k] for k in ('logical_calls','host_calls','scale_retry_count','pipeline_retry_launches','fused_nonfinite_detections','scale_attempts','stage_bytes')}
        attempts=evidence['scale_attempts']
        expected_attempts=expected['baseline']['scale_attempts'][:20]
        if not boundary_reached or not capture.done or len(capture.families)!=4 or capture.attempted_after_boundary:raise RuntimeError('Bounded capture incomplete')
        if attempts!=expected_attempts or evidence['logical_calls']!=20 or evidence['host_calls']!=20 or len(result['transactions'])!=20:raise RuntimeError('Original layer0 prefix physical/logical/retry accounting differs')
        if evidence['scale_retry_count'] or evidence['pipeline_retry_launches'] or evidence['fused_nonfinite_detections']:raise RuntimeError('Unexpected layer0 retry')
        if any(r['layer']!=0 or r['family'] not in ('q','kv','attention_out','gate_up') for r in result['transactions']):raise RuntimeError('Transaction escaped capture prefix')
        if [p['name'] for n,p in events if n=='stage']!=['preprocess','vision','prefill'] or any(n!='stage' for n,p in events):raise RuntimeError('Unexpected stream output after boundary')
        if result['preprocessed']!=visual_reference['preprocessed'] or result['visual_features']!=visual_reference['visual_features'] or result['prompt_token_ids']!=visual_reference['prompt_token_ids']:raise RuntimeError('Actual visual/input identity differs')
        if not resident() or any(t.name.startswith(('m238-parse','m238-pack')) for t in threading.enumerate()):raise RuntimeError('Capture completion/worker lifecycle unproven')
        result['capture_pass']=True
        result['numerical_pass']=False
        result['fixed_video_diagnostic_pass']=False
        result['status']='PASS_M390_ACTUAL_GATE_UP_CAPTURE'
        result['memory_capacity_proven']=False
'''
    gate=gate[:a]+replacement+gate[z:]
    a=gate.index('    except (RetainedPSResourcesError,RetainedSlotError) as exc:')
    z=gate.index('    except CapacityRejected as exc:',a)
    gate=gate[:a]+gate[z:]
    gate=gate.replace('unsafe=unsafe or ps_session is not None', 'unsafe=unsafe or ps_session is not None')
    gate=gate.replace('Independent video adjudication; balanced full-request performance only after exact output and lifecycle PASS synchronized', 'Capture identity/lifecycle adjudication only; CPU SiLU component after raw/closure triad, no whole model or performance rerun')
    assert 'VideoPSReadSession' not in gate and 'RetainedPSResourcesError' not in gate
    # Explicitly reject a head submission even if dispatch control escapes.
    gate=once(gate,"        patch(runtime,'_execute',observed_head)",
                   "        patch(runtime,'_execute',forbid('head.not-admitted',blocked))")
    PKG.mkdir(parents=True)
    skip={'m387_ps_video_gate.py','m387_video_ps_read.py','m387_export_result.py',
          'm387_assemble.py','run_m387_ps_video.sh','ps_read_ahead.py','m383_sealed_ps_read.py',
          'm382_ps_slot.py','SHA256SUMS'}
    for row in manifest['files']:
        if row['path'] not in skip:shutil.copyfile(OLD/row['path'],PKG/row['path'])
    atomic(PKG/'m390_capture_gate.py',gate.encode('utf-8'))
    shutil.copyfile(HERE/'m390_capture_boundary.py',PKG/'m390_capture_boundary.py')
    exporter=(OLD/'m387_export_result.py').read_text(encoding='utf-8').replace('M387','M390').replace('m387_ps_video_01','m390_gate_up_capture_01').replace('sealed-DMA-PS-fixed159-video-numerical','sealed-DMA-fixed159-layer0-gate-up-capture')
    atomic(PKG/'m390_export_result.py',exporter.encode('utf-8'))
    runner=(OLD/'run_m387_ps_video.sh').read_text(encoding='utf-8').replace('M387','M390').replace('m387_ps_video_01','m390_gate_up_capture_01').replace('m387_ps_video_gate.py','m390_capture_gate.py').replace('m387_export_result.py','m390_export_result.py').replace('ENABLE_PS_VIDEO','ENABLE_CAPTURE').replace('--enable-ps-video','--enable-capture')
    atomic(PKG/'run_m390_capture.sh',runner.encode('utf-8'))
    assembly=(OLD/'m387_assemble.py').read_text(encoding='utf-8')
    a=assembly.index("OLD=Path(");z=assembly.index('\ndef sha',a)
    assembly=assembly[:a]+"OLD=Path('/home/ubuntu/m387_ps_video_candidate_01')\nOLD_SHA='2613ed813ca8d873076b0a6443309242f9c0594e655e57dcfe4d1859839f4fbb'\n"+assembly[z:]
    a=assembly.index('    secondary=');z=assembly.index('    names=set()',a)
    assembly=assembly[:a]+assembly[z:]
    assembly=assembly.replace('            elif second.get(name)==row:source=secondary/name\n','').replace('M387','M390')
    atomic(PKG/'m390_assemble.py',assembly.encode('utf-8'))
    trees={p.stem:ast.parse(p.read_text(encoding='utf-8'),feature_version=(3,10)) for p in PKG.glob('*.py')}
    allowed=set(sys.stdlib_module_names)|set(json.loads((PKG/'SOURCE_CLOSURE.json').read_text(encoding='utf-8'))['modules'])|{'numpy','pynq','tokenizers'}
    missing=[]
    for module,tree in trees.items():
        for n in ast.walk(tree):
            imports=[a.name.split('.')[0] for a in n.names] if isinstance(n,ast.Import) else ([(n.module or '').split('.')[0]] if isinstance(n,ast.ImportFrom) else [])
            missing.extend((module,i) for i in imports if i and i not in trees and i not in allowed)
    assert not missing,missing
    rows=[dict(path=p.name,bytes=p.stat().st_size,sha256=sha(p)) for p in sorted(PKG.iterdir())]
    atomic(PKG/'SHA256SUMS',''.join(r['sha256']+'  '+r['path']+'\n' for r in rows).encode('ascii'))
    rows.append(dict(path='SHA256SUMS',bytes=(PKG/'SHA256SUMS').stat().st_size,sha256=sha(PKG/'SHA256SUMS')))
    atomic(PKG/'PACKAGE_MANIFEST.json',encoded(dict(schema='M390-original-video-layer0-capture-v1',files=rows,file_count=len(rows),total_bytes=sum(r['bytes'] for r in rows))))
    result=dict(status='PASS_OFFLINE_BOUNDED_CAPTURE_PREPARATION',prior=prior,video_prerequisite=video,
                manifest_sha256=sha(PKG/'PACKAGE_MANIFEST.json'),files=len(rows),bytes=sum(r['bytes'] for r in rows),
                recursive_missing=missing,python310_syntax=True,build_id='0x4D333537',ps_prefetch=False,
                parser_workers=1,additional_dma_allowed=False,expected_logical_calls=20,
                expected_physical_with_minimal=21,original_gate_up_shape=[159,9728],
                algorithm_component_executed=False,board_run=False,performance_pass=False)
    out=BASE/'runs/M390-capture-preparation-01/RESULT.json';atomic(out,encoded(result),immutable=True);d=sha(out)
    sync('latest_m390_capture_preparation',dict(status=result['status'],result=out.relative_to(ROOT).as_posix(),sha256=d,manifest_sha256=result['manifest_sha256']),
         f'## M390 原159视频layer0 gate/up捕获准备（2026-10-04）\n\nSHA {d}；原视觉/159输入/四family全SHA，原20逻辑/20物理+同Overlay最小事务，gate_up完整同步返回后两个真实FP32数组原子保存并主动边界结束；不运行mlp_down/后层/head/新SiLU。原七DMA封锁、1GiB普通预算和64MiB可用余量、原生产准入保持，PS预读/双parser关闭。missing0/3.10仅离线；尚需冻结实际调用顺序/故障/回收支持，未上传上板。COM3初次在login，未发命令，等待人工恢复且不重复探测。')
    print(json.dumps(dict(status=result['status'],sha256=d,manifest_sha256=result['manifest_sha256'],files=len(rows))))


if __name__=='__main__':main()
