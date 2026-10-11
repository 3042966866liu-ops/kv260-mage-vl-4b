"""Conditional fixed-video same-kernel original-expression/workspace trials."""
import ast,json,shutil,sys,symtable
from m351_workflow import ROOT,HERE,BASE,sha,atomic,encoded,sync
from m377_prepare import once
OLD=BASE/'candidates/M388-ps-performance-01'
VIDEO=BASE/'candidates/M394-silu-video-01'
PKG=BASE/'candidates/M395-silu-performance-01'

def main():
    if PKG.exists():raise RuntimeError('Immutable candidate exists')
    b=json.loads((ROOT/'deployment/mage_vl4b/BOARD_GATE_RESULT.json').read_text(encoding='utf-8'));prior=b['latest_m394_silu_video_closure'];raw=b['latest_m394_silu_video_board']
    assert prior['status']=='PASS_FIXED159_VIDEO_SILU_SCOPE_ONLY' and raw['status']=='PASS_M394_SILU_VIDEO_NUMERICAL'
    for e in (prior,raw):assert sha(ROOT/e['result'])==e['sha256'] and all(e['sha256'] in (ROOT/n).read_text(encoding='utf-8') for n in ('CURRENT_STATE.md','docsMILESTONES.md'))
    for pkg in (OLD,VIDEO):
        for r in json.loads((pkg/'PACKAGE_MANIFEST.json').read_text(encoding='utf-8'))['files']:assert sha(pkg/r['path'])==r['sha256']
    assert "$remote='/home/ubuntu/m388_ps_performance_candidate_01'" in (HERE/'m388_control.ps1').read_text(encoding='utf-8-sig')
    gate=(OLD/'m388_light_video_gate.py').read_text(encoding='utf-8').replace('M388','M395').replace('m388','m395').replace('ps_performance','silu_performance').replace('balanced-fixed159-video-original-staging-versus-PS-prefetch','balanced-fixed159-video-original-expression-versus-SiLU-workspace')
    a=gate.index("        video_path=Path('/home/ubuntu/m387_");z=gate.index('        if os.geteuid()',a)
    gate=gate[:a]+f"        video_path=Path('/home/ubuntu/m394_silu_video_01/B1/load-memory.json')\n        video=json.loads(video_path.read_text(encoding='utf-8'))\n        if sha256(video_path)!='{raw['sha256']}' or video['status']!='PASS_M394_SILU_VIDEO_NUMERICAL' or video['gate_return_code'] or not video['scope_weakref_dead'] or not video['safe_buffers_released']:raise RuntimeError('Actual SiLU video prerequisite differs')\n        result['silu_video_prerequisite_sha256']=sha256(video_path)\n"+gate[z:]
    gate=gate.replace("result.get('retained_PS_scope',False) or (runtime is not None and hasattr(runtime,'_m351_ps_owner'))","result.get('retained_SiLU_scope',False)").replace('Both staging variants','Both SiLU variants').replace('B ordinary PS slot, no extra CMA','B ordinary5.900390625MiB workspace, no extra CMA')
    trials=(OLD/'m388_trials.py').read_text(encoding='utf-8').replace('M388','M395')
    trials=once(trials,'from m387_video_ps_read import VideoPSReadSession\nfrom ps_read_ahead import RetainedPSResourcesError','import sys\nfrom m393_silu_scope import SiluLayerScope,RetainedSiluOwnerError')
    trials=trials.replace('ps_session=None;variant=None;plan=None','silu_scope=None;variant=None').replace('nonlocal ps_session','nonlocal silu_scope')
    a=trials.index("        if variant=='B':");z=trials.index("        stage_ms['prefill']",a)
    trials=trials[:a]+'''        if variant=='B':
            result['retained_SiLU_scope']=True
            silu_scope=SiluLayerScope(engine.language,policy,resident,enabled=True)
            scope_ref=weakref.ref(silu_scope)
            candidate_prefill=silu_scope.bind(sys.modules['m241_video_language_runtime'])
            answer=candidate_prefill(engine.language,hidden)
            silu_scope.close()
            scope_report=silu_scope.report()
            del candidate_prefill
            silu_scope=None
            if scope_ref() is not None:raise RetainedSiluOwnerError('Closed timed SiLU scope retained')
            result['retained_SiLU_scope']=False
            captured['silu_report']=dict(scope_report,scope_weakref_dead=True)
        else:
            answer=original_prefill(hidden)
            captured['silu_report']=dict(enabled=False,original_expression=True,extra_pynq_allocations=0)
''' +trials[z:]
    a=trials.index('        plan=[(');z=trials.index('        captured.clear();stage_ms.clear()',a)
    trials=trials[:a]+'''        # Candidate source pinning/binding, workspace allocation and safe close
        # remain inside original request/Prefill timers, including all overhead.
''' +trials[z:]
    trials=once(trials,"        if result.get('retained_PS_scope') or ps_session is not None or hasattr(runtime,'_m351_ps_owner'):raise RetainedPSResourcesError('PS lifecycle incomplete before DMA release')","        if result.get('retained_SiLU_scope') or silu_scope is not None:raise RetainedSiluOwnerError('SiLU lifecycle incomplete before DMA release')")
    trials=trials.replace("('m238-parse','m238-pack','m351-ps-read')","('m238-parse','m238-pack')").replace("sample['ps_session']=captured['ps_report']","sample['silu_scope']=captured['silu_report']").replace('timed_head,plan','timed_head').replace("result['ps_prefetch_enabled']='B only'","result['ps_prefetch_enabled']=False\n    result['silu_workspace_enabled']='B only'").replace('A original staging / B ordinary PS pre-read','A original expression / B SiLU workspace')
    assert not any(n in trials for n in ('ps_session','ps_report','VideoPSReadSession','RetainedPSResourcesError','plan='))
    PKG.mkdir(parents=True)
    skip={'m388_assemble.py','m388_trials.py','m388_light_video_gate.py','m388_export_result.py','run_m388_light_video.sh','SHA256SUMS','ps_read_ahead.py','m383_sealed_ps_read.py','m382_ps_slot.py','m387_video_ps_read.py'}
    for r in json.loads((OLD/'PACKAGE_MANIFEST.json').read_text(encoding='utf-8'))['files']:
        if r['path'] not in skip:shutil.copyfile(OLD/r['path'],PKG/r['path'])
    for n in ('m393_silu_scope.py','m393_silu_workspace.py'):shutil.copyfile(VIDEO/n,PKG/n)
    atomic(PKG/'m395_light_video_gate.py',gate.encode('utf-8'));atomic(PKG/'m395_trials.py',trials.encode('utf-8'))
    for src,dst in [('m388_export_result.py','m395_export_result.py'),('run_m388_light_video.sh','run_m395_light_video.sh')]:
        s=(OLD/src).read_text(encoding='utf-8').replace('M388','M395').replace('m388','m395').replace('ps_performance','silu_performance').replace('balanced-fixed159-video-original-staging-versus-PS-prefetch','balanced-fixed159-video-original-expression-versus-SiLU-workspace')
        atomic(PKG/dst,s.encode('utf-8'))
    s=(VIDEO/'m394_assemble.py').read_text(encoding='utf-8').replace('M394','M395').replace('/home/ubuntu/m387_ps_video_candidate_01','/home/ubuntu/m388_ps_performance_candidate_01').replace(sha(BASE/'candidates/M387-ps-video-01/PACKAGE_MANIFEST.json'),sha(OLD/'PACKAGE_MANIFEST.json'))
    atomic(PKG/'m395_assemble.py',s.encode('utf-8'))
    trees={p.stem:ast.parse(p.read_text(encoding='utf-8'),feature_version=(3,10)) for p in PKG.glob('*.py')};allowed=set(sys.stdlib_module_names)|set(json.loads((PKG/'SOURCE_CLOSURE.json').read_text(encoding='utf-8'))['modules'])|{'numpy','pynq','tokenizers'};missing=[]
    for mod,tree in trees.items():
        for n in ast.walk(tree):
            names=[x.name.split('.')[0] for x in n.names] if isinstance(n,ast.Import) else ([(n.module or '').split('.')[0]] if isinstance(n,ast.ImportFrom) else [])
            missing.extend((mod,n) for n in names if n and n not in trees and n not in allowed)
    assert not missing,missing
    table=next(x for x in symtable.symtable(trials,'trials','exec').get_children() if x.get_name()=='run_trials');assert next(x for x in table.get_children() if x.get_name()=='timed_prefill').lookup('silu_scope').is_nonlocal()
    for r in json.loads((PKG/'HARDWARE_CLOSURE.json').read_text(encoding='utf-8'))['prerequisites']:assert sha(ROOT/r['path'])==r['sha256']
    rows=[dict(path=p.name,bytes=p.stat().st_size,sha256=sha(p)) for p in sorted(PKG.iterdir())];atomic(PKG/'SHA256SUMS',''.join(r['sha256']+'  '+r['path']+'\n' for r in rows).encode('ascii'));rows.append(dict(path='SHA256SUMS',bytes=(PKG/'SHA256SUMS').stat().st_size,sha256=sha(PKG/'SHA256SUMS')))
    atomic(PKG/'PACKAGE_MANIFEST.json',encoded(dict(schema='m395-SiLU-workspace-balanced-request-v1',files=rows,file_count=len(rows),total_bytes=sum(r['bytes'] for r in rows))))
    value=dict(status='PASS_OFFLINE_SILU_BALANCED_REQUEST_PREPARATION',manifest_sha256=sha(PKG/'PACKAGE_MANIFEST.json'),video_raw_sha256=raw['sha256'],video_closure_sha256=prior['sha256'],
               package_files=len(rows),package_bytes=sum(r['bytes'] for r in rows),recursive_missing=missing,order='ABBABAAB',same_hardware=True,original_parser_workers=1,PS_prefetch=False,extra_DMA=False,
               scope_source_same_SHA=True,workspace_geometry=[159,9728],workspace_bytes=6187008,source_binding_allocation_and_shutdown_inside_original_timers=True,all_numerical_SHA_after_timer=True,production_policy_unchanged=True,board_run=False,performance_pass=False)
    out=BASE/'runs/M395-silu-performance-preparation-01/RESULT.json';atomic(out,encoded(value),immutable=True);h=sha(out)
    sync('latest_m395_silu_performance_preparation',dict(status=value['status'],manifest_sha256=value['manifest_sha256'],result=out.relative_to(ROOT).as_posix(),sha256=h),
         f'## M395 SiLU完整请求轻量对照准备（2026-10-04）\n\n新159视频raw {raw["sha256"]}/闭合后冻结；同Build0x4D333537/原单parser、A原表达式/B单5.900390625MiB工作缓冲，ABBABAAB。绑定/创建/关闭包含在原Prefill与请求计时，完整视觉/输入/logits/72KV哈希在计时后；原视觉懒缓存一次预热、自然文件缓存与逐请求实际读盘记录。PS预读/双parser关闭、零新增DMA、同SHA数学/scope/硬件、生产准入不改，SHA {h}。未新完整请求收益，尚需编排/回收支持。')
    print(json.dumps(value|{'sha256':h}))

if __name__=='__main__':main()
