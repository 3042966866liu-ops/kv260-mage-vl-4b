"""Original M276 requests with light timing; exact hashes only after completion."""
import hashlib
import json
from pathlib import Path
import threading
import time
from types import SimpleNamespace
import numpy as np
import weakref
import sys
from m393_silu_scope import SiluLayerScope,RetainedSiluOwnerError
from m368_stage_policy import FAMILIES,SHAPES
from board_safety import safe_to_release
from measurement import sha256
from frozen_video_identity import FRAMES,STACK_SHA,ADDON
from m368_video_contract import tensor,check_call_contract,validate_stream

ORDER='ABBABAAB'


def io_snapshot():
    return {k:int(v.strip()) for k,v in (line.split(':',1) for line in Path('/proc/self/io').read_text(encoding='utf-8').splitlines())}


def minimal(runtime,policy,base,candidate):
    packet=(candidate/'build_packet.bin').read_bytes();golden=(candidate/'build_golden.bin').read_bytes()
    if len(packet)!=2576 or len(golden)!=4096:raise RuntimeError('Minimal fixture size differs')
    for buffer in runtime.staged_buffers:buffer[:144]=0;buffer.sync_to_device()
    runtime.input_buffer[:len(packet)]=np.frombuffer(packet,np.uint8);runtime.input_buffer.sync_to_device()
    runtime.output_buffer[:len(golden)]=0xa5;runtime.output_buffer.sync_to_device()
    for reg,buffer in zip(base.REG_POINTERS,runtime.staged_buffers):base.write_u64(runtime.kernel,reg,base.physical_address(buffer))
    runtime.kernel.write(base.REG_CONFIG,0x10201);policy.capture('before-same-overlay-legal-minimal',True)
    policy.active=policy.ever=True;policy.completed=False
    runtime.dma.recvchannel.transfer(runtime.output_buffer,nbytes=len(golden));runtime.kernel.write(base.REG_AP_CTRL,1)
    runtime.dma.sendchannel.transfer(runtime.input_buffer,nbytes=len(packet));s=base.wait_transaction(runtime.kernel,runtime.dma,10.0)
    if not safe_to_release(s) or s['ap_return']!=policy.build:raise RuntimeError('Minimal physical completion unproven')
    policy.active=False;policy.completed=True;runtime.output_buffer.sync_from_device()
    if bytes(memoryview(runtime.output_buffer)[:len(golden)])!=golden:raise RuntimeError('Minimal full output differs')
    runtime._programmed_weight_addresses=runtime._programmed_config=None
    policy.capture('after-same-overlay-legal-minimal',True)
    return dict(snapshot=s,output_bytes=len(golden),full_output_exact=True)


