"""Actual visual-forward + three checkpoint Decode states on borrowed runtime."""
import hashlib
import inspect
import json
from pathlib import Path
import time
import numpy as np
from measurement import sha256,write_json


def verify_imports():
    from m222_vectorized_w4_runtime import M222PSVisionRuntime
    from decode_io_trace import process_snapshot
    from video_contract_v2 import preprocess_raw_frames
    from sys_video_input import decode_raw_video
    import cv2
    owner=next(c for c in M222PSVisionRuntime.__mro__ if 'close' in c.__dict__)
    path=Path(inspect.getfile(owner))
    return dict(close_owner=owner.__name__,close_source=str(path),close_source_sha256=sha256(path),
        close_body=inspect.getsource(owner.close),cv2_version=cv2.__version__,
        io_available='read_bytes' in process_snapshot())


def run_experiment(model,board,base,root,config,plan,output):
    import torch
    from m222_vectorized_w4_runtime import M222PSVisionRuntime
    from decode_checkpoint import load_checkpoint
    from video_language_runtime import KVCache
    from decode_diagnostic import DecodeDiagnostic
    from decode_io_trace import DecodeIOTrace,process_snapshot
    from sys_video_input import decode_raw_video
    from video_contract_v2 import preprocess_raw_frames
    from lifecycle_trial import run_trial
    from lifecycle_reads import prepare_reads
    from memory_lifecycle import memory_snapshot
    from summarize_decode_trace import summarize
    torch.set_num_threads(4)
    here=Path(__file__).resolve().parent
    reads=json.loads((here/'lifecycle_read_plan.json').read_text())
    holder=[];results=[]
    result=dict(status='FAIL',scope='A/B/C lifecycle diagnosis, not performance acceptance',
        records=results,imports=verify_imports(),timing_eligible=False)
    def save_record(record):
        results.append(record)
        write_json(output.with_name(output.stem+'_partial.json'),result)
        print('LIFECYCLE_STATE_DONE '+record['state'],flush=True)
    try:
        package=root/'m181_m120_video_board_candidate'
        holder.append(M222PSVisionRuntime(package/'ps_vision_payload',package/'vision_layout',
            package/'auxiliary/M90_VISION_RAW_AUX_MANIFEST.json'))
        frames,evidence=decode_raw_video(root/'optimization_v1/OP00-import-decode-01/dev-0001.mp4',config['video_sha256'])
        prepared=preprocess_raw_frames(frames,evidence['selected_frame_indices'])
        start=time.perf_counter()
        visual=holder[0](**prepared)
        result['vision_s']=time.perf_counter()-start
        observed=hashlib.sha256(np.asarray(visual,dtype='<f4').tobytes()).hexdigest()
        result['visual_sha256']=observed
        if observed!='b9c476bb5945f66a1046cc4c113a742a723173b2d21e279dcb44878f77e4b53f':
            raise RuntimeError('Visual output differs from frozen SYS05; do not proceed')
        result['memory_after_vision']=memory_snapshot()
        # Keep the same small visual/preprocessed arrays in all three states.
        def restore():
            return load_checkpoint(root/'optimization_v1/decode_checkpoints/SYS05-prefill',
                plan['checkpoint_manifest_sha256'],plan['identity'],KVCache)
        def decode(token,cache):
            before=board.logical_calls;physical=board.host_calls;retries=board.scale_retry_count
            diagnostic=DecodeDiagnostic(model,board,base,trace_factory=DecodeIOTrace)
            start=time.perf_counter_ns()
            output_token,logits=diagnostic.decode(token,cache)
            ready_s=(time.perf_counter_ns()-start)/1e9
            detail=diagnostic.finalize()
            detail['token_ready_s']=ready_s
            detail['attribution']=summarize(detail['steps'][0])
            if (board.logical_calls-before!=162 or board.host_calls-physical!=162 or
                board.scale_retry_count!=retries or any(a.shape!=(853,8,128) for a in cache.keys+cache.values)):
                raise RuntimeError('Single Decode plan or KV geometry changed')
            return output_token,logits,detail
        outcome=run_trial(vision_holder=holder,restore=restore,
            prepare_reads=lambda:prepare_reads(reads,snapshot=process_snapshot,
                progress=lambda s:print(s,flush=True)),decode=decode,on_record=save_record)
        result.update(status=outcome['status'],caveat=outcome['caveat'],numerical_scope='Full logits identical across states only')
    except Exception as exc:
        result['error']=repr(exc)
        raise
    finally:
        if holder:
            holder[0].close();holder.clear()
        write_json(output.with_name(output.stem+'_lifecycle.json'),result)
    return result
