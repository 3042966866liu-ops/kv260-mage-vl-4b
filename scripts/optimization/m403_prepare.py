"""Independent immutable same-kernel original/tail performance package."""
import ast
import json
import shutil
import sys
from m351_workflow import ROOT,HERE,BASE,sha,atomic,encoded,sync
from m377_prepare import once

OLD=BASE/'candidates/M395-silu-performance-01'
VIDEO=BASE/'candidates/M402-tail-video-01'
PKG=BASE/'candidates/M403-tail-performance-01'
SCOPE='balanced-fixed159-video-full-final-layer-versus-last-T32-tail'


def renamed(text):
    return text.replace('M395','M403').replace('m395','m403').replace('silu-performance','tail-performance').replace('silu_performance','tail_performance').replace('balanced-fixed159-video-original-expression-versus-SiLU-workspace',SCOPE)


def main():
    if PKG.exists():raise RuntimeError('Immutable package exists')
    board=json.loads((ROOT/'deployment/mage_vl4b/BOARD_GATE_RESULT.json').read_bytes())
    raw=board['latest_m402_tail_video_board'];closed=board['latest_m402_tail_video_closure']
    assert raw['status']=='PASS_M402_TAIL_VIDEO_NUMERICAL' and closed['status']=='PASS_FIXED159_FULL_VIDEO_LAST_LAYER_TAIL_NUMERICAL_ONLY'
    for e in (raw,closed):
        assert sha(ROOT/e['result'])==e['sha256']
        assert all(e['sha256'] in (ROOT/n).read_text(encoding='utf-8') for n in ('CURRENT_STATE.md','docsMILESTONES.md'))
    for package in (OLD,VIDEO):
        for r in json.loads((package/'PACKAGE_MANIFEST.json').read_bytes())['files']:
            assert sha(package/r['path'])==r['sha256']
    actual=json.loads((ROOT/raw['result']).read_bytes())
    reference=BASE/'runs/M398-tail-reference-board-01/BOARD_RESULT.json'
    assert sha(reference)=='ca4a8d45e5e73190ee476958886cc97eafb42f6476d1c440fcbae9d99b2400ef'
    a=json.loads(reference.read_bytes())['video_result'];b=actual['video_result']
    for k in ('input','token','logits','keys','values'):assert a[k]==b[k]
    assert (a['logical_calls'],a['host_calls'],b['logical_calls'],b['host_calls'])==(778,781,766,767)
    gate=renamed((OLD/'m395_light_video_gate.py').read_text(encoding='utf-8'))
    gate=gate.replace('Both SiLU variants','Both tail variants').replace('B ordinary5.900390625MiB workspace, no extra CMA','B final-layer last31 tokens only, no extra CMA')
    gate=once(gate,"    EVIDENCE=Path('/home/ubuntu/m403_tail_performance_01')","    if not globals().get('SOURCE_PRECHECK_PROOF'):raise RuntimeError('Pre-resource source proof required')\n    EVIDENCE=Path('/home/ubuntu/m403_tail_performance_01')")
    gate=once(gate,'    runtime = engine = base = lock = policy = None',"    result['source_precheck_before_hardware_import']=dict(SOURCE_PRECHECK_PROOF)\n    runtime = engine = base = lock = policy = None")
    start=gate.index("        video_path=Path('/home/ubuntu/m394_");end=gate.index('        if os.geteuid()',start)
    gate=gate[:start]+f"        video_path=Path('/home/ubuntu/m402_tail_video_01/B1/load-memory.json')\n        video=json.loads(video_path.read_bytes())\n        if sha256(video_path)!='{raw['sha256']}' or video['status']!='PASS_M402_TAIL_VIDEO_NUMERICAL' or video['gate_return_code'] or not video['scope_weakref_dead'] or not video['count_scope_weakref_dead'] or not video['safe_buffers_released']:raise RuntimeError('Actual tail video prerequisite differs')\n        result['tail_video_prerequisite_sha256']=sha256(video_path)\n"+gate[end:]
    gate=once(gate,"        policy=StagePolicy(result,lambda:runtime,base)\n        mark('after-exact-runtime-imports')","        from m402_count_scope import validate as validate_count\n        if m276_video_runtime._server is not video_server:raise RuntimeError('Actual stream server identity differs')\n        result['count_source_precheck']=validate_count(video_server.expected_physical_calls)\n        policy=StagePolicy(result,lambda:runtime,base)\n        mark('after-exact-runtime-imports')")
    gate=gate.replace("result.get('retained_SiLU_scope',False)","result.get('retained_tail_scope',False) or result.get('retained_count_scope',False)")
    trials=renamed((OLD/'m395_trials.py').read_text(encoding='utf-8'))
    trials=once(trials,'from m393_silu_scope import SiluLayerScope,RetainedSiluOwnerError','from m401_prefill_tail_scope import LastLayerTailScope,RetainedTailOwnerError\nfrom m403_timed_count_scope import TimedVideoCountScope\nfrom m402_video_contract import check_call_contract as check_tail_contract,validate_stream as validate_tail_stream')
    trials=once(trials,"    expected=json.loads((here/'VIDEO_EXPECTED.json').read_text(encoding='utf-8'))['baseline']","    references=json.loads((here/'VIDEO_EXPECTED.json').read_bytes())\n    expected=references['baseline']")
    trials=once(trials,'    silu_scope=None;variant=None','    tail_scope=count_scope=None;variant=None')
    trials=once(trials,'        nonlocal silu_scope','        nonlocal tail_scope,count_scope')
    start=trials.index("        if variant=='B':");end=trials.index("        stage_ms['prefill']",start)
    trials=trials[:start]+'''        if variant=='B':
            result['retained_tail_scope']=result['retained_count_scope']=True
            count_scope=TimedVideoCountScope(video._server,resident,enabled=True)
            count_ref=weakref.ref(count_scope)
            tail_scope=LastLayerTailScope(engine.language,policy,resident,tokens=159,enabled=True)
            scope_ref=weakref.ref(tail_scope)
            candidate_prefill=tail_scope.bind(sys.modules['m241_video_language_runtime'])
            answer=candidate_prefill(engine.language,hidden)
            tail_scope.close()
            scope_report=tail_scope.report()
            del candidate_prefill
            tail_scope=None
            if scope_ref() is not None:raise RetainedTailOwnerError('Closed timed tail scope retained')
            result['retained_tail_scope']=False
            captured['tail_report']=dict(scope_report,scope_weakref_dead=True)
            captured['count_ref']=count_ref
        else:
            answer=original_prefill(hidden)
            captured['tail_report']=dict(enabled=False,original_full_final_layer=True,extra_dma_allocations=0)
            captured['count_report']=dict(enabled=False,original_expected=778,binding_unchanged=True)
''' +trials[end:]
    trials=once(trials,'    for index,variant in enumerate(ORDER):',"    for index,variant in enumerate(ORDER):\n        expected=references['candidate' if variant=='B' else 'baseline']")
    trials=once(trials,"        if result.get('retained_SiLU_scope') or silu_scope is not None:raise RetainedSiluOwnerError('SiLU lifecycle incomplete before DMA release')",'''        if variant=='B':
            if count_scope is None or not count_scope.closed:raise RetainedTailOwnerError('Timed count binding not safely closed')
            captured['count_report']=dict(count_scope.report(),closed_inside_original_total_timer=True)
            count_scope=None
            if captured['count_ref']() is not None:raise RetainedTailOwnerError('Closed count scope retained')
            captured.pop('count_ref')
            captured['count_report']['scope_weakref_dead']=True
            result['retained_count_scope']=False
        if result.get('retained_tail_scope') or result.get('retained_count_scope') or tail_scope is not None or count_scope is not None:
            raise RetainedTailOwnerError('Tail/count lifecycle incomplete before DMA release')''')
    trials=once(trials,'        semantic=validate_stream(events,engine.vision.decoder_evidence(),',"        semantic=(validate_tail_stream if variant=='B' else validate_stream)(events,engine.vision.decoder_evidence(),")
    trials=once(trials,"        check_call_contract(row,expected['logical_expected_macros'])","        (check_tail_contract if variant=='B' else check_call_contract)(row,expected['logical_expected_macros'])")
    trials=once(trials,"        sample['silu_scope']=captured['silu_report']","        sample['tail_scope']=captured['tail_report']\n        sample['count_scope']=captured['count_report']")
    trials=trials.replace("result['silu_workspace_enabled']='B only'","result['silu_workspace_enabled']=False\n    result['tail_candidate_enabled']='B only'").replace('A original expression / B SiLU workspace','A full final layer / B final T32 tail')
    trials=trials.replace('# Candidate source pinning/binding, workspace allocation and safe close','# Candidate source/count pinning, binding and safe close')
    assert 'silu_scope' not in trials and 'SiluLayerScope' not in trials
    PKG.mkdir(parents=True)
    skip={'m395_assemble.py','m395_trials.py','m395_light_video_gate.py','m395_export_result.py','run_m395_light_video.sh','SHA256SUMS','m393_silu_scope.py','m393_silu_workspace.py','VIDEO_EXPECTED.json'}
    for row in json.loads((OLD/'PACKAGE_MANIFEST.json').read_bytes())['files']:
        if row['path'] not in skip:shutil.copyfile(OLD/row['path'],PKG/row['path'])
    for n in ('m401_prefill_tail_scope.py','m401_prefill_source.py','frozen_prefill.py','m402_count_scope.py','m402_video_contract.py'):
        shutil.copyfile(VIDEO/n,PKG/n)
    shutil.copyfile(HERE/'m403_timed_count_scope.py',PKG/'m403_timed_count_scope.py')
    atomic(PKG/'VIDEO_EXPECTED.json',encoded(dict(baseline=a,candidate=b,baseline_raw_sha256=sha(reference),candidate_raw_sha256=raw['sha256'])))
    atomic(PKG/'m403_light_video_gate.py',gate.encode('utf-8'));atomic(PKG/'m403_trials.py',trials.encode('utf-8'))
    for old,new in (('m395_export_result.py','m403_export_result.py'),('run_m395_light_video.sh','run_m403_light_video.sh'),('m395_assemble.py','m403_assemble.py')):
        s=renamed((OLD/old).read_text(encoding='utf-8'))
        if 'assemble' in new:s=s.replace('/home/ubuntu/m388_ps_performance_candidate_01','/home/ubuntu/m395_silu_performance_candidate_01').replace('025ae1b1e24d2295745f3469fcc84363503a0d4d42ae736ad4ac85c036c69964',sha(OLD/'PACKAGE_MANIFEST.json'))
        if new.endswith('.sh'):s=s.replace('m403_light_video_gate.py','m403_video_entry.py')
        atomic(PKG/new,s.encode('utf-8'))
    entry=(VIDEO/'m402_video_entry.py').read_text(encoding='utf-8').replace('M402','M403').replace('m402_tail_video_gate','m403_light_video_gate').replace('--enable-tail-video','--enable-staged-video')
    atomic(PKG/'m403_video_entry.py',entry.encode('utf-8'))
    allowed=set(sys.stdlib_module_names)|set(json.loads((PKG/'SOURCE_CLOSURE.json').read_bytes())['modules'])|{'numpy','pynq','tokenizers'}
    trees={p.stem:ast.parse(p.read_text(encoding='utf-8'),feature_version=(3,10)) for p in PKG.glob('*.py')};missing=[]
    for mod,t in trees.items():
        for n in ast.walk(t):
            imports=[a.name.split('.')[0] for a in n.names] if isinstance(n,ast.Import) else [(n.module or '').split('.')[0]] if isinstance(n,ast.ImportFrom) else []
            missing.extend((mod,x) for x in imports if x and x not in trees and x not in allowed)
    assert not missing,missing
    rows=[dict(path=p.name,bytes=p.stat().st_size,sha256=sha(p)) for p in sorted(PKG.iterdir())]
    atomic(PKG/'SHA256SUMS',''.join(r['sha256']+'  '+r['path']+'\n' for r in rows).encode('ascii'))
    rows.append(dict(path='SHA256SUMS',bytes=(PKG/'SHA256SUMS').stat().st_size,sha256=sha(PKG/'SHA256SUMS')))
    atomic(PKG/'PACKAGE_MANIFEST.json',encoded(dict(schema='m403-last-tail-balanced-request-v1',files=rows,file_count=len(rows),total_bytes=sum(r['bytes'] for r in rows))))
    for src,dst in [('m395_control.ps1','m403_control.ps1'),('m395_workflow.py','m403_workflow.py')]:
        s=renamed((HERE/src).read_text(encoding='utf-8-sig')).replace('M388-ps-performance-01','M395-silu-performance-01')
        s=s.replace('一次同核原表达式/SiLU工作缓冲ABBABAAB轻量请求对照','一次同核完整末层/末T32裁剪ABBABAAB轻量请求对照').replace('精确M388复制','精确M395复制').replace('SiLU视频包传输','末层性能包传输')
        atomic(HERE/dst,s.encode('utf-8'))
    c=renamed((HERE/'m395_collect.py').read_text(encoding='utf-8'))
    c=c.replace('silu_video_prerequisite_sha256','tail_video_prerequisite_sha256').replace('bff53238edcbfc611e7c3ca275113294bd75c70106af882115b9f880e03d256c',raw['sha256'])
    c=once(c,"r['silu_workspace_enabled']!='B only'","r['silu_workspace_enabled'] is not False or r['tail_candidate_enabled']!='B only'")
    c=once(c,"        expected=expected or json.loads((PKG/'VIDEO_EXPECTED.json').read_text(encoding='utf-8'))['baseline']","        references=expected or json.loads((PKG/'VIDEO_EXPECTED.json').read_bytes())")
    c=once(c,"        for i,s in enumerate(r['samples']):","        for i,s in enumerate(r['samples']):\n            expected=references['candidate' if s['variant']=='B' else 'baseline']")
    start=c.index("            p=s['silu_scope']");end=c.index("            n=s['numeric_sha_after_timer']",start)
    c=c[:start]+'''            p=s['tail_scope'];count=s['count_scope']
            if s['variant']=='A':
                if p!=dict(enabled=False,original_full_final_layer=True,extra_dma_allocations=0) or count!=dict(enabled=False,original_expected=778,binding_unchanged=True):raise ValueError('Original full layer/count changed')
            else:
                actual=json.loads((w.BASE/'runs/M402-tail-video-board-01/BOARD_RESULT.json').read_bytes())
                if p!=dict(actual['tail_scope'],scope_weakref_dead=True):raise ValueError('Timed tail scope differs')
                if count!=dict(actual['count_scope'],closed_inside_original_total_timer=True,scope_weakref_dead=True):raise ValueError('Timed count closure differs')
''' +c[end:]
    c=c.replace('A原表达式/B单SiLU工作缓冲','A完整末层/B末T32裁剪').replace('Changed SiLU prerequisite','Changed tail prerequisite')
    c=once(c,"        if r['order']!='ABBABAAB'", "        proof=json.loads((w.BASE/'runs/M402-tail-video-board-01/BOARD_RESULT.json').read_bytes())\n        if r.get('source_precheck_before_hardware_import')!=proof['source_precheck_before_hardware_import'] or r.get('count_source_precheck')!=proof['count_source_precheck']:raise ValueError('Pre-resource frozen source proof differs')\n        if r['order']!='ABBABAAB'")
    atomic(HERE/'m403_collect.py',c.encode('utf-8'))
    value=dict(status='PASS_OFFLINE_TAIL_BALANCED_REQUEST_PREPARATION',manifest_sha256=sha(PKG/'PACKAGE_MANIFEST.json'),video_raw_sha256=raw['sha256'],video_closure_sha256=closed['sha256'],baseline_raw_sha256=sha(reference),package_files=len(rows),package_bytes=sum(r['bytes'] for r in rows),recursive_missing=missing,order='ABBABAAB',same_hardware=True,original_parser_workers=1,PS_prefetch=False,SiLU_workspace=False,extra_DMA=False,source_scope_same_SHA=True,source_binding_and_shutdown_inside_original_timers=True,count_close_inside_original_total_timer=True,expected_logical_A=778,expected_logical_B=766,expected_physical_total=6200,all_numerical_SHA_after_timer=True,production_policy_unchanged=True,board_run=False,performance_pass=False)
    out=BASE/'runs/M403-tail-performance-preparation-01/RESULT.json';atomic(out,encoded(value),immutable=True);h=sha(out)
    sync('latest_m403_tail_performance_preparation',dict(status=value['status'],manifest_sha256=value['manifest_sha256'],result=out.relative_to(ROOT).as_posix(),sha256=h),f'## M403 末层裁剪轻量性能准备（2026-10-04）\n\n原M402视频raw {raw["sha256"]}/闭合后冻结，SHA {h}。同并行Build0x4D333537/原单parser、A完整末层778逻辑/B末31裁剪766逻辑、ABBABAAB。绑定/源检查/关闭含原计时，计数绑定在原complete计时内恢复，数值SHA全部在计时后。封锁额外DMA，PS预读/SiLU工作缓冲关闭、生产政策保持。尚需实际编排/回收/控制检查，没有新性能或上板。')
    print(json.dumps(value|dict(sha256=h)))


if __name__=='__main__':main()
