"""Create isolated phase diagnostics from frozen load observers; no production edits."""
import ast
import hashlib
import json
import shutil
import m351_workflow as w
from m358_prepare_capacity import replace_once
from m343_layer_scope import derive

PKG=w.BASE/'candidates/M365-staged-layer-03'

LAYER_CODE='''
        import numpy as np
        from m343_layer_scope import bind
        from m365_stage_policy import FAMILIES
        from board_safety import safe_to_release
        policy.seal(allocations,int(TARGET_BUILD,16))
        result['production_threshold_would_admit']=result['loaded_capacity']['meets_threshold']
        result['diagnostic_admitted']=True
        result['additional_cma_requests_allowed']=False
        result['diagnostic_ps_growth_limit_bytes']=256<<20
        result['diagnostic_ps_available_margin_bytes']=64<<20
        if runtime.host_calls or runtime.logical_calls: raise RuntimeError('Unexpected prior transaction')
        # Bootstrap completes one legal transaction on this very Overlay.
        packet=(CANDIDATE/'build_packet.bin').read_bytes()
        golden=(CANDIDATE/'build_golden.bin').read_bytes()
        if len(packet)!=2576 or len(golden)!=4096: raise RuntimeError('Minimal fixture size differs')
        for buffer in runtime.staged_buffers: buffer[:144]=0;buffer.sync_to_device()
        runtime.input_buffer[:len(packet)]=np.frombuffer(packet,np.uint8);runtime.input_buffer.sync_to_device()
        runtime.output_buffer[:len(golden)]=0xa5;runtime.output_buffer.sync_to_device()
        for reg,buffer in zip(base.REG_POINTERS,runtime.staged_buffers):base.write_u64(runtime.kernel,reg,base.physical_address(buffer))
        runtime.kernel.write(base.REG_CONFIG,0x10201)
        policy.capture('before-same-overlay-legal-minimal',True)
        policy.active=policy.ever=True;policy.completed=False
        result['fpga_transactions']=1
        runtime.dma.recvchannel.transfer(runtime.output_buffer,nbytes=len(golden))
        runtime.kernel.write(base.REG_AP_CTRL,1)
        runtime.dma.sendchannel.transfer(runtime.input_buffer,nbytes=len(packet))
        minimal=base.wait_transaction(runtime.kernel,runtime.dma,10.0)
        if not safe_to_release(minimal) or minimal['ap_return']!=policy.build:raise RuntimeError('Minimal transaction completion unsafe')
        policy.active=False;policy.completed=True
        runtime.output_buffer.sync_from_device()
        if bytes(memoryview(runtime.output_buffer)[:len(golden)])!=golden:raise RuntimeError('Minimal full output differs')
        runtime._programmed_weight_addresses=None;runtime._programmed_config=None
        result['same_overlay_minimal_proof']=dict(snapshot=minimal,output_bytes=len(golden),full_output_exact=True)
        policy.capture('after-same-overlay-legal-minimal',True)
        for name in ('_launch_prepacked','_launch_once'):
            setattr(runtime,name,policy.wrap_launch(getattr(runtime,name),name))
        expected=json.loads((HERE/'LAYER_EXPECTED.json').read_text(encoding='utf-8'))
        contract=expected['input_contract']
        with np.load(STABLE/'auxiliary/m77_text_aux_fp16.npz',allow_pickle=False) as archive:
            selected_rows=np.asarray(archive['model.language_model.embed_tokens.weight'],np.float32)
        hidden=np.tile(np.stack([selected_rows[contract['selected_embedding_ids'].index(t)] for t in contract['prompt_token_ids']]),(6,1))[:159].copy()
        def tensor(value):
            value=np.ascontiguousarray(value)
            if not np.isfinite(value).all():raise FloatingPointError('Nonfinite diagnostic output')
            return dict(shape=list(value.shape),dtype=str(value.dtype),bytes=int(value.nbytes),sha256=hashlib.sha256(value.tobytes()).hexdigest())
        if tensor(hidden)!=contract['input_tensor']:raise RuntimeError('Original layer input differs')
        one_layer=bind(sys.modules['m241_video_language_runtime'],(HERE/'frozen_one_layer.py').read_text(encoding='utf-8'))
        model=engine.language;families=[];original_family=model._family
        def observed_family(layer,name,values):
            if layer!=0 or len(families)>=5 or name!=FAMILIES[len(families)]:raise RuntimeError('Layer0 family sequence escaped')
            print('M365_FAMILY '+name,flush=True)
            policy.capture('before-family:'+name,True)
            output=original_family(layer,name,values)
            policy.capture('after-family:'+name,True)
            families.append(dict(family=name,input=tensor(values),output={k:tensor(v) for k,v in sorted(output.items())}))
            return output
        patch(model,'_family',observed_family)
        policy.capture('before-layer0',True);policy.begin_sampling()
        result['model_forward_calls']=1
        output,kv=one_layer(model,hidden.copy())
        policy.capture('after-layer0',True);policy.stop_sampling()
        evidence=runtime.evidence()
        result['layer_result']=dict(families=families,hidden=tensor(output),keys=[tensor(v) for v in kv.keys],values=[tensor(v) for v in kv.values],logical_calls=evidence['logical_calls'],host_calls=evidence['host_calls'],retry_count=evidence['scale_retry_count'],retry_launches=evidence['pipeline_retry_launches'],nonfinite_detections=evidence['fused_nonfinite_detections'],scale_attempts=evidence['scale_attempts'],stage_bytes=evidence['stage_bytes'])
        result['fpga_transactions']=1+len(result['transactions'])
        result['model_forward_calls']=1
        result['diagnostic_scope']='One original layer0 on159 repeated fixed-text embeddings with full runtime objects retained; no visual forward/LM head/full-model/video/performance'
        result['exact_comparison']={key:result['layer_result'][key]==expected['baseline'][key] for key in result['layer_result']}
        if not all(result['exact_comparison'].values()):raise RuntimeError('Frozen stable layer family/hidden/KV/retry reference differs')
        if result['layer_result']['logical_calls']!=25 or len(families)!=5:raise RuntimeError('Incomplete single layer')
        if result['layer_result']['host_calls']!=len(result['transactions']):raise RuntimeError('Physical launch accounting differs')
        result['numerical_pass']=True;result['single_layer_diagnostic_pass']=True
        result['status']='PASS_M365_SINGLE_LAYER_DIAGNOSTIC'
        result['memory_capacity_proven']=False
        result['boot_unchanged']=sha256(boot)==before_boot
        result['cmdline_unchanged']=Path('/proc/cmdline').read_text(encoding='utf-8')==before_cmd
        if not result['boot_unchanged'] or not result['cmdline_unchanged']:raise RuntimeError('Protected identities changed')
'''

