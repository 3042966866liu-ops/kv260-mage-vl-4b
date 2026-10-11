"""Freeze unchanged fixed159 video with only the proven SiLU Prefill scope."""
import ast
import json
import shutil
import sys
import symtable
from m351_workflow import ROOT,HERE,BASE,sha,atomic,encoded,sync
OLD=BASE/'candidates/M387-ps-video-01';TEXT=BASE/'candidates/M393-silu-text-01';PKG=BASE/'candidates/M394-silu-video-01'

def main():
    if PKG.exists():raise RuntimeError('Immutable preparation exists')
    b=json.loads((ROOT/'deployment/mage_vl4b/BOARD_GATE_RESULT.json').read_text(encoding='utf-8'));prior=b['latest_m393_silu_text_closure'];raw=b['latest_m393_silu_text_board']['sha256']
    assert prior['status']=='PASS_FIXED_TEXT_SILU_SCOPE_ONLY'
    for e in (prior,b['latest_m393_silu_text_board']):assert sha(ROOT/e['result'])==e['sha256'] and all(e['sha256'] in (ROOT/n).read_text(encoding='utf-8') for n in ('CURRENT_STATE.md','docsMILESTONES.md'))
    m=json.loads((OLD/'PACKAGE_MANIFEST.json').read_text(encoding='utf-8'));assert all(sha(OLD/r['path'])==r['sha256'] for r in m['files'])
    old_remote='/home/ubuntu/m387_ps_video_candidate_01'
    assert "$remote='"+old_remote+"'" in (HERE/'m387_control_recovered_02.ps1').read_text(encoding='utf-8-sig')
    s=(OLD/'m387_ps_video_gate.py').read_text(encoding='utf-8').replace('M387','M394').replace('m387','m394')
    s=s.replace('from m394_video_ps_read import VideoPSReadSession','from m393_silu_scope import SiluLayerScope,RetainedSiluOwnerError').replace('from ps_read_ahead import RetainedPSResourcesError\n','').replace('from m382_ps_slot import RetainedSlotError\n','')
    s=s.replace('ps_session','silu_scope').replace('/home/ubuntu/m394_ps_video_01','/home/ubuntu/m394_silu_video_01').replace('enable-ps-video','enable-silu-video').replace('enable_ps_video','enable_silu_video').replace('sealed-DMA-PS-fixed159-video-numerical','sealed-DMA-SiLU-workspace-fixed159-video-numerical')
    s=s.replace('except (RetainedPSResourcesError,RetainedSlotError) as exc:','except RetainedSiluOwnerError as exc:').replace('PASS_M394_PS_VIDEO_NUMERICAL','PASS_M394_SILU_VIDEO_NUMERICAL')
    a=s.index("        text_path=Path('/home/ubuntu/m386_");z=s.index('        if os.geteuid()',a)
    s=s[:a]+f"        text_path=Path('/home/ubuntu/m393_silu_text_01/B1/load-memory.json')\n        text=json.loads(text_path.read_text(encoding='utf-8'))\n        if sha256(text_path)!='{raw}' or text['status']!='PASS_M393_SILU_TEXT_NUMERICAL' or not text['scope_weakref_dead']:raise RuntimeError('Actual SiLU text prerequisite differs')\n        result['silu_text_prerequisite_sha256']=sha256(text_path)\n"+s[z:]
    a=s.index('            plan=[(');z=s.index("            policy.capture('after-language-prefill-and-head'",a)
    s=s[:a]+"""            silu_scope=SiluLayerScope(model,policy,resident,enabled=True)
            scope_ref=weakref.ref(silu_scope)
            prefill_function=silu_scope.bind(sys.modules['m241_video_language_runtime'])
            output=prefill_function(model,hidden)
            silu_scope.close()
            result['silu_scope']=silu_scope.report()
            del prefill_function
            silu_scope=None
            if scope_ref() is not None:raise RetainedSiluOwnerError('Closed video SiLU scope retained')
            result['scope_weakref_dead']=True
            result['ps_prefetch_enabled']=False
            result['worker_started']=False
            result['silu_workspace_enabled']=True
            result['original_parser_workers']=1
            result['extra_pynq_allocations']=len(allocations)-7
"""+s[z:]
    s=s.replace('one ordinary PS slot, no extra CMA; original visual plus language and head','one ordinary5.900390625MiB SiLU workspace, no PS prefetch or extra CMA; original visual plus language and head')
    s=s.replace('Independent video adjudication; balanced full-request performance only after exact output and lifecycle PASS synchronized','Independent SiLU video numeric/lifetime closure; then lightweight original expression A/workspace B balanced full requests on same parallel hardware and one parser')
    assert 'VideoPSReadSession' not in s and 'RetainedPSResourcesError' not in s
    PKG.mkdir(parents=True)
    skip={'m387_ps_video_gate.py','m387_video_ps_read.py','m387_assemble.py','m387_export_result.py','run_m387_ps_video.sh','ps_read_ahead.py','m383_sealed_ps_read.py','m382_ps_slot.py','SHA256SUMS'}
    for r in m['files']:
        if r['path'] not in skip:shutil.copyfile(OLD/r['path'],PKG/r['path'])
    atomic(PKG/'m394_silu_video_gate.py',s.encode('utf-8'))
    for n in ('m393_silu_scope.py','m393_silu_workspace.py'):
        assert sha(TEXT/n)==sha(HERE/n);shutil.copyfile(TEXT/n,PKG/n)
    for src,dst in [('m387_export_result.py','m394_export_result.py'),('run_m387_ps_video.sh','run_m394_silu_video.sh')]:
        t=(OLD/src).read_text(encoding='utf-8').replace('M387','M394').replace('m387','m394').replace('m394_ps_video','m394_silu_video').replace('ENABLE_PS_VIDEO','ENABLE_SILU_VIDEO').replace('enable-ps-video','enable-silu-video').replace('sealed-DMA-PS-fixed159-video-numerical','sealed-DMA-SiLU-workspace-fixed159-video-numerical')
        atomic(PKG/dst,t.encode('utf-8'))
    t=(BASE/'candidates/M393-silu-text-01/m393_assemble.py').read_text(encoding='utf-8').replace('M393','M394').replace('/home/ubuntu/m386_ps_text_candidate_01',old_remote).replace(sha(BASE/'candidates/M386-ps-text-01/PACKAGE_MANIFEST.json'),sha(OLD/'PACKAGE_MANIFEST.json'))
    atomic(PKG/'m394_assemble.py',t.encode('utf-8'))
    trees={p.stem:ast.parse(p.read_text(encoding='utf-8'),feature_version=(3,10)) for p in PKG.glob('*.py')};allowed=set(sys.stdlib_module_names)|set(json.loads((PKG/'SOURCE_CLOSURE.json').read_text(encoding='utf-8'))['modules'])|{'numpy','pynq','tokenizers'};missing=[]
    for mod,tree in trees.items():
        for n in ast.walk(tree):
            names=[x.name.split('.')[0] for x in n.names] if isinstance(n,ast.Import) else ([(n.module or '').split('.')[0]] if isinstance(n,ast.ImportFrom) else [])
            missing.extend((mod,n) for n in names if n and n not in trees and n not in allowed)
    assert not missing,missing
    table=next(x for x in symtable.symtable(s,'gate','exec').get_children() if x.get_name()=='main');assert next(x for x in table.get_children() if x.get_name()=='tracked_allocate').lookup('SHAPES').is_global()
    assert next(x for x in table.get_children() if x.get_name()=='observed_prefill').lookup('silu_scope').is_nonlocal()
    for r in json.loads((PKG/'HARDWARE_CLOSURE.json').read_text(encoding='utf-8'))['prerequisites']:assert sha(ROOT/r['path'])==r['sha256']
    rows=[dict(path=p.name,bytes=p.stat().st_size,sha256=sha(p)) for p in sorted(PKG.iterdir())];atomic(PKG/'SHA256SUMS',''.join(r['sha256']+'  '+r['path']+'\n' for r in rows).encode('ascii'));rows.append(dict(path='SHA256SUMS',bytes=(PKG/'SHA256SUMS').stat().st_size,sha256=sha(PKG/'SHA256SUMS')))
    atomic(PKG/'PACKAGE_MANIFEST.json',encoded(dict(schema='M394-isolated-SiLU-fixed159-video-v1',files=rows,file_count=len(rows),total_bytes=sum(r['bytes'] for r in rows))))
    value=dict(status='PASS_OFFLINE_SILU_FIXED159_VIDEO_PREPARATION',manifest_sha256=sha(PKG/'PACKAGE_MANIFEST.json'),prior=prior,text_raw_sha256=raw,
               recursive_missing=missing,python310_syntax=True,workspace_shape=[159,9728],workspace_bytes=6187008,file_count=len(rows),total_bytes=sum(r['bytes'] for r in rows),
               original_parser_workers=1,PS_prefetch=False,extra_DMA_allowed=False,diagnostic_growth_budget_bytes=1024<<20,ordinary_margin_bytes=64<<20,
               exact_input_visual_weights_unchanged=True,production_policy_unchanged=True,board_run=False,performance_pass=False,test_support_pending=True)
    out=BASE/'runs/M394-silu-video-preparation-01/RESULT.json';atomic(out,encoded(value),immutable=True);d=sha(out)
    sync('latest_m394_silu_video_preparation',dict(status=value['status'],manifest_sha256=value['manifest_sha256'],sha256=d,result=out.relative_to(ROOT).as_posix()),
         f'## M394 SiLU固定159视频接入准备（2026-10-04）\n\n新固定文本原SHA {raw}闭合后，原最后帧两视图/分辨率/提示词/权重/视觉/159Token及36层完整输出参考，沿用同SHA SiLU scope。原单parser/暂存、0新DMA，原视频1GiB普通停止预算含5.900390625MiB工作缓冲和视觉缓存/159KV，64MiB普通余量/生产准入不改。SHA {d}，missing0/3.10，同SHA硬件/head观察复用；尚需实际stream/失败scope/回收支持，未新视频/性能PASS。')
    print(json.dumps(value|{'result_sha256':d}))

if __name__=='__main__':main()
