"""Exact fixed159 video numerics with two gate_up parser workers only."""
import ast,json,shutil,sys,symtable
from m351_workflow import ROOT,HERE,BASE,sha,atomic,encoded,sync
from m377_prepare import once
OLD=BASE/'candidates/M368-staged-video-03'
PKG=BASE/'candidates/M380-gate-up-video-01'
def main():
    if PKG.exists():raise RuntimeError('Immutable package exists')
    board=json.loads((ROOT/'deployment/mage_vl4b/BOARD_GATE_RESULT.json').read_text(encoding='utf-8'));prior=board['latest_m379_gate_up_text_board']
    assert prior['status']=='PASS_M379_FIXED_TEXT_DIAGNOSTIC' and sha(ROOT/prior['result'])==prior['sha256']
    assert all(prior['sha256'] in (ROOT/n).read_text(encoding='utf-8-sig') for n in ('CURRENT_STATE.md','docsMILESTONES.md'))
    manifest=json.loads((OLD/'PACKAGE_MANIFEST.json').read_text(encoding='utf-8'))
    for r in manifest['files']:assert sha(OLD/r['path'])==r['sha256']
    oldraw=json.loads((BASE/'runs/M368-staged-video-board-02/BOARD_RESULT.json').read_text(encoding='utf-8'));assert oldraw['manifest_sha256']==sha(OLD/'PACKAGE_MANIFEST.json') and oldraw['status']=='PASS_M368_FIXED_VIDEO_DIAGNOSTIC'
    old_result_sha=sha(BASE/'runs/M368-staged-video-board-02/BOARD_RESULT.json')
    PKG.mkdir(parents=True)
    skip={'m368_assemble.py','m368_staged_video_gate.py','m368_export_result.py','run_m368_staged_video.sh','SHA256SUMS'}
    for r in manifest['files']:
        if r['path'] not in skip:shutil.copyfile(OLD/r['path'],PKG/r['path'])
    shutil.copyfile(BASE/'candidates/M376-gate-up-worker-component-01/m376_gate_up_workers.py',PKG/'m376_gate_up_workers.py')
    assembly=(BASE/'candidates/M379-gate-up-text-01/m379_assemble.py').read_text(encoding='utf-8').replace('M379','M380').replace('/home/ubuntu/m366_staged_text_candidate_03','/home/ubuntu/m368_staged_video_candidate_03').replace(sha(BASE/'candidates/M366-staged-text-03/PACKAGE_MANIFEST.json'),sha(OLD/'PACKAGE_MANIFEST.json'))
    atomic(PKG/'m380_assemble.py',assembly.encode('utf-8'))
    s=(OLD/'m368_staged_video_gate.py').read_text(encoding='utf-8')
    a=s.index("        identity_path=Path('/home/ubuntu/m368_identity_preflight_01/RESULT.json')");b=s.index("        prior=json.loads((HERE/'STAGE_PREREQUISITE.json')",a)
    # Loading path/source closure remains byte-identical to previously actual verified M368.
    # Bind that hardware numerical result, and require new text numeric evidence as well.
    s=s[:a]+"        prior_video_path=Path('/home/ubuntu/m368_staged_video_02/B1/load-memory.json')\n        prior_video=json.loads(prior_video_path.read_text(encoding='utf-8'))\n        if sha256(prior_video_path)!='"+old_result_sha+"' or prior_video['status']!='PASS_M368_FIXED_VIDEO_DIAGNOSTIC' or prior_video['manifest_sha256']!='"+sha(OLD/'PACKAGE_MANIFEST.json')+"':raise RuntimeError('Same-source actual video loader prerequisite differs')\n        result['same_loading_path_video_sha256']=sha256(prior_video_path)\n"+s[b:]
    s=s.replace('M368','M380').replace('/home/ubuntu/m368_staged_video_02','/home/ubuntu/m380_gate_up_video_01').replace('from m368_export_result import emit_saved','from m380_export_result import emit_saved')
    # Restore original raw-path/status provenance after experiment marker rename.
    s=s.replace("prior_video_path=Path('/home/ubuntu/m380_gate_up_video_01/B1/load-memory.json')","prior_video_path=Path('/home/ubuntu/m368_staged_video_02/B1/load-memory.json')").replace("prior_video['status']!='PASS_M380_FIXED_VIDEO_DIAGNOSTIC'","prior_video['status']!='PASS_M368_FIXED_VIDEO_DIAGNOSTIC'")
    s=once(s,"        result['prior_board_sha256'] = PRIOR_SHA","        result['prior_board_sha256'] = PRIOR_SHA\n        text_path=Path('/home/ubuntu/m379_gate_up_text_01/B1/load-memory.json')\n        text=json.loads(text_path.read_text(encoding='utf-8'))\n        if sha256(text_path)!='"+prior['sha256']+"' or text['status']!='PASS_M379_FIXED_TEXT_DIAGNOSTIC' or text['gate_return_code']!=0 or not text['safe_buffers_released']:raise RuntimeError('New two-parser text prerequisite differs')\n        result['two_parser_text_sha256']=sha256(text_path)")
    s=once(s,'            output=original_prefill(hidden)',"            from m376_gate_up_workers import GateUpWorkers\n            parser_scope=GateUpWorkers(runtime,workers=2,enabled=True)\n            with parser_scope:\n                output=original_prefill(hidden)\n            result['parser_scope']=parser_scope.report()\n            result['ps_prefetch_enabled']=False")
    atomic(PKG/'m380_staged_video_gate.py',s.encode('utf-8'))
    export=(BASE/'candidates/M379-gate-up-text-01/m379_export_result.py').read_text(encoding='utf-8').replace('M379','M380').replace('/home/ubuntu/m379_gate_up_text_01','/home/ubuntu/m380_gate_up_video_01').replace('independent-fixed-text-capacity-diagnostic','independent-fixed159-video-capacity-diagnostic')
    atomic(PKG/'m380_export_result.py',export.encode('utf-8'))
    runner=(BASE/'candidates/M379-gate-up-text-01/run_m379_staged_text.sh').read_text(encoding='utf-8').replace('M379','M380').replace('m379_export_result','m380_export_result').replace('m379_staged_text_gate','m380_staged_video_gate').replace('/home/ubuntu/m379_gate_up_text_01','/home/ubuntu/m380_gate_up_video_01').replace('ENABLE_STAGED_LAYER','ENABLE_STAGED_VIDEO').replace('--enable-staged-layer','--enable-staged-video')
    atomic(PKG/'run_m380_staged_video.sh',runner.encode('utf-8'))
    closure=json.loads((PKG/'SOURCE_CLOSURE.json').read_text(encoding='utf-8'));trees={p.stem:ast.parse(p.read_text(encoding='utf-8'),feature_version=(3,10)) for p in PKG.glob('*.py')};allowed=set(sys.stdlib_module_names)|set(closure['modules'])|{'numpy','pynq','tokenizers'};missing=[]
    for mod,tree in trees.items():
        for node in ast.walk(tree):
            names=[r.name.split('.')[0] for r in node.names] if isinstance(node,ast.Import) else ([(node.module or '').split('.')[0]] if isinstance(node,ast.ImportFrom) else [])
            missing.extend((mod,n) for n in names if n and n not in trees and n not in allowed)
    assert not missing,missing
    table=next(t for t in symtable.symtable(s,'gate','exec').get_children() if t.get_name()=='main');assert next(t for t in table.get_children() if t.get_name()=='tracked_allocate').lookup('SHAPES').is_global()
    for n in ('m368_stage_policy.py','m368_head_observer.py','VIDEO_EXPECTED.json','VISUAL_EXPECTED.json','SOURCE_CLOSURE.json','HARDWARE_CLOSURE.json','owned_buffer_release.py','frozen_video_identity.py'):assert sha(PKG/n)==sha(OLD/n)
    rows=[dict(path=p.name,bytes=p.stat().st_size,sha256=sha(p)) for p in sorted(PKG.iterdir())];atomic(PKG/'SHA256SUMS',''.join(r['sha256']+'  '+r['path']+'\n' for r in rows).encode('ascii'));rows.append(dict(path='SHA256SUMS',bytes=(PKG/'SHA256SUMS').stat().st_size,sha256=sha(PKG/'SHA256SUMS')))
    atomic(PKG/'PACKAGE_MANIFEST.json',encoded(dict(schema='m380-two-parser-fixed-video-v1',files=rows,file_count=len(rows),total_bytes=sum(r['bytes'] for r in rows))))
    r=dict(status='PASS_OFFLINE_TWO_PARSER_FIXED_VIDEO_PREPARATION',manifest_sha256=sha(PKG/'PACKAGE_MANIFEST.json'),two_parser_text_sha256=prior['sha256'],original_video_raw_sha256=old_result_sha,original_video_manifest_sha256=sha(OLD/'PACKAGE_MANIFEST.json'),recursive_import_missing=missing,python310_syntax=True,original159token_math_visual_head_reference_policy_same_sha=True,extra_cma_bytes=0,additional_parser_array_bound_bytes=1638400,ps_growth_policy_bytes=1024<<20,ps_available_margin_bytes=64<<20,native_peak_certified=False,board_run=False,numerical_pass=False,performance_pass=False)
    path=BASE/'runs/M380-gate-up-video-preparation-01/RESULT.json';atomic(path,encoded(r),immutable=True);digest=sha(path);sync('latest_m380_gate_up_video_preparation',dict(status=r['status'],result=path.relative_to(ROOT).as_posix(),sha256=digest,manifest_sha256=r['manifest_sha256']),f'## M380 gate_up 双解析worker固定视频准备（2026-10-03）\n\n新文本SHA {prior["sha256"]}同步后准备；复用原M368实际加载/数值SHA {old_result_sha}与全部同SHA输入/视觉/family/72KV/logits/判断参考。原159Token/778逻辑、实际重试物理计数，0新增DMA。额外解析数组保守1.5625MiB，native峰值不预称；原视频1GiB增长监控及64MiB普通可用余量、逐提交CMA计数停止保持。源码missing=0/3.10/作用域通过。准备 SHA {digest}；尚未上板，下一步支持检查。')
    print('M380_PREPARED',digest,len(rows))
if __name__=='__main__':main()
