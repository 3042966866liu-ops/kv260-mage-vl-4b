"""Freeze one original layer with five PS windows, after complete-chain closure."""
import ast, json, shutil, sys, symtable
from m351_workflow import ROOT,HERE,BASE,sha,atomic,encoded,sync
from m377_prepare import once
OLD=BASE/'candidates/M384-ps-chain-01'
LAYER=BASE/'candidates/M378-gate-up-layer-01'
PKG=BASE/'candidates/M385-ps-layer-02'
RAW='31121b29b1a1fbcd6f578bc2f984b0bbca4a12420fdf3fc0481fd7eb16df2277'

def main():
    if PKG.exists():raise RuntimeError('Immutable candidate exists')
    board=json.loads((ROOT/'deployment/mage_vl4b/BOARD_GATE_RESULT.json').read_text(encoding='utf-8'))
    prior=board['latest_m384_ps_chain_closure']
    assert sha(ROOT/prior['result'])==prior['sha256']
    assert json.loads((ROOT/prior['result']).read_text(encoding='utf-8'))['status']=='PASS_COMPLETE_Q_CHAIN_PS_BINDING_ONLY'
    assert all(prior['sha256'] in (ROOT/n).read_text(encoding='utf-8') for n in ('CURRENT_STATE.md','docsMILESTONES.md'))
    m=json.loads((OLD/'PACKAGE_MANIFEST.json').read_text(encoding='utf-8'))
    for r in m['files']:assert sha(OLD/r['path'])==r['sha256']
    lm=json.loads((LAYER/'PACKAGE_MANIFEST.json').read_text(encoding='utf-8'))
    for r in lm['files']:assert sha(LAYER/r['path'])==r['sha256']
    PKG.mkdir(parents=True)
    exclude={'m384_assemble.py','m384_ps_chain_gate.py','m384_export_result.py','run_m384_ps_chain.sh','SHA256SUMS'}
    for r in m['files']:
        if r['path'] not in exclude:shutil.copyfile(OLD/r['path'],PKG/r['path'])
    for n in ('frozen_one_layer.py','LAYER_EXPECTED.json','m343_layer_scope.py'):shutil.copyfile(LAYER/n,PKG/n)
    shutil.copyfile(HERE/'m385_layer_ps_read.py',PKG/'m385_layer_ps_read.py')
    s=(LAYER/'m378_staged_layer_gate.py').read_text(encoding='utf-8').replace('M378','M385').replace('m378_export_result','m385_export_result').replace('/home/ubuntu/m378_gate_up_layer_01','/home/ubuntu/m385_ps_layer_01').replace('--enable-staged-layer','--enable-ps-layer').replace('args.enable_staged_layer','args.enable_ps_layer').replace('independent-single-layer-capacity-diagnostic','sealed-DMA-PS-single-layer-numerical')
    s=once(s,'import traceback','import traceback\nimport weakref\nfrom m370_patch_scope import PatchScope\nfrom m385_layer_ps_read import LayerPSReadSession\nfrom ps_read_ahead import RetainedPSResourcesError\nfrom m382_ps_slot import RetainedSlotError')
    s=once(s,'allocations = []; restorations = []; slots = []','allocations = []; registry = PatchScope(); slots = []; ps_session = None')
    s=once(s,'original = getattr(obj,name); restorations.append((obj,name,original)); setattr(obj,name,replacement)\n        return original','return registry.patch(obj,name,replacement)')
    a=s.index("        family_path=Path(");b=s.index('        if os.geteuid()',a)
    s=s[:a]+"        chain_path=Path('/home/ubuntu/m384_ps_chain_01/B1/load-memory.json')\n        chain_proof=json.loads(chain_path.read_text(encoding='utf-8'))\n        if sha256(chain_path)!='"+RAW+"' or chain_proof['status']!='PASS_M384_PS_CHAIN_NUMERICAL' or not chain_proof['session_weakref_dead']:raise RuntimeError('Actual PS chain prerequisite differs')\n        result['chain_prerequisite_sha256']=sha256(chain_path)\n"+s[b:]
    s=once(s,"        for name in ('_launch_prepacked','_launch_once'):","        patch(pynq,'allocate',forbid('extra-DMA.pynq.allocate',blocked))\n        patch(runtime,'allocate',forbid('extra-DMA.runtime.allocate',blocked))\n        def resident():\n            return (initialized and not runtime._m365_closed and engine.board is runtime\n                and engine.language is not None and engine.vision is not None and engine.tokenizer is not None\n                and len(allocations)==7 and not result['released_buffers'] and not blocked\n                and [int(x.nbytes) for x in allocations]==SHAPES and policy.safe())\n        for name in ('_launch_prepacked','_launch_once'):")
    s=once(s,"            setattr(runtime,name,policy.wrap_launch(getattr(runtime,name),name))","            patch(runtime,name,policy.wrap_launch(getattr(runtime,name),name))")
    a=s.index('        from m376_gate_up_workers import GateUpWorkers');b=s.index("        policy.capture('after-layer0'",a)
    s=s[:a]+"        plan=[(runtime.language_layout,runtime._language_chain(0,name)) for name in FAMILIES]\n        ps_session=LayerPSReadSession(runtime,base,plan,enabled=True,policy=policy,resident=resident,completed_transaction_snapshot=base.transaction_snapshot(runtime.kernel,runtime.dma))\n        session_ref=weakref.ref(ps_session)\n        with ps_session:\n            output,kv=one_layer(model,hidden.copy())\n        result['ps_session']=ps_session.report()\n        ps_session=None\n        if session_ref() is not None:raise RetainedPSResourcesError('Closed PS layer session still retained')\n        result['session_weakref_dead']=True\n        result['ps_prefetch_enabled']=True\n        result['worker_started']=True\n        result['original_parser_workers']=1\n        result['extra_pynq_allocations']=len(allocations)-7\n"+s[b:]
    s=once(s,'    except CapacityRejected as exc:',"    except (RetainedPSResourcesError,RetainedSlotError) as exc:\n        unsafe=True;result['errors'].append(type(exc).__name__+': '+str(exc));result['traceback']=traceback.format_exc()\n    except CapacityRejected as exc:")
    s=once(s,'        # Keep guards installed until all resource cleanup is finished.','        # Keep guards installed until all resource cleanup is finished.\n        unsafe=unsafe or ps_session is not None')
    s=once(s,'            for obj,name,original in reversed(restorations): setattr(obj,name,original)',"            registry.restore_all(completion_proven=True,release_proven=True)\n            result['patch_registry_cleared']=not registry.entries")
    s=s.replace('PASS_M385_SINGLE_LAYER_DIAGNOSTIC','PASS_M385_PS_LAYER_NUMERICAL').replace('Original complete runtime and one layer retained; gate_up two parser workers only; no extra CMA/PS slot; production policy unchanged','Original complete runtime/seven DMA, original one parser; five-window PS slot within existing layer budget; production policy unchanged').replace('Independent layer adjudication then separately freeze fixed-text admission; no full-model/video/performance unlocked automatically','Single-layer PS numerical/lifecycle closure and triad; only then prepare fixed-text PS plan; stop expansion on capacity/lifecycle issue')
    atomic(PKG/'m385_ps_layer_gate.py',s.encode('utf-8'))
    for old,new in [('m384_assemble.py','m385_assemble.py'),('m384_export_result.py','m385_export_result.py'),('run_m384_ps_chain.sh','run_m385_ps_layer.sh')]:
        s=(OLD/old).read_text(encoding='utf-8').replace('M384','M385').replace('m384','m385').replace('/home/ubuntu/m385_ps_chain','/home/ubuntu/m385_ps_layer').replace('m385_ps_chain_gate','m385_ps_layer_gate').replace('ENABLE_PS_CHAIN','ENABLE_PS_LAYER').replace('--enable-ps-chain','--enable-ps-layer').replace('sealed-DMA-PS-single-chain-numerical','sealed-DMA-PS-single-layer-numerical')
        if old=='m384_assemble.py':s=s.replace('/home/ubuntu/m383_ps_descriptor_candidate_01','/home/ubuntu/m384_ps_chain_candidate_01').replace(sha(BASE/'candidates/M383-ps-descriptor-01/PACKAGE_MANIFEST.json'),sha(OLD/'PACKAGE_MANIFEST.json'))
        atomic(PKG/new,s.encode('utf-8'))
    closure=json.loads((PKG/'SOURCE_CLOSURE.json').read_text(encoding='utf-8'));trees={p.stem:ast.parse(p.read_text(encoding='utf-8'),feature_version=(3,10)) for p in PKG.glob('*.py')};allowed=set(sys.stdlib_module_names)|set(closure['modules'])|{'numpy','pynq','tokenizers'};missing=[]
    for mod,tree in trees.items():
        for node in ast.walk(tree):
            names=[n.name.split('.')[0] for n in node.names] if isinstance(node,ast.Import) else ([(node.module or '').split('.')[0]] if isinstance(node,ast.ImportFrom) else [])
            missing.extend((mod,n) for n in names if n and n not in trees and n not in allowed)
    assert not missing,missing
    gate=(PKG/'m385_ps_layer_gate.py').read_text(encoding='utf-8');symbols=next(t for t in symtable.symtable(gate,'gate','exec').get_children() if t.get_name()=='main');assert next(t for t in symbols.get_children() if t.get_name()=='tracked_allocate').lookup('SHAPES').is_global()
    for n in ('ps_read_ahead.py','m383_sealed_ps_read.py','m382_ps_slot.py','m365_stage_policy.py','m370_patch_scope.py'):assert sha(PKG/n)==sha(OLD/n)
    assert 'GateUpWorkers' not in gate
    for row in json.loads((PKG/'HARDWARE_CLOSURE.json').read_text(encoding='utf-8'))['prerequisites']:assert sha(ROOT/row['path'])==row['sha256']
    rows=[dict(path=p.name,bytes=p.stat().st_size,sha256=sha(p)) for p in sorted(PKG.iterdir())];atomic(PKG/'SHA256SUMS',''.join(r['sha256']+'  '+r['path']+'\n' for r in rows).encode('ascii'));rows.append(dict(path='SHA256SUMS',bytes=(PKG/'SHA256SUMS').stat().st_size,sha256=sha(PKG/'SHA256SUMS')))
    atomic(PKG/'PACKAGE_MANIFEST.json',encoded(dict(schema='m385-sealed-PS-layer-v1',files=rows,file_count=len(rows),total_bytes=sum(r['bytes'] for r in rows))))
    r=dict(status='PASS_OFFLINE_PS_SINGLE_LAYER_PREPARATION',chain_raw_sha256=RAW,chain_closure_sha256=prior['sha256'],manifest_sha256=sha(PKG/'PACKAGE_MANIFEST.json'),package_files=len(rows),package_bytes=sum(x['bytes'] for x in rows),recursive_missing=missing,python310_syntax=True,original_parser_workers=1,PS_source_unchanged=True,production64MiB_unchanged=True,diagnostic_growth_budget_bytes=256<<20,available_margin_bytes=64<<20,PS_payload_bytes=27852800,budget_reason='Existing independent single-layer total RSS ceiling, includes slot; not a predicted native peak. Slot26.5625MiB+previous observed layer43.08984375MiB motivates combined monitoring rather than applying load-only64MiB ceiling to all inference.',board_run=False,performance_pass=False)
    p=BASE/'runs/M385-ps-layer-preparation-01/RESULT.json';atomic(p,encoded(r),immutable=True);d=sha(p)
    sync('latest_m385_ps_layer_preparation',dict(status=r['status'],result=p.relative_to(ROOT).as_posix(),sha256=d,manifest_sha256=r['manifest_sha256']),f'## M385 原单层五family PS预读准备（2026-10-03）\n\nM384完整Q闭合已同步；原layer0/159重复文本embedding、五family/hidden/KV原参考、单parser，只有原PS slot连续五窗口。封锁公共及捕获分配入口，slot/层共用原独立256MiB RSS增长预算及64MiB可用余量，原生产64MiB不改；这是停止上限非真实峰值证明。missing0/3.10/同SHA数学与电路证据通过；准备SHA {d}。尚需实际编排/新准入/回收检查，未上板或新增性能。')
    print('M385_PREPARED',d,r['manifest_sha256'],len(rows),r['package_bytes'])
if __name__=='__main__':main()
