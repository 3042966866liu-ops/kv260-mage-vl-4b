"""Freeze unchanged fixed159 video plus the verified one-slot PS schedule."""
import ast,json,shutil,sys,symtable
from m351_workflow import ROOT,HERE,BASE,sha,atomic,encoded,sync
from m377_prepare import once
OLD=BASE/'candidates/M386-ps-text-01'
VIDEO=BASE/'candidates/M380-gate-up-video-01'
PKG=BASE/'candidates/M387-ps-video-01'
def main():
    if PKG.exists():raise RuntimeError('Immutable candidate exists')
    b=json.loads((ROOT/'deployment/mage_vl4b/BOARD_GATE_RESULT.json').read_text(encoding='utf-8'));prior=b['latest_m386_ps_text_closure']
    assert sha(ROOT/prior['result'])==prior['sha256'] and json.loads((ROOT/prior['result']).read_text(encoding='utf-8'))['status']=='PASS_FIXED_TEXT_PS_PLAN_ONLY'
    assert all(prior['sha256'] in (ROOT/n).read_text(encoding='utf-8') for n in ('CURRENT_STATE.md','docsMILESTONES.md'))
    text_raw=b['latest_m386_ps_text_board']['sha256']
    for pkg in (OLD,VIDEO):
        for r in json.loads((pkg/'PACKAGE_MANIFEST.json').read_text(encoding='utf-8'))['files']:assert sha(pkg/r['path'])==r['sha256']
    PKG.mkdir(parents=True)
    skip={'m380_assemble.py','m380_staged_video_gate.py','m380_export_result.py','run_m380_staged_video.sh','m376_gate_up_workers.py','SHA256SUMS'}
    for r in json.loads((VIDEO/'PACKAGE_MANIFEST.json').read_text(encoding='utf-8'))['files']:
        if r['path'] not in skip:shutil.copyfile(VIDEO/r['path'],PKG/r['path'])
    for n in ('ps_read_ahead.py','m383_sealed_ps_read.py','m382_ps_slot.py','m370_patch_scope.py'):shutil.copyfile(OLD/n,PKG/n)
    s=(OLD/'m386_text_ps_read.py').read_text(encoding='utf-8').replace('m366_stage_policy','m368_stage_policy').replace('TextPSReadSession','VideoPSReadSession').replace('fixed-text diagnostic','fixed159-video diagnostic').replace('existing 256 MiB budget','existing video1GiB total budget')
    atomic(PKG/'m387_video_ps_read.py',s.encode('utf-8'))
    s=(VIDEO/'m380_staged_video_gate.py').read_text(encoding='utf-8').replace('M380','M387').replace('m380_export_result','m387_export_result').replace('/home/ubuntu/m380_gate_up_video_01','/home/ubuntu/m387_ps_video_01').replace('--enable-staged-video','--enable-ps-video').replace('args.enable_staged_video','args.enable_ps_video').replace('independent-fixed159-video-capacity-diagnostic','sealed-DMA-PS-fixed159-video-numerical')
    s=once(s,'import traceback','import traceback\nimport weakref\nfrom m370_patch_scope import PatchScope\nfrom m387_video_ps_read import VideoPSReadSession\nfrom ps_read_ahead import RetainedPSResourcesError\nfrom m382_ps_slot import RetainedSlotError')
    s=once(s,'allocations = []; restorations = []; slots = []','allocations = []; registry = PatchScope(); slots = []; ps_session = None')
    s=once(s,'original = getattr(obj,name); restorations.append((obj,name,original)); setattr(obj,name,replacement)\n        return original','return registry.patch(obj,name,replacement)')
    a=s.index("        text_path=Path('/home/ubuntu/m379_gate_up_text_01/");z=s.index('        if os.geteuid() != 0:',a)
    s=s[:a]+"        text_path=Path('/home/ubuntu/m386_ps_text_01/B1/load-memory.json')\n        text=json.loads(text_path.read_text(encoding='utf-8'))\n        if sha256(text_path)!='"+text_raw+"' or text['status']!='PASS_M386_PS_TEXT_NUMERICAL' or not text['session_weakref_dead']:raise RuntimeError('Actual PS text prerequisite differs')\n        result['PS_text_prerequisite_sha256']=sha256(text_path)\n"+s[z:]
    s=once(s,"        for name in ('_launch_prepacked','_launch_once'):","        patch(pynq,'allocate',forbid('extra-DMA.pynq.allocate',blocked))\n        patch(runtime,'allocate',forbid('extra-DMA.runtime.allocate',blocked))\n        def resident():\n            return (initialized and not runtime._m368_closed and engine.board is runtime\n                and engine.language is not None and engine.vision is not None and engine.tokenizer is not None\n                and len(allocations)==7 and not result['released_buffers'] and not blocked\n                and [int(x.nbytes) for x in allocations]==SHAPES and policy.safe())\n        for name in ('_launch_prepacked','_launch_once'):")
    s=once(s,"            setattr(runtime,name,policy.wrap_launch(getattr(runtime,name),name))","            patch(runtime,name,policy.wrap_launch(getattr(runtime,name),name))")
    s=once(s,'        def observed_prefill(hidden):','        def observed_prefill(hidden):\n            nonlocal ps_session')
    a=s.index('            from m376_gate_up_workers import GateUpWorkers');z=s.index("            policy.capture('after-language-prefill-and-head'",a)
    s=s[:a]+"            plan=[(runtime.language_layout,runtime._language_chain(layer,name)) for layer,name in FAMILIES]\n            plan.extend((runtime.head_layout,chain) for chain in runtime.head_contract.chains)\n            if len(plan)!=162:raise RuntimeError('Original video PS plan differs')\n            ps_session=VideoPSReadSession(runtime,base,plan,enabled=True,policy=policy,resident=resident,completed_transaction_snapshot=base.transaction_snapshot(runtime.kernel,runtime.dma))\n            session_ref=weakref.ref(ps_session)\n            with ps_session:\n                output=original_prefill(hidden)\n            result['ps_session']=ps_session.report()\n            ps_session=None\n            if session_ref() is not None:raise RetainedPSResourcesError('Closed video PS session retained')\n            result['session_weakref_dead']=True\n            result['ps_prefetch_enabled']=True\n            result['worker_started']=True\n            result['original_parser_workers']=1\n            result['extra_pynq_allocations']=len(allocations)-7\n"+s[z:]
    s=once(s,'    except CapacityRejected as exc:',"    except (RetainedPSResourcesError,RetainedSlotError) as exc:\n        unsafe=True;result['errors'].append(type(exc).__name__+': '+str(exc));result['traceback']=traceback.format_exc()\n    except CapacityRejected as exc:")
    s=once(s,'        # Keep guards installed until all resource cleanup is finished.','        # Keep guards installed until all resource cleanup is finished.\n        unsafe=unsafe or ps_session is not None')
    s=once(s,'            for obj,name,original in reversed(restorations): setattr(obj,name,original)',"            registry.restore_all(completion_proven=True,release_proven=True)\n            result['patch_registry_cleared']=not registry.entries")
    s=s.replace('PASS_M387_FIXED_VIDEO_DIAGNOSTIC','PASS_M387_PS_VIDEO_NUMERICAL').replace('no extra CMA/PS slot','one ordinary PS slot, no extra CMA')
    assert 'GateUpWorkers' not in s
    atomic(PKG/'m387_ps_video_gate.py',s.encode('utf-8'))
    # Two already verified immutable sources avoid retransmitting numeric refs.
    assembly=(OLD/'m386_assemble.py').read_text(encoding='utf-8').replace('M386','M387').replace('/home/ubuntu/m385_ps_layer_candidate_01','/home/ubuntu/m386_ps_text_candidate_01').replace(sha(BASE/'candidates/M385-ps-layer-02/PACKAGE_MANIFEST.json'),sha(OLD/'PACKAGE_MANIFEST.json'))
    assembly=once(assembly,"    names=set()","    secondary=Path('/home/ubuntu/m380_gate_up_video_candidate_01')\n    if sha(secondary/'PACKAGE_MANIFEST.json')!='"+sha(VIDEO/'PACKAGE_MANIFEST.json')+"':raise RuntimeError('Secondary manifest differs')\n    second={r['path']:r for r in json.loads((secondary/'PACKAGE_MANIFEST.json').read_text(encoding='utf-8'))['files']}\n    names=set()")
    assembly=once(assembly,"            if name not in prior or prior[name]!=row:raise RuntimeError('New payload missing')\n            source=OLD/name","            if prior.get(name)==row:source=OLD/name\n            elif second.get(name)==row:source=secondary/name\n            else:raise RuntimeError('New payload missing')")
    atomic(PKG/'m387_assemble.py',assembly.encode('utf-8'))
    for old,new in [('m386_export_result.py','m387_export_result.py'),('run_m386_ps_text.sh','run_m387_ps_video.sh')]:
        a=(OLD/old).read_text(encoding='utf-8').replace('M386','M387').replace('m386','m387').replace('/home/ubuntu/m387_ps_text','/home/ubuntu/m387_ps_video').replace('m387_ps_text_gate','m387_ps_video_gate').replace('ENABLE_PS_TEXT','ENABLE_PS_VIDEO').replace('--enable-ps-text','--enable-ps-video').replace('sealed-DMA-PS-fixed-text-numerical','sealed-DMA-PS-fixed159-video-numerical')
        atomic(PKG/new,a.encode('utf-8'))
    closure=json.loads((PKG/'SOURCE_CLOSURE.json').read_text(encoding='utf-8'));trees={p.stem:ast.parse(p.read_text(encoding='utf-8'),feature_version=(3,10)) for p in PKG.glob('*.py')};allowed=set(sys.stdlib_module_names)|set(closure['modules'])|{'numpy','pynq','tokenizers'};missing=[]
    for mod,tree in trees.items():
        for node in ast.walk(tree):
            names=[n.name.split('.')[0] for n in node.names] if isinstance(node,ast.Import) else ([(node.module or '').split('.')[0]] if isinstance(node,ast.ImportFrom) else [])
            missing.extend((mod,n) for n in names if n and n not in trees and n not in allowed)
    assert not missing,missing
    table=next(t for t in symtable.symtable(s,'gate','exec').get_children() if t.get_name()=='main');assert next(t for t in table.get_children() if t.get_name()=='tracked_allocate').lookup('SHAPES').is_global()
    assert next(t for t in table.get_children() if t.get_name()=='observed_prefill').lookup('ps_session').is_nonlocal()
    for n in ('m368_stage_policy.py','m368_head_observer.py','VIDEO_EXPECTED.json','VISUAL_EXPECTED.json','frozen_video_identity.py','SOURCE_CLOSURE.json','HARDWARE_CLOSURE.json'):assert sha(PKG/n)==sha(VIDEO/n)
    assert sha(PKG/'ps_read_ahead.py')==sha(OLD/'ps_read_ahead.py')
    rows=[dict(path=p.name,bytes=p.stat().st_size,sha256=sha(p)) for p in sorted(PKG.iterdir())];atomic(PKG/'SHA256SUMS',''.join(r['sha256']+'  '+r['path']+'\n' for r in rows).encode('ascii'));rows.append(dict(path='SHA256SUMS',bytes=(PKG/'SHA256SUMS').stat().st_size,sha256=sha(PKG/'SHA256SUMS')))
    atomic(PKG/'PACKAGE_MANIFEST.json',encoded(dict(schema='m387-sealed-PS-fixed159-video-v1',files=rows,file_count=len(rows),total_bytes=sum(r['bytes'] for r in rows))))
    r=dict(status='PASS_OFFLINE_PS_FIXED159_VIDEO_PREPARATION',PS_text_prerequisite_sha256=text_raw,text_closure_sha256=prior['sha256'],manifest_sha256=sha(PKG/'PACKAGE_MANIFEST.json'),package_files=len(rows),package_bytes=sum(x['bytes'] for x in rows),source_manifests=dict(PS_text=sha(OLD/'PACKAGE_MANIFEST.json'),old_video=sha(VIDEO/'PACKAGE_MANIFEST.json')),plan_language_windows=154,plan_head_windows=8,original_parser_workers=1,PS_source_unchanged=True,original_video_visual_math_head_reference_policy_same_sha=True,diagnostic_growth_budget_bytes=1024<<20,available_margin_bytes=64<<20,PS_payload_bytes=27852800,recursive_missing=missing,python310_syntax=True,board_run=False,performance_pass=False,budget_scope='Existing whole-video1GiB RSS ceiling since full runtime/7DMA seal; includes visual unpacking/lazy caches/features159KV/temporary arrays/PS slot. Stop ceiling, not native peak certificate')
    p=BASE/'runs/M387-ps-video-preparation-01/RESULT.json';atomic(p,encoded(r),immutable=True);d=sha(p)
    sync('latest_m387_ps_video_preparation',dict(status=r['status'],result=p.relative_to(ROOT).as_posix(),sha256=d,manifest_sha256=r['manifest_sha256']),f'## M387 原159视频PS预读准备（2026-10-03）\n\nM386文本原SHA {text_raw}和闭合已同步；原最后帧两视图/分辨率/提示词/159Token/权重、视觉与全部语言/logits/72KV/判断参考保持。原单parser＋162PS窗口，slot包含在原全视频1GiB RSS停止上限，64MiB普通余量；视觉后及每次提交检查、0新增DMA/原生产准入不改。准备SHA {d}；missing0/3.10/PSowner nonlocal核对；两旧包依赖复制须独立故障门禁，未上传/新视频数值或性能。')
    print('M387_PREPARED',d,r['manifest_sha256'],len(rows))
if __name__=='__main__':main()