def run_trials(engine,runtime,policy,base,candidate,here,result,new_board,patch,restore_trial):
    import m276_video_runtime as video
    from m366_head_observer import bind as bind_head
    expected=json.loads((here/'VIDEO_EXPECTED.json').read_text(encoding='utf-8'))['baseline']
    visual_ref=json.loads((here/'VISUAL_EXPECTED.json').read_text(encoding='utf-8'))
    frames=[]
    for name,digest in FRAMES.items():
        file=ADDON/'fixtures'/name
        if sha256(file)!=digest:raise RuntimeError('Frame file identity differs')
        frames.append(np.load(file,allow_pickle=False))
    frames=np.ascontiguousarray(np.stack(frames))
    if frames.shape!=(4,448,448,3) or frames.dtype!=np.uint8 or hashlib.sha256(frames.tobytes()).hexdigest()!=STACK_SHA:raise RuntimeError('Ordered frames differ')
    request=SimpleNamespace(prompt=video.M276_KNIFE_PROMPT,max_new_tokens=1,frames_rgb_u8=frames)
    result['frames_sha256']=STACK_SHA;result['order']=ORDER;result['samples']=[]
    # Establish the original PS code cache once; no untimed PL model request.
    policy.capture('before-PS-visual-cache-preparation',True)
    tensors=video.preprocess(np.ascontiguousarray(frames[-1:]))
    visual=engine.vision(tensors['pixel_values'],tensors['image_grid_thw'],tensors['patch_positions'])
    if tensor(visual)!=visual_ref['visual_features']:raise RuntimeError('PS cache preparation visual differs')
    if {k:tensor(v) for k,v in sorted(tensors.items())}!=visual_ref['preprocessed']:raise RuntimeError('PS preparation tensors differ')
    result['cache_preparation']=engine.vision.decoder_evidence()
    if result['cache_preparation']['cache_entries']!=26 or result['cache_preparation']['cache_bytes']!=66699264:raise RuntimeError('Original cache preparation differs')
    del visual,tensors
    captured={};stage_ms={};original_prefill=engine.language.prefill;original_preprocess=video.preprocess;vision_call=engine.vision.__class__.__call__
    def timed_preprocess(*a,**kw):
        started=time.perf_counter();answer=original_preprocess(*a,**kw);stage_ms['preprocess']=(time.perf_counter()-started)*1000
        captured['preprocessed']=answer;return answer
    def timed_vision(self,*a,**kw):
        started=time.perf_counter();answer=vision_call(self,*a,**kw);stage_ms['vision']=(time.perf_counter()-started)*1000
        captured['visual']=answer;return answer
    silu_scope=None;variant=None
    def resident():
        return (not runtime._m368_closed and engine.board is runtime and engine.language.runtime is runtime
            and engine.language is not None and engine.vision is not None and engine.tokenizer is not None
            and not result['released_buffers'] and not result['blocked_inference_attempts']
            and [r['bytes'] for r in result['allocated_buffers']]==SHAPES and policy.safe())
    def timed_prefill(hidden):
        nonlocal silu_scope
        result['model_forward_calls']=result.get('model_forward_calls',0)+1
        captured['input']=hidden;started=time.perf_counter()
        if variant=='B':
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
        stage_ms['prefill']=(time.perf_counter()-started)*1000
        captured['output']=answer;return answer
    patch(video,'preprocess',timed_preprocess);patch(engine.vision.__class__,'__call__',timed_vision);patch(engine.language,'prefill',timed_prefill)
    for index,variant in enumerate(ORDER):
        init_started=time.monotonic()
        if index:runtime,policy=new_board(variant,index)
        build=0x4d333537
        if policy.build!=build:raise RuntimeError('Trial order/build differs')
        engine.board=runtime;engine.language.runtime=runtime
        policy.baseline_rss=policy.snapshot()['process_bytes']['VmRSS']
        policy.capture('performance-admission-with-original-warm-code-cache',True)
        min_proof=minimal(runtime,policy,base,candidate)
        for name in ('_launch_prepacked','_launch_once'):patch(runtime,name,policy.wrap_launch(getattr(runtime,name),name))
        observed_head,head_proof=bind_head(runtime._execute,policy,runtime.head_contract.chains)
        if head_proof.get('original_module')!='m230_prefill_runtime' or head_proof.get('original_function')!='M230PrefillRuntime._execute' or not head_proof.get('removed_observation_calls_ast_equals_original'):raise RuntimeError('Actual head executor observer identity differs')
        patch(runtime,'_execute',observed_head)
        head=runtime.lm_head
        def timed_head(*a,_original=head,**kw):
            started=time.perf_counter();answer=_original(*a,**kw);stage_ms['head']=(time.perf_counter()-started)*1000
            return answer
        patch(runtime,'lm_head',timed_head)
        def forbid_extra(*a,**kw):
            result['blocked_inference_attempts'].append('extra-DMA.runtime.allocate')
            raise RuntimeError('Original7DMA sealed during request')
        patch(runtime,'allocate',forbid_extra)
        # Public PYNQ allocator remains the original tracked allocator, rejecting
        # index>=7; the captured runtime allocator is sealed separately.
        # Candidate source pinning/binding, workspace allocation and safe close
        # remain inside original request/Prefill timers, including all overhead.
        captured.clear();stage_ms.clear()
        # All input SHA and package checks above are outside original request timers.
        old_gqa=engine.language.grouped_attention_calls;before_memory=policy.capture('before-timed-request',True)
        before_io=io_snapshot();before_cache=engine.vision.decoder_evidence();events=[]
        initialization_ms=(time.monotonic()-init_started)*1000
        policy.stop_event=threading.Event();policy.stop_reason=None;policy.sample_count=0;policy.extrema=None;policy.begin_sampling()
        print(f'M395_REQUEST_BEGIN sample={index+1} variant={variant}',flush=True)
        for event,payload in engine.stream(request):events.append((event,payload))
        parser_report=dict(parse_workers=1,original_single_worker_dispatch=True,bindings_restored=True,extra_dma_allocations=0)
        if result.get('retained_SiLU_scope') or silu_scope is not None:raise RetainedSiluOwnerError('SiLU lifecycle incomplete before DMA release')
        if any(t.name.startswith(('m238-parse','m238-pack')) for t in threading.enumerate()):raise RuntimeError('Worker retained after request')
        # Original complete first_token_ms/total_ms have stopped before all following work.
        after_memory=policy.capture('after-timed-request',True);policy.stop_sampling();after_io=io_snapshot()
        semantic=validate_stream(events,engine.vision.decoder_evidence(),f'0x{build:08X}')
        semantic['proof']['build_id']=expected['semantic']['proof']['build_id']
        if semantic!=expected['semantic']:raise RuntimeError('Trial final decision/proof differs')
        token,logits,kv=captured['output']
        numerics=dict(input=tensor(captured['input']),visual=tensor(captured['visual']),preprocessed={k:tensor(v) for k,v in sorted(captured['preprocessed'].items())},token=token,logits=tensor(logits),keys=[tensor(v) for v in kv.keys],values=[tensor(v) for v in kv.values])
        if any(numerics[k]!=expected[k] for k in ('input','token','logits','keys','values')) or numerics['visual']!=visual_ref['visual_features'] or numerics['preprocessed']!=visual_ref['preprocessed']:raise RuntimeError('Post-timer exact visual/input/logits/KV differs')
        e=runtime.evidence()
        row={key:e[source] for key,source in [('logical_calls','logical_calls'),('host_calls','host_calls'),('retry_count','scale_retry_count'),('retry_launches','pipeline_retry_launches'),('nonfinite_detections','fused_nonfinite_detections'),('scale_attempts','scale_attempts'),('stage_bytes','stage_bytes'),('logical_expected_macros','logical_expected_macros'),('expected_macros','expected_macros')]}
        check_call_contract(row,expected['logical_expected_macros'])
        if any(row[k]!=expected[k] for k in row) or engine.language.grouped_attention_calls-old_gqa!=36:raise RuntimeError('Trial transaction/retry/weight bytes differ')
        transactions=policy.result.get('transactions',[])
        if len(transactions)!=row['host_calls'] or len([t for t in transactions if t['method']=='head-original-execute'])!=8:raise RuntimeError('Physical transaction coverage differs')
        snapshot=base.transaction_snapshot(runtime.kernel,runtime.dma)
        if not policy.safe() or not safe_to_release(snapshot) or snapshot['ap_return']!=build:raise RuntimeError('Trial exit state unsafe')
        final=next(p for event,p in events if event=='complete')
        sample=dict(index=index+1,variant=variant,build_id=f'0x{build:08X}',timing=dict(first_token_ms=final['first_token_ms'],total_ms=final['total_ms'],stages_ms=dict(stage_ms),initialization_ms=initialization_ms),numeric_sha_after_timer=numerics,semantic=semantic,counts={k:v for k,v in row.items() if k!='scale_attempts'},scale_attempts_sha_after_timer=hashlib.sha256(json.dumps(row['scale_attempts'],sort_keys=True,separators=(',',':')).encode()).hexdigest(),retry_records=[a for a in row['scale_attempts'] if len(a['attempted_shifts'])>1],same_overlay_minimal_proof=min_proof,head_observer_proof=head_proof,final_snapshot=snapshot,before_memory=before_memory,after_memory=after_memory,sampled_memory=dict(policy.result['sampled_memory']),before_cache=before_cache,after_cache=engine.vision.decoder_evidence(),io_delta={k:after_io[k]-before_io[k] for k in before_io},allocated_buffers=list(result['allocated_buffers']))
        if sample['timing']['total_ms']<=0 or not all(v>=0 for v in stage_ms.values()):raise RuntimeError('Invalid timing')
        # Native timing overhead and post-request validation are not called inference acceleration.
        runtime.close()
        if result['released_buffers']!=list(reversed(result['allocated_buffers'])):raise RuntimeError('Trial original7 reverse release differs')
        sample['released_buffers']=list(result['released_buffers']);sample['safe_buffers_released']=True
        sample['parser_scope']=parser_report
        sample['silu_scope']=captured['silu_report']
        sample['restored_owner_patch_count']=restore_trial(runtime,policy)
        sample['owner_registry_cleared']=True
        result['samples'].append(sample);result['last_transaction']=transactions[-1] if transactions else None
        print(f'M395_REQUEST_COMPLETE sample={index+1} variant={variant} total_ms={final["total_ms"]:.3f} first_token_ms={final["first_token_ms"]:.3f}',flush=True)
        captured.clear();policy.result['transactions']=[]
        # Do not retain previous full logits/KV arrays during the next construction.
        del logits,kv,events,e,row,transactions,head,observed_head,timed_head
    result['numerical_pass']=True;result['all8_requests_completed']=True
    result['fpga_transactions_total']=sum(1+s['counts']['host_calls'] for s in result['samples'])
    result['measurement_scope']='Preloaded original request, original timers, warm original PS code cache; initialization and all SHA validation outside request'
    result['performance_measurements_collected']=True
    result['ps_prefetch_enabled']=False
    result['silu_workspace_enabled']='B only'
    result['comparison']='Same parallel hardware and original one parser: A original expression / B SiLU workspace'
    result['historical_hardware_40_81_percent_result_unchanged']=True
