"""Freeze a new load-only entry; preserve existing production/PS component guards."""
import ast,json,shutil,subprocess,sys,symtable
from m351_workflow import ROOT,HERE,BASE,sha,atomic,encoded,sync
from m377_prepare import once
OLD=BASE/'candidates/M378-gate-up-layer-01'
PKG=BASE/'candidates/M382-sealed-ps-slot-01'


def main():
    if PKG.exists():raise RuntimeError('Immutable candidate exists')
    recovery={}
    for n in ('CURRENT_STATE.md','DEPLOYMENT_OPERATION_MISTAKES_REVIEW.md','docsMILESTONES.md','deployment/mage_vl4b/BOARD_GATE_RESULT.json'):
        value=(ROOT/n).read_text(encoding='utf-8-sig');recovery[n]=dict(sha256=sha(ROOT/n),characters=len(value))
    board=json.loads((ROOT/'deployment/mage_vl4b/BOARD_GATE_RESULT.json').read_text(encoding='utf-8'))
    priors={}
    for key in ('latest_m351_ps_component_board','latest_m372_prefetch_future_review','latest_m381_gate_up_performance_closure'):
        row=board[key];assert sha(ROOT/row['result'])==row['sha256']
        assert all(row['sha256'] in (ROOT/n).read_text(encoding='utf-8-sig') for n in ('CURRENT_STATE.md','docsMILESTONES.md'));priors[key]=row['sha256']
    tests=subprocess.run([sys.executable,'-B',str(HERE/'test_m382_ps_slot.py')],capture_output=True,text=True,encoding='utf-8')
    if tests.returncode or 'Ran 11 tests' not in tests.stderr:raise RuntimeError(tests.stdout+tests.stderr)
    manifest=json.loads((OLD/'PACKAGE_MANIFEST.json').read_text(encoding='utf-8'))
    for row in manifest['files']:assert sha(OLD/row['path'])==row['sha256']
    PKG.mkdir(parents=True)
    excluded={'m378_assemble.py','m378_staged_layer_gate.py','m378_export_result.py','run_m378_staged_layer.sh','SHA256SUMS','frozen_one_layer.py','m343_layer_scope.py','m376_gate_up_workers.py','LAYER_EXPECTED.json'}
    for row in manifest['files']:
        if row['path'] not in excluded:shutil.copyfile(OLD/row['path'],PKG/row['path'])
    shutil.copyfile(HERE/'m382_ps_slot.py',PKG/'m382_ps_slot.py')
    shutil.copyfile(HERE/'m370_patch_scope.py',PKG/'m370_patch_scope.py')
    source=(OLD/'m378_staged_layer_gate.py').read_text(encoding='utf-8').replace('M378','M382').replace('m378_export_result','m382_export_result').replace('/home/ubuntu/m378_gate_up_layer_01','/home/ubuntu/m382_sealed_ps_slot_01').replace('--enable-staged-layer','--enable-load-only-slot').replace('args.enable_staged_layer','args.enable_load_only_slot').replace('independent-single-layer-capacity-diagnostic','sealed-DMA-load-only-PS-slot-diagnostic')
    source=once(source,'from m365_stage_policy import StagePolicy,SHAPES','from m365_stage_policy import StagePolicy,SHAPES\nfrom m382_ps_slot import run_probe,RetainedSlotError\nfrom m370_patch_scope import PatchScope')
    source=once(source,"BLOCKED_BOARD_METHODS = ('lm_head',)","BLOCKED_BOARD_METHODS = ('_execute','_launch_once','_launch_prepacked','_stage','language_family_many','language_family','lm_head')")
    source=once(source,'allocations = []; restorations = []; slots = []','allocations = []; registry = PatchScope(); slots = []')
    source=once(source,'        original = getattr(obj,name); restorations.append((obj,name,original)); setattr(obj,name,replacement)\n        return original','        return registry.patch(obj,name,replacement)')
    source=once(source,"for name in ('prefill','decode'):","for name in ('prefill','decode','_family'):")
    start=source.index('        import numpy as np\n',source.index("result['loaded_capacity']=capacity(loaded)"))
    end=source.index("        result['boot_unchanged']",start)
    source=source[:start]+'''        policy.seal(allocations,int(TARGET_BUILD,16))
        result['production_threshold_would_admit']=result['loaded_capacity']['meets_threshold']
        result['additional_cma_requests_allowed']=False
        result['allocator_sealed']=True
        # Both public and captured allocator paths refuse all future calls.
        patch(pynq,'allocate',forbid('extra-DMA.pynq.allocate',blocked))
        patch(runtime,'allocate',forbid('extra-DMA.runtime.allocate',blocked))
        patch(runtime.dma.sendchannel,'transfer',forbid('PL.MM2S.transfer',blocked))
        patch(runtime.dma.recvchannel,'transfer',forbid('PL.S2MM.transfer',blocked))
        patch(runtime.kernel,'write',forbid('PL.kernel.write',blocked))
        def resident():
            return (initialized and not runtime._m365_closed and engine.board is runtime
                and engine.language is not None and engine.vision is not None and engine.tokenizer is not None
                and len(allocations)==7 and not result['released_buffers'] and not blocked
                and [int(b.nbytes) for b in allocations]==SHAPES
                and runtime.host_calls==runtime.logical_calls==0 and policy.safe())
        result['resident_before_slot']=resident()
        if not result['resident_before_slot']:raise RuntimeError('Complete resident runtime/seven DMA closure differs')
        run_probe(slots,result['ps_slot'],policy.snapshot,policy.counters,mark,resident)
        result['resident_after_slot_release']=resident()
        result['load_only_slot_pass']=True
        result['extra_pynq_allocations']=len(allocations)-7
        result['ps_prefetch_enabled']=False
        result['status']='PASS_M382_SEALED_LOAD_ONLY_PS_SLOT'
        result['memory_capacity_proven']=False
'''+source[end:]
    source=once(source,'    except CapacityRejected as exc:',"    except RetainedSlotError as exc:\n        unsafe=True; result['errors'].append(type(exc).__name__+': '+str(exc)); result['traceback']=traceback.format_exc()\n    except CapacityRejected as exc:")
    source=once(source,'        # Keep guards installed until all resource cleanup is finished.','        # Keep guards installed until all resource cleanup is finished.\n        unsafe = unsafe or bool(slots)')
    source=once(source,'            for obj,name,original in reversed(restorations): setattr(obj,name,original)','            registry.restore_all(completion_proven=True,release_proven=True)\n            result[\'patch_registry_cleared\']=not registry.entries')
    source=source.replace('PASS_M382_SINGLE_LAYER_DIAGNOSTIC','PASS_M382_SEALED_LOAD_ONLY_PS_SLOT')
    source=source.replace('Original complete runtime and one layer retained; gate_up two parser workers only; no extra CMA/PS slot; production policy unchanged','Complete runtime/seven original DMA retained; touched ordinary PS slot then sole-owner release; no forward/worker/PL; production policy unchanged')
    source=source.replace('Independent layer adjudication then separately freeze fixed-text admission; no full-model/video/performance unlocked automatically','Adjudicate slot-only raw and lifecycle; only after triad synchronization prepare isolated PS read binding at descriptor/chain level; stop expansion on capacity/lifecycle failure')
    assert 'GateUpWorkers' not in source and 'minimal=' not in source and 'one_layer' not in source
    atomic(PKG/'m382_load_slot_gate.py',source.encode('utf-8'))
    assembly=(OLD/'m378_assemble.py').read_text(encoding='utf-8').replace('M378','M382').replace('/home/ubuntu/m377_gate_up_pair_candidate_01','/home/ubuntu/m378_gate_up_layer_candidate_01').replace('c211d99d3b279555a9e93d5f26a7a5aa6179062a1ab1aad801fae3862fd61c9f',sha(OLD/'PACKAGE_MANIFEST.json'))
    atomic(PKG/'m382_assemble.py',assembly.encode('utf-8'))
    exporter=(OLD/'m378_export_result.py').read_text(encoding='utf-8').replace('M378','M382').replace('/home/ubuntu/m378_gate_up_layer_01','/home/ubuntu/m382_sealed_ps_slot_01').replace('independent-single-layer-capacity-diagnostic','sealed-DMA-load-only-PS-slot-diagnostic')
    atomic(PKG/'m382_export_result.py',exporter.encode('utf-8'))
    runner=(OLD/'run_m378_staged_layer.sh').read_text(encoding='utf-8').replace('M378','M382').replace('m378_export_result','m382_export_result').replace('m378_staged_layer_gate','m382_load_slot_gate').replace('/home/ubuntu/m378_gate_up_layer_01','/home/ubuntu/m382_sealed_ps_slot_01').replace('ENABLE_STAGED_LAYER','ENABLE_LOAD_ONLY_SLOT').replace('--enable-staged-layer','--enable-load-only-slot')
    atomic(PKG/'run_m382_load_slot.sh',runner.encode('utf-8'))
    closure=json.loads((PKG/'SOURCE_CLOSURE.json').read_text(encoding='utf-8'));trees={p.stem:ast.parse(p.read_text(encoding='utf-8'),feature_version=(3,10)) for p in PKG.glob('*.py')};allowed=set(sys.stdlib_module_names)|set(closure['modules'])|{'numpy','pynq','tokenizers'};missing=[]
    for mod,tree in trees.items():
        for node in ast.walk(tree):
            names=[n.name.split('.')[0] for n in node.names] if isinstance(node,ast.Import) else ([(node.module or '').split('.')[0]] if isinstance(node,ast.ImportFrom) else [])
            missing.extend((mod,n) for n in names if n and n not in trees and n not in allowed)
    assert not missing,missing
    symbols=next(t for t in symtable.symtable(source,'gate','exec').get_children() if t.get_name()=='main');assert next(t for t in symbols.get_children() if t.get_name()=='tracked_allocate').lookup('SHAPES').is_global()
    assert source.index('engine.load()')<source.index('run_probe(slots,')
    assert 'runtime.allocate' in source and 'PL.kernel.write' in source
    hw=json.loads((PKG/'HARDWARE_CLOSURE.json').read_text(encoding='utf-8'))
    for row in hw['prerequisites']:assert sha(ROOT/row['path'])==row['sha256']
    rows=[dict(path=p.name,bytes=p.stat().st_size,sha256=sha(p)) for p in sorted(PKG.iterdir())]
    atomic(PKG/'SHA256SUMS',''.join(r['sha256']+'  '+r['path']+'\n' for r in rows).encode('ascii'));rows.append(dict(path='SHA256SUMS',bytes=(PKG/'SHA256SUMS').stat().st_size,sha256=sha(PKG/'SHA256SUMS')))
    atomic(PKG/'PACKAGE_MANIFEST.json',encoded(dict(schema='m382-sealed-load-only-ps-slot-v1',files=rows,file_count=len(rows),total_bytes=sum(r['bytes'] for r in rows))))
    out=BASE/'runs/M382-sealed-ps-slot-preparation-01'
    atomic(out/'TEST_OUTPUT.txt',(tests.stdout+tests.stderr).encode('utf-8'))
    value=dict(status='PASS_OFFLINE_SEALED_PS_SLOT_PREPARATION',manifest_sha256=sha(PKG/'PACKAGE_MANIFEST.json'),recovery_reads=recovery,prior_sha256=priors,tests=11,tests_actual_bytearrays_and_weakrefs=True,explicit_fake_memory_runtime_in_host_tests=True,recursive_missing=missing,python310_syntax=True,original_loader_and_hardware_reused=True,production64MiB_unchanged=True,old_PS_component_unchanged=True,slot_bytes=27852800,load_only_PS_growth_ceiling_bytes=64<<20,available_margin_bytes=64<<20,additional_dma_calls=0,model_forward_calls=0,physical_transactions=0,board_run=False,performance_pass=False,source_sha256={'helper':sha(HERE/'m382_ps_slot.py'),'tests':sha(HERE/'test_m382_ps_slot.py')})
    rejected=BASE/'runs/M382-offline-rejection-01/RESULT.json'
    value['rejected_attempts']=dict(result=rejected.relative_to(ROOT).as_posix(),sha256=sha(rejected),failures=2,board_run=False)
    atomic(out/'RESULT.json',encoded(value),immutable=True);digest=sha(out/'RESULT.json')
    sync('latest_m382_sealed_ps_slot_preparation',dict(status=value['status'],result=(out/'RESULT.json').relative_to(ROOT).as_posix(),sha256=digest,manifest_sha256=value['manifest_sha256']),f'## M382 七DMA封锁后完整runtime＋PS slot只加载准备（2026-10-03）\n\n复用同SHA loader/幂等释放/硬件；全部forward、两transfer及kernel.write封锁，额外DMA公共/捕获入口拒绝。slot27,852,800B，普通PS增长64MiB实验上限＋64MiB剩余预算余量，基准在slot前；生产及原预读64MiB CMA不改。11项实际bytearray/weakref＋显式memory/runtime替身检查，缺失依赖0/3.10/作用域通过；单独释放slot并保留runtime后观察，RSS不要求回落。准备 SHA {digest}；未上传/Overlay，下一步控制与原字节回收支持。')
    print('M382_PREPARED',digest,value['manifest_sha256'],len(rows))


if __name__=='__main__':main()
