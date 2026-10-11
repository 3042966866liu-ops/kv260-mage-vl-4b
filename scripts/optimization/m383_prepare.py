"""First new PS binding: same frozen single descriptor, no model forward."""
import ast,json,shutil,subprocess,sys,symtable
from m351_workflow import ROOT,HERE,BASE,sha,atomic,encoded,sync
from m377_prepare import once
OLD=BASE/'candidates/M382-sealed-ps-slot-01'
TEMPLATE=BASE/'candidates/M378-gate-up-layer-01'
PKG=BASE/'candidates/M383-ps-descriptor-01'
SLOT_RAW='178a914e34cf0cb9a74b19853b01ee5f7fd549059b9b7a9a42cc3827332d7a5a'
ORIGINAL_PS='4cd28217f1bf8b36cb29d80ff16c64d7e10d5240b20a7c2a8cc5849ee39aabd2'
def main():
    if PKG.exists():raise RuntimeError('Immutable candidate exists')
    board=json.loads((ROOT/'deployment/mage_vl4b/BOARD_GATE_RESULT.json').read_text(encoding='utf-8'))
    prior=board['latest_m382_sealed_ps_slot_closure'];assert sha(ROOT/prior['result'])==prior['sha256']
    assert json.loads((ROOT/prior['result']).read_text(encoding='utf-8'))['status']=='PASS_LOAD_ONLY_SLOT_LIFECYCLE_PRECONDITION'
    assert all(prior['sha256'] in (ROOT/n).read_text(encoding='utf-8-sig') for n in ('CURRENT_STATE.md','docsMILESTONES.md'))
    assert sha(HERE/'ps_read_ahead.py')==ORIGINAL_PS
    # Tests were completed once on these exact source SHAs before preparation.
    test_receipt=BASE/'runs/M383-adapter-tests-01/RESULT.json'
    tested=json.loads(test_receipt.read_text(encoding='utf-8'));assert tested['tests']==8 and tested['return_code']==0
    for n,d in tested['source_sha256'].items():assert sha(HERE/n)==d
    manifest=json.loads((OLD/'PACKAGE_MANIFEST.json').read_text(encoding='utf-8'))
    for r in manifest['files']:assert sha(OLD/r['path'])==r['sha256']
    PKG.mkdir(parents=True)
    excluded={'m382_assemble.py','m382_load_slot_gate.py','m382_export_result.py','run_m382_load_slot.sh','SHA256SUMS'}
    for r in manifest['files']:
        if r['path'] not in excluded:shutil.copyfile(OLD/r['path'],PKG/r['path'])
    for n in ('ps_read_ahead.py','m383_sealed_ps_read.py'):shutil.copyfile(HERE/n,PKG/n)
    source=(TEMPLATE/'m378_staged_layer_gate.py').read_text(encoding='utf-8').replace('M378','M383').replace('m378_export_result','m383_export_result').replace('/home/ubuntu/m378_gate_up_layer_01','/home/ubuntu/m383_ps_descriptor_01').replace('--enable-staged-layer','--enable-ps-descriptor').replace('args.enable_staged_layer','args.enable_ps_descriptor').replace('independent-single-layer-capacity-diagnostic','sealed-DMA-PS-single-descriptor-numerical')
    source=once(source,'from m365_stage_policy import StagePolicy,SHAPES','from m365_stage_policy import StagePolicy,SHAPES\nfrom m383_sealed_ps_read import SealedPSReadSession\nfrom ps_read_ahead import RetainedPSResourcesError\nfrom m382_ps_slot import RetainedSlotError\nfrom m370_patch_scope import PatchScope\nimport weakref')
    source=once(source,"BLOCKED_BOARD_METHODS = ('lm_head',)","BLOCKED_BOARD_METHODS = ('_execute','language_family_many','language_family','lm_head')")
    source=once(source,'allocations = []; restorations = []; slots = []','allocations = []; registry = PatchScope(); slots = []; ps_session = None')
    source=once(source,'        original = getattr(obj,name); restorations.append((obj,name,original)); setattr(obj,name,replacement)\n        return original','        return registry.patch(obj,name,replacement)')
    source=once(source,"for name in ('prefill','decode'):","for name in ('prefill','decode','_family'):")
    source=once(source,"        result['family_pair_prerequisite_sha256']=sha256(family_path)","        result['family_pair_prerequisite_sha256']=sha256(family_path)\n        slot_path=Path('/home/ubuntu/m382_sealed_ps_slot_01/B1/load-memory.json')\n        slot=json.loads(slot_path.read_text(encoding='utf-8'))\n        if sha256(slot_path)!='"+SLOT_RAW+"' or slot['status']!='PASS_M382_SEALED_LOAD_ONLY_PS_SLOT' or not slot['ps_slot']['release']['all_owner_weakrefs_dead']:raise RuntimeError('Actual prior PS slot proof differs')\n        result['slot_prerequisite_sha256']=sha256(slot_path)")
    source=once(source,"            result['allocated_buffers'].append(row)","            if row['address']+row['bytes']>base.LOW_END:raise RuntimeError('Original DMA outside low DDR ABI')\n            result['allocated_buffers'].append(row)")
    source=once(source,'        from m343_layer_scope import bind\n','')
    a=source.index("        for name in ('_launch_prepacked','_launch_once'):")
    b=source.index("        result['boot_unchanged']",a)
    source=source[:a]+'''        # Allocation source used by the constructor is also sealed explicitly.
        patch(pynq,'allocate',forbid('extra-DMA.pynq.allocate',blocked))
        patch(runtime,'allocate',forbid('extra-DMA.runtime.allocate',blocked))
        def resident():
            return (initialized and not runtime._m365_closed and engine.board is runtime
                and engine.language is not None and engine.vision is not None and engine.tokenizer is not None
                and len(allocations)==7 and not result['released_buffers'] and not blocked
                and [int(x.nbytes) for x in allocations]==SHAPES and policy.safe()
                and runtime.host_calls==runtime.logical_calls==0)
        spec=json.loads((CANDIDATE/'BOARD_CASES.json').read_text(encoding='utf-8'))
        chain=spec['single_descriptor_chain'];layout=runtime.language_layout
        words,size=base.chain_window(layout,chain)
        values=((np.arange(32*chain['groups']*64,dtype=np.int32)%31-15).astype(np.float32)*np.float32(.002)).reshape(32,chain['groups']*64)
        packet=(CANDIDATE/'descriptor_packet.bin').read_bytes();golden=(CANDIDATE/'descriptor_golden.bin').read_bytes()
        if chain['descriptor_count']!=1 or words!=0 or size!=368640 or len(packet)!=102416 or len(golden)!=262144:raise RuntimeError('Frozen original single-descriptor geometry differs')
        if base.pack_chain_input(chain,values,words,activation_scale_shift=0)!=packet:raise RuntimeError('Original pack or activation changed')
        def weight_hashes():
            return [hashlib.sha256(memoryview(x)[:size]).hexdigest() for x in runtime.staged_buffers]
        def transact(label):
            if not resident():raise RuntimeError('Sealed runtime not safe before submit')
            policy.capture('before-physical-'+label,True)
            runtime.input_buffer[:len(packet)]=np.frombuffer(packet,np.uint8);runtime.input_buffer.sync_to_device()
            runtime.output_buffer[:len(golden)]=0xa5;runtime.output_buffer.sync_to_device()
            for reg,buffer in zip(base.REG_POINTERS,runtime.staged_buffers):base.write_u64(runtime.kernel,reg,base.physical_address(buffer))
            runtime.kernel.write(base.REG_CONFIG,int(chain['config_u32'],16))
            result.setdefault('transactions',[]).append(dict(label=label,chain_index=chain['chain_index'],descriptor_count=1,input_bytes=len(packet),output_bytes=len(golden)))
            policy.active=policy.ever=True;policy.completed=False
            runtime.dma.recvchannel.transfer(runtime.output_buffer,nbytes=len(golden))
            runtime.kernel.write(base.REG_AP_CTRL,1)
            runtime.dma.sendchannel.transfer(runtime.input_buffer,nbytes=len(packet))
            completed=base.wait_transaction(runtime.kernel,runtime.dma,10)
            if not safe_to_release(completed) or completed['ap_return']!=policy.build:raise RuntimeError('Descriptor completion unsafe')
            policy.active=False;policy.completed=True
            runtime.output_buffer.sync_from_device()
            output=bytes(memoryview(runtime.output_buffer)[:len(golden)])
            if output!=golden:raise RuntimeError('Full descriptor output differs from frozen FTZ reference')
            policy.capture('after-physical-'+label,True)
            return dict(label=label,packet_sha256=hashlib.sha256(packet).hexdigest(),weight_sha256=weight_hashes(),output_sha256=hashlib.sha256(output).hexdigest(),output_bytes=len(output),full_output_exact=True,snapshot=completed)
        policy.begin_sampling()
        # One same-hardware baseline then the PS staging candidate; this is a
        # numerical pair, never a speed comparison or full-model attempt.
        before_bytes=runtime.stage_bytes
        runtime._stage(layout,chain)
        result['baseline_descriptor']=transact('original-single-descriptor')
        ps_session=SealedPSReadSession(runtime,base,[(layout,chain)],enabled=True,policy=policy,resident=resident,completed_transaction_snapshot=base.transaction_snapshot(runtime.kernel,runtime.dma))
        session_ref=weakref.ref(ps_session)
        with ps_session:
            runtime._stage(layout,chain)
            ps_session._memory()
            result['candidate_descriptor']=transact('PS-single-descriptor')
            ps_session._memory()
        result['ps_session']=ps_session.report()
        ps_session=None
        if session_ref() is not None:raise RetainedPSResourcesError('Closed session still held after report; retain runtime')
        result['session_weakref_dead']=True
        if any(result['baseline_descriptor'][k]!=result['candidate_descriptor'][k] for k in ('packet_sha256','weight_sha256','output_sha256','output_bytes','full_output_exact')):raise RuntimeError('Candidate packet/weights/full wire output differs')
        if runtime.stage_bytes-before_bytes!=8*size:raise RuntimeError('One original plus one candidate stage byte accounting differs')
        result['stage_pair_bytes']=runtime.stage_bytes-before_bytes
        result['original_parser_workers']=1
        result['model_forward_calls']=0
        result['extra_pynq_allocations']=len(allocations)-7
        result['ps_prefetch_enabled']=True
        result['worker_started']=True
        result['numerical_pass']=True
        result['status']='PASS_M383_PS_DESCRIPTOR_NUMERICAL'
        result['memory_capacity_proven']=False
        policy.stop_sampling()
'''+source[b:]
    source=once(source,'    except CapacityRejected as exc:',"    except (RetainedPSResourcesError,RetainedSlotError) as exc:\n        unsafe=True;result['errors'].append(type(exc).__name__+': '+str(exc));result['traceback']=traceback.format_exc()\n    except CapacityRejected as exc:")
    source=once(source,'        # Keep guards installed until all resource cleanup is finished.','        # Keep guards installed until all resource cleanup is finished.\n        unsafe=unsafe or ps_session is not None')
    source=once(source,'            for obj,name,original in reversed(restorations): setattr(obj,name,original)',"            registry.restore_all(completion_proven=True,release_proven=True)\n            result['patch_registry_cleared']=not registry.entries")
    source=source.replace('PASS_M383_SINGLE_LAYER_DIAGNOSTIC','PASS_M383_PS_DESCRIPTOR_NUMERICAL').replace('Original complete runtime and one layer retained; gate_up two parser workers only; no extra CMA/PS slot; production policy unchanged','Complete runtime/seven DMA; original baseline and isolated one-slot PS staging single descriptor; no model/vision, original pack and full wire golden').replace('Independent layer adjudication then separately freeze fixed-text admission; no full-model/video/performance unlocked automatically','Single-descriptor numerical/lifecycle adjudication and three-record synchronization; only then prepare representative chain; stop expansion on capacity/lifecycle issue')
    assert 'GateUpWorkers' not in source and 'one_layer' not in source
    atomic(PKG/'m383_ps_descriptor_gate.py',source.encode('utf-8'))
    assembly=(OLD/'m382_assemble.py').read_text(encoding='utf-8').replace('M382','M383').replace('/home/ubuntu/m378_gate_up_layer_candidate_01','/home/ubuntu/m382_sealed_ps_slot_candidate_01').replace(sha(TEMPLATE/'PACKAGE_MANIFEST.json'),sha(OLD/'PACKAGE_MANIFEST.json'))
    atomic(PKG/'m383_assemble.py',assembly.encode('utf-8'))
    exporter=(OLD/'m382_export_result.py').read_text(encoding='utf-8').replace('M382','M383').replace('/home/ubuntu/m382_sealed_ps_slot_01','/home/ubuntu/m383_ps_descriptor_01').replace('sealed-DMA-load-only-PS-slot-diagnostic','sealed-DMA-PS-single-descriptor-numerical')
    atomic(PKG/'m383_export_result.py',exporter.encode('utf-8'))
    runner=(OLD/'run_m382_load_slot.sh').read_text(encoding='utf-8').replace('M382','M383').replace('m382_export_result','m383_export_result').replace('m382_load_slot_gate','m383_ps_descriptor_gate').replace('/home/ubuntu/m382_sealed_ps_slot_01','/home/ubuntu/m383_ps_descriptor_01').replace('ENABLE_LOAD_ONLY_SLOT','ENABLE_PS_DESCRIPTOR').replace('--enable-load-only-slot','--enable-ps-descriptor')
    atomic(PKG/'run_m383_ps_descriptor.sh',runner.encode('utf-8'))
    closure=json.loads((PKG/'SOURCE_CLOSURE.json').read_text(encoding='utf-8'));trees={p.stem:ast.parse(p.read_text(encoding='utf-8'),feature_version=(3,10)) for p in PKG.glob('*.py')};allowed=set(sys.stdlib_module_names)|set(closure['modules'])|{'numpy','pynq','tokenizers'};missing=[]
    for mod,tree in trees.items():
        for node in ast.walk(tree):
            names=[n.name.split('.')[0] for n in node.names] if isinstance(node,ast.Import) else ([(node.module or '').split('.')[0]] if isinstance(node,ast.ImportFrom) else [])
            missing.extend((mod,n) for n in names if n and n not in trees and n not in allowed)
    assert not missing,missing
    symbols=next(t for t in symtable.symtable(source,'gate','exec').get_children() if t.get_name()=='main');assert next(t for t in symbols.get_children() if t.get_name()=='tracked_allocate').lookup('SHAPES').is_global()
    for row in json.loads((PKG/'HARDWARE_CLOSURE.json').read_text(encoding='utf-8'))['prerequisites']:assert sha(ROOT/row['path'])==row['sha256']
    rows=[dict(path=p.name,bytes=p.stat().st_size,sha256=sha(p)) for p in sorted(PKG.iterdir())]
    atomic(PKG/'SHA256SUMS',''.join(r['sha256']+'  '+r['path']+'\n' for r in rows).encode('ascii'));rows.append(dict(path='SHA256SUMS',bytes=(PKG/'SHA256SUMS').stat().st_size,sha256=sha(PKG/'SHA256SUMS')))
    atomic(PKG/'PACKAGE_MANIFEST.json',encoded(dict(schema='m383-sealed-PS-descriptor-v1',files=rows,file_count=len(rows),total_bytes=sum(r['bytes'] for r in rows))))
    out=BASE/'runs/M383-ps-descriptor-preparation-01';r=dict(status='PASS_OFFLINE_SEALED_PS_DESCRIPTOR_PREPARATION',slot_closure_sha256=prior['sha256'],slot_raw_sha256=SLOT_RAW,manifest_sha256=sha(PKG/'PACKAGE_MANIFEST.json'),original_PS_source_sha256=ORIGINAL_PS,adapter_tests_sha256=sha(test_receipt),tests=8,recursive_missing=missing,python310_syntax=True,source_scope_callback_checked=True,package_files=len(rows),package_bytes=sum(r['bytes'] for r in rows),production64MiB_unchanged=True,additional_dma_calls=0,planned_transactions=3,model_forward_calls=0,board_run=False,numerical_pass=False,performance_pass=False)
    atomic(out/'RESULT.json',encoded(r),immutable=True);digest=sha(out/'RESULT.json')
    sync('latest_m383_ps_descriptor_preparation',dict(status=r['status'],result=(out/'RESULT.json').relative_to(ROOT).as_posix(),sha256=digest,manifest_sha256=r['manifest_sha256']),f'## M383 独立PS预读单descriptor准备（2026-10-03）\n\nM382 slot闭合SHA {prior["sha256"]}同步后才冻结。复用原PS源SHA {ORIGINAL_PS}，只独立诊断适配实际内存准入及sole-owner释放；原64MiB/生产源保持。原同Overlay合法最小＋同核原暂存/PS暂存单descriptor完整wire golden与权重字节，0模型forward/新增DMA，原单parser。8项新适配检查＋依赖missing0/3.10/作用域通过，准备 SHA {digest}。尚未上传/新数值；下一步实际编排/回收支持后只一次本级。')
    print('M383_PREPARED',digest,r['manifest_sha256'])
if __name__=='__main__':main()