def main():
    if PKG.exists():raise RuntimeError('Immutable package exists')
    recovery={}
    for name in ('CURRENT_STATE.md','DEPLOYMENT_OPERATION_MISTAKES_REVIEW.md','docsMILESTONES.md','deployment/mage_vl4b/BOARD_GATE_RESULT.json'):
        path=w.ROOT/name;t=path.read_text(encoding='utf-8-sig');recovery[name]=dict(sha256=w.sha(path),bytes=path.stat().st_size,lines=len(t.splitlines()))
    prior=w.BASE/'runs/M364-memory-questions-closure-01/RESULT.json';assert w.sha(prior)=='020689187348cad23dc421cb2fddbfa7e98e260f772a1301af8769e48c4ebc48'
    old=w.BASE/'candidates/M363-common-load-observer-01'
    text=(old/'m363_load_only_probe.py').read_text(encoding='utf-8')
    substitutions=[
        ('M357 complete runtime capacity only. All inference is blocked.','Independent layer0 capacity diagnostic; production admission unchanged.'),
        ("from ps_slot_capacity import (eligibility, require_capacity, materialize_slot, never_submitted_release, CapacityRejected)","from ps_slot_capacity import CapacityRejected\nfrom m365_stage_policy import StagePolicy,SHAPES"),
        ("BLOCKED_BOARD_METHODS = ('_execute', '_launch_once', '_launch_prepacked', '_stage',\n                         'language_family_many', 'language_family', 'lm_head')","BLOCKED_BOARD_METHODS = ('lm_head',)"),
        ("choices=('A1','B1','B2','A2')","choices=('B1',)"),
        ("--enable-load-only","--enable-staged-layer"),
        ('args.enable_load_only','args.enable_staged_layer'),
        ("Path('/home/ubuntu/m363_load_comparison_01')","Path('/home/ubuntu/m365_staged_layer_02')"),
        ("gate_level='load-only-memory-diagnostic'","gate_level='independent-single-layer-capacity-diagnostic'"),
        ("runtime = engine = base = lock = None","runtime = engine = base = lock = policy = None"),
        ("        mark('after-exact-runtime-imports')","        policy=StagePolicy(result,lambda:runtime,base)\n        mark('after-exact-runtime-imports')"),
        ("            if index>=7: raise RuntimeError('Unexpected extra DMA allocation refused')","            if index>=7: raise RuntimeError('Allocator sealed: extra DMA allocation refused')\n            requested=int(a[0][0]) if a and isinstance(a[0],tuple) and len(a[0])==1 else -1\n            if requested!=SHAPES[index] or kw.get('dtype')!=sys.modules['numpy'].uint8:raise RuntimeError('Original buffer request differs')\n            before=policy.snapshot()['system_bytes']\n            aligned=((requested+4095)//4096)*4096\n            if before['CmaFree']<aligned:raise MemoryError('Diagnostic free-page request precheck refused; not allocator failure')"),
        ("                return never_submitted_release(observed,runtime.host_calls,runtime.logical_calls,result['blocked_inference_attempts'],len(allocations))","                return policy.safe()"),
        ("        patch(pynq,'Overlay',observe_call", "        patch(base,'BUILD_ID',int(TARGET_BUILD,16))\n        patch(pynq,'Overlay',observe_call"),
        ("for name in ('prefill','decode','_family')","for name in ('prefill','decode')"),
        ("            unsafe = not initialized or not never_submitted_release(result.get('final_snapshot',{}),getattr(runtime,'host_calls',-1),getattr(runtime,'logical_calls',-1),result['blocked_inference_attempts'],len(allocations))","            unsafe = unsafe or not initialized or policy is None or not policy.safe()"),
        ("        # Keep guards installed until all resource cleanup is finished.","        # Keep guards installed until all resource cleanup is finished.\n        result['fpga_transactions']=(1 if policy is not None and policy.ever else 0)+len(result.get('transactions',[]))\n        if policy is not None:\n            try:policy.stop_sampling()\n            except BaseException as exc:unsafe=True;result['errors'].append('Observer retained: '+str(exc))"),
        ("result['gate_return_code']=0 if result['status']=='PASS_COMPLETE_RUNTIME_CAPACITY' else 1","result['gate_return_code']=0 if result['status']=='PASS_M365_SINGLE_LAYER_DIAGNOSTIC' else 1"),
        ("result['memory_capacity_proven']=result['gate_return_code']==0","result['memory_capacity_proven']=False"),
        ("fpga_transactions=0,input_bytes=0,output_bytes=0","fpga_transactions=result['fpga_transactions'],last_transaction=result.get('transactions',[])[-1:]"),
        ("Independent load-only adjudication and three-record synchronization; no video/worker/performance unlocked automatically","Independent layer adjudication then separately freeze fixed-text admission; no full-model/video/performance unlocked automatically")]
    for before,after in substitutions:text=replace_once(text,before,after)
    start=text.index("        if len(allocations)!=7 or runtime.maximum_weight_window_bytes!=6963200:")
    end=text.index('    except CapacityRejected as exc:',start)
    text=text[:start]+"        if len(allocations)!=7 or runtime.maximum_weight_window_bytes!=6963200:raise RuntimeError('Seven buffer geometry differs')\n"+LAYER_CODE+text[end:]
    # Delete load-only assertion on closure counters; seal remains after full load.
    text=text.replace('M363','M365').replace('_m363_closed','_m365_closed')
    text=text.replace('from m363_export_result import emit_saved','from m365_export_result import emit_saved')
    text=text.replace('Original complete video runtime with selected stable/M357 bit; no extra CMA/PS slot, GC/trim/forward/worker/PL transaction','Original complete runtime objects retained; independent one-layer diagnostic, no extra CMA/PS slot or vision/LMhead/multi-layer; production policy unchanged')
    ast.parse(text,feature_version=(3,10))
    PKG.mkdir(parents=True)
    exclude={'PACKAGE_MANIFEST.json','SHA256SUMS','m363_assemble.py','m363_load_only_probe.py','m363_export_result.py','run_m363_load_only.sh'}
    for p in old.iterdir():
        if p.name not in exclude:shutil.copyfile(p,PKG/p.name)
    for name in ('m365_stage_policy.py','m343_layer_scope.py','m365_assemble.py'):shutil.copyfile(w.HERE/name,PKG/name)
    w.atomic(PKG/'m365_staged_layer_gate.py',text.encode('utf-8'))
    reference=w.BASE/'runs/M343-single-layer-board-01/BOARD_RESULT.json';ref=json.loads(reference.read_text(encoding='utf-8'))
    assert ref['status']=='PASS' and not ref['unsafe_buffers_retained']
    keys=('families','hidden','keys','values','logical_calls','host_calls','retry_count','retry_launches','nonfinite_detections','scale_attempts','stage_bytes')
    inputpkg=w.BASE/'candidates/M343-single-layer-01'
    input_contract=json.loads((inputpkg/'INPUT_CONTRACT.json').read_text(encoding='utf-8'))
    w.atomic(PKG/'LAYER_EXPECTED.json',w.encoded(dict(prior_reference_raw_sha256=w.sha(reference),input_contract=input_contract,baseline={k:ref['passes'][0][k] for k in keys})))
    closure=json.loads((old/'SOURCE_CLOSURE.json').read_text(encoding='utf-8'))
    release=w.ROOT/'release_staging/kv260-mage-vl-4b-prebuilt-install-20260926-v7'
    source=(release/closure['modules']['m241_video_language_runtime']).read_bytes()
    frozen=derive(source);assert frozen==(inputpkg/'frozen_one_layer.py').read_text(encoding='utf-8')
    w.atomic(PKG/'frozen_one_layer.py',frozen.encode())
    export=(old/'m363_export_result.py').read_text(encoding='utf-8').replace('m363_load_comparison_01','m365_staged_layer_02').replace('load-only-memory-diagnostic','independent-single-layer-capacity-diagnostic').replace('M363','M365')
    w.atomic(PKG/'m365_export_result.py',export.encode())
    runner=(old/'run_m363_load_only.sh').read_text(encoding='utf-8').replace('m363_load_comparison_01','m365_staged_layer_02').replace('m363_load_only_probe.py','m365_staged_layer_gate.py').replace('m363_export_result.py','m365_export_result.py').replace('M363_ENABLE_LOAD_ONLY','M365_ENABLE_STAGED_LAYER').replace('--enable-load-only','--enable-staged-layer').replace('M363','M365')
    runner=runner.replace('$3 =~ ^(A1|B1|B2|A2)$','$3 == B1')
    w.atomic(PKG/'run_m365_staged_layer.sh',runner.encode())
    rows=[dict(path=p.name,bytes=p.stat().st_size,sha256=w.sha(p)) for p in sorted(PKG.iterdir())]
    w.atomic(PKG/'SHA256SUMS',''.join(x['sha256']+'  '+x['path']+'\n' for x in rows).encode())
    rows.append(dict(path='SHA256SUMS',bytes=(PKG/'SHA256SUMS').stat().st_size,sha256=w.sha(PKG/'SHA256SUMS')))
    w.atomic(PKG/'PACKAGE_MANIFEST.json',w.encoded(dict(schema='independent-m365-staged-layer-capacity-v1',files=rows,file_count=len(rows),total_bytes=sum(x['bytes'] for x in rows))))
    out=w.BASE/'runs/M365-staged-layer-preparation-03'
    result=dict(status='DRAFT_STAGED_LAYER_PENDING_POLICY_AND_SUPPORT_VERIFICATION',manifest_sha256=w.sha(PKG/'PACKAGE_MANIFEST.json'),files=len(rows),bytes=sum(x['bytes'] for x in rows),recovery_read=recovery,prior_m364_sha256=w.sha(prior),production_changed=False,production_reserve_unchanged=True,numerical_pass=False,performance_pass=False,board_executed=False)
    w.atomic(out/'RESULT.json',w.encoded(result),immutable=True);print(json.dumps(result))

if __name__=='__main__':main()
