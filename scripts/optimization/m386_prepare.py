"""Original fixed30 text with one ordinary PS slot, gated by new layer closure."""
import ast,json,shutil,sys,symtable
from m351_workflow import ROOT,HERE,BASE,sha,atomic,encoded,sync
from m377_prepare import once
OLD=BASE/'candidates/M385-ps-layer-02'
TEXT=BASE/'candidates/M366-staged-text-03'
PKG=BASE/'candidates/M386-ps-text-01'
def main():
    if PKG.exists():raise RuntimeError('Immutable candidate exists')
    board=json.loads((ROOT/'deployment/mage_vl4b/BOARD_GATE_RESULT.json').read_text(encoding='utf-8'))
    prior=board['latest_m385_ps_layer_closure'];assert sha(ROOT/prior['result'])==prior['sha256']
    assert json.loads((ROOT/prior['result']).read_text(encoding='utf-8'))['status']=='PASS_SINGLE_LAYER_PS_PLAN_ONLY'
    assert all(prior['sha256'] in (ROOT/n).read_text(encoding='utf-8') for n in ('CURRENT_STATE.md','docsMILESTONES.md'))
    layer_raw=board['latest_m385_ps_layer_board']['sha256']
    for pkg in (OLD,TEXT):
        for r in json.loads((pkg/'PACKAGE_MANIFEST.json').read_text(encoding='utf-8'))['files']:assert sha(pkg/r['path'])==r['sha256']
    PKG.mkdir(parents=True)
    skip={'m366_assemble.py','m366_staged_text_gate.py','m366_export_result.py','run_m366_staged_text.sh','SHA256SUMS'}
    for r in json.loads((TEXT/'PACKAGE_MANIFEST.json').read_text(encoding='utf-8'))['files']:
        if r['path'] not in skip:shutil.copyfile(TEXT/r['path'],PKG/r['path'])
    for n in ('ps_read_ahead.py','m383_sealed_ps_read.py','m382_ps_slot.py','m370_patch_scope.py'):shutil.copyfile(OLD/n,PKG/n)
    # The same mathematical 256 MiB budget function is used by fixed text;
    # only the stage dispatcher expands from layer0 to all layers/head.
    s=(OLD/'m385_layer_ps_read.py').read_text(encoding='utf-8').replace('m365_stage_policy','m366_stage_policy').replace('LayerPSReadSession','TextPSReadSession').replace('layer diagnostic','fixed-text diagnostic')
    atomic(PKG/'m386_text_ps_read.py',s.encode('utf-8'))
    s=(TEXT/'m366_staged_text_gate.py').read_text(encoding='utf-8').replace('M366','M386').replace('m366_export_result','m386_export_result').replace('/home/ubuntu/m366_staged_text_02','/home/ubuntu/m386_ps_text_01').replace('--enable-staged-layer','--enable-ps-text').replace('args.enable_staged_layer','args.enable_ps_text').replace('independent-fixed-text-capacity-diagnostic','sealed-DMA-PS-fixed-text-numerical')
    s=once(s,'import traceback','import traceback\nimport weakref\nfrom m370_patch_scope import PatchScope\nfrom m386_text_ps_read import TextPSReadSession\nfrom ps_read_ahead import RetainedPSResourcesError\nfrom m382_ps_slot import RetainedSlotError')
    s=once(s,'allocations = []; restorations = []; slots = []','allocations = []; registry = PatchScope(); slots = []; ps_session = None')
    s=once(s,'original = getattr(obj,name); restorations.append((obj,name,original)); setattr(obj,name,replacement)\n        return original','return registry.patch(obj,name,replacement)')
    s=once(s,"        result['prior_board_sha256'] = PRIOR_SHA","        result['prior_board_sha256'] = PRIOR_SHA\n        layer_path=Path('/home/ubuntu/m385_ps_layer_01/B1/load-memory.json')\n        layer=json.loads(layer_path.read_text(encoding='utf-8'))\n        if sha256(layer_path)!='"+layer_raw+"' or layer['status']!='PASS_M385_PS_LAYER_NUMERICAL' or not layer['session_weakref_dead']:raise RuntimeError('Actual PS layer prerequisite differs')\n        result['PS_layer_prerequisite_sha256']=sha256(layer_path)")
    s=once(s,"        for name in ('_launch_prepacked','_launch_once'):","        patch(pynq,'allocate',forbid('extra-DMA.pynq.allocate',blocked))\n        patch(runtime,'allocate',forbid('extra-DMA.runtime.allocate',blocked))\n        def resident():\n            return (initialized and not runtime._m366_closed and engine.board is runtime\n                and engine.language is not None and engine.vision is not None and engine.tokenizer is not None\n                and len(allocations)==7 and not result['released_buffers'] and not blocked\n                and [int(x.nbytes) for x in allocations]==SHAPES and policy.safe())\n        for name in ('_launch_prepacked','_launch_once'):")
    s=once(s,"            setattr(runtime,name,policy.wrap_launch(getattr(runtime,name),name))","            patch(runtime,name,policy.wrap_launch(getattr(runtime,name),name))")
    s=once(s,'        token,logits,kv=model.prefill(hidden.copy())',"        plan=[(runtime.language_layout,runtime._language_chain(layer,name)) for layer,name in FAMILIES]\n        plan.extend((runtime.head_layout,chain) for chain in runtime.head_contract.chains)\n        if len(plan)!=162:raise RuntimeError('Fixed text 154 language plus8 head plan differs')\n        ps_session=TextPSReadSession(runtime,base,plan,enabled=True,policy=policy,resident=resident,completed_transaction_snapshot=base.transaction_snapshot(runtime.kernel,runtime.dma))\n        session_ref=weakref.ref(ps_session)\n        with ps_session:\n            token,logits,kv=model.prefill(hidden.copy())\n        result['ps_session']=ps_session.report()\n        ps_session=None\n        if session_ref() is not None:raise RetainedPSResourcesError('Closed fixed-text PS session retained')\n        result['session_weakref_dead']=True\n        result['ps_prefetch_enabled']=True\n        result['worker_started']=True\n        result['original_parser_workers']=1\n        result['extra_pynq_allocations']=len(allocations)-7")
    s=once(s,'    except CapacityRejected as exc:',"    except (RetainedPSResourcesError,RetainedSlotError) as exc:\n        unsafe=True;result['errors'].append(type(exc).__name__+': '+str(exc));result['traceback']=traceback.format_exc()\n    except CapacityRejected as exc:")
    s=once(s,'        # Keep guards installed until all resource cleanup is finished.','        # Keep guards installed until all resource cleanup is finished.\n        unsafe=unsafe or ps_session is not None')
    s=once(s,'            for obj,name,original in reversed(restorations): setattr(obj,name,original)',"            registry.restore_all(completion_proven=True,release_proven=True)\n            result['patch_registry_cleared']=not registry.entries")
    s=s.replace('PASS_M386_FIXED_TEXT_DIAGNOSTIC','PASS_M386_PS_TEXT_NUMERICAL').replace('no extra CMA/PS slot or visual forward','one ordinary PS slot, no extra CMA or visual forward').replace('Independent fixed-text adjudication then separately freeze actual video admission; no actual-video/performance unlocked automatically','Fixed-text PS numerical and lifecycle closure; only then independently budget fixed159 video; stop expansion on capacity/lifecycle issue')
    atomic(PKG/'m386_ps_text_gate.py',s.encode('utf-8'))
    for old,new in [('m385_assemble.py','m386_assemble.py'),('m385_export_result.py','m386_export_result.py'),('run_m385_ps_layer.sh','run_m386_ps_text.sh')]:
        s=(OLD/old).read_text(encoding='utf-8').replace('M385','M386').replace('m385','m386').replace('/home/ubuntu/m386_ps_layer','/home/ubuntu/m386_ps_text').replace('m386_ps_layer_gate','m386_ps_text_gate').replace('ENABLE_PS_LAYER','ENABLE_PS_TEXT').replace('--enable-ps-layer','--enable-ps-text').replace('sealed-DMA-PS-single-layer-numerical','sealed-DMA-PS-fixed-text-numerical')
        if old=='m385_assemble.py':s=s.replace('/home/ubuntu/m384_ps_chain_candidate_01','/home/ubuntu/m385_ps_layer_candidate_01').replace(sha(BASE/'candidates/M384-ps-chain-01/PACKAGE_MANIFEST.json'),sha(OLD/'PACKAGE_MANIFEST.json'))
        atomic(PKG/new,s.encode('utf-8'))
    closure=json.loads((PKG/'SOURCE_CLOSURE.json').read_text(encoding='utf-8'));trees={p.stem:ast.parse(p.read_text(encoding='utf-8'),feature_version=(3,10)) for p in PKG.glob('*.py')};allowed=set(sys.stdlib_module_names)|set(closure['modules'])|{'numpy','pynq','tokenizers'};missing=[]
    for mod,tree in trees.items():
        for node in ast.walk(tree):
            names=[n.name.split('.')[0] for n in node.names] if isinstance(node,ast.Import) else ([(node.module or '').split('.')[0]] if isinstance(node,ast.ImportFrom) else [])
            missing.extend((mod,n) for n in names if n and n not in trees and n not in allowed)
    assert not missing,missing
    table=next(t for t in symtable.symtable((PKG/'m386_ps_text_gate.py').read_text(encoding='utf-8'),'gate','exec').get_children() if t.get_name()=='main');assert next(t for t in table.get_children() if t.get_name()=='tracked_allocate').lookup('SHAPES').is_global()
    for n in ('m366_stage_policy.py','m366_head_observer.py','LAYER_EXPECTED.json','SOURCE_CLOSURE.json','HARDWARE_CLOSURE.json'):assert sha(PKG/n)==sha(TEXT/n)
    assert sha(PKG/'ps_read_ahead.py')==sha(OLD/'ps_read_ahead.py')
    rows=[dict(path=p.name,bytes=p.stat().st_size,sha256=sha(p)) for p in sorted(PKG.iterdir())];atomic(PKG/'SHA256SUMS',''.join(r['sha256']+'  '+r['path']+'\n' for r in rows).encode('ascii'));rows.append(dict(path='SHA256SUMS',bytes=(PKG/'SHA256SUMS').stat().st_size,sha256=sha(PKG/'SHA256SUMS')))
    atomic(PKG/'PACKAGE_MANIFEST.json',encoded(dict(schema='m386-sealed-PS-fixed-text-v1',files=rows,file_count=len(rows),total_bytes=sum(r['bytes'] for r in rows))))
    r=dict(status='PASS_OFFLINE_PS_FIXED_TEXT_PREPARATION',PS_layer_prerequisite_sha256=layer_raw,layer_closure_sha256=prior['sha256'],manifest_sha256=sha(PKG/'PACKAGE_MANIFEST.json'),package_files=len(rows),package_bytes=sum(x['bytes'] for x in rows),plan_language_windows=154,plan_head_windows=8,original_parser_workers=1,PS_source_unchanged=True,original30token_math_head_reference_policy_same_sha=True,diagnostic_growth_budget_bytes=256<<20,available_margin_bytes=64<<20,PS_payload_bytes=27852800,recursive_missing=missing,python310_syntax=True,board_run=False,performance_pass=False)
    p=BASE/'runs/M386-ps-text-preparation-01/RESULT.json';atomic(p,encoded(r),immutable=True);d=sha(p)
    sync('latest_m386_ps_text_preparation',dict(status=r['status'],result=p.relative_to(ROOT).as_posix(),sha256=d,manifest_sha256=r['manifest_sha256']),f'## M386 原固定文本PS预读准备（2026-10-03）\n\nM385新单层原SHA {layer_raw}和闭合已同步；原30Token/36层/完整head/151936logits及72KV参考，154语言＋8head窗口、原单parser。原真实head物理观察和256MiB总RSS停止预算同SHA，slot包括在预算内，64MiB普通余量、额外DMA封锁，原生产准入不改。准备SHA {d}；missing0/3.10通过，尚需实际编排/回收支持，不是新文本数值或性能。')
    print('M386_PREPARED',d,r['manifest_sha256'],len(rows))
if __name__=='__main__':main()
