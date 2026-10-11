"""Raw-video SYS measurement adapter; the authorized runner owns hardware lifecycle.

Model/overlay must be loaded before this call. Visual results and KV are never
reused across calls. This module alone cannot grant a numerical/hardware gate.
"""
import hashlib
import numpy as np
from causal_generation import generate, GenerationFailure
from measurement import TokenTrace
from sys_video_input import decode_raw_video, render_prompt


def run_sys_request(*, video_path, video_sha256, question, vision, model, tokenizer,
                    preprocess, board, max_new_tokens, cpu_linear_fallback=None,
                    on_token=None, decoder=decode_raw_video, generator=generate,
                    prompt_renderer=render_prompt):
    trace = TokenTrace((151645,))
    record = dict(track='SYS', input_sha256=video_sha256, question=question,
                  raw_video_decoded_in_this_process=True, full_visual_tokens=784,
                  cache_policy='model-hot; request-KV/vision/answer-cold',
                  hardware_proof_verified=False, numerical_gate_pass=False,
                  requested_max_new_tokens=max_new_tokens)

    def timed(name, function):
        start = trace.clock()
        try:
            return function()
        finally:
            trace.stage(name, start, trace.clock())

    try:
        frames, decode_evidence = timed('video_decode_resize', lambda: decoder(video_path, video_sha256))
        if frames.shape != (4,448,448,3) or frames.dtype != np.uint8:
            raise ValueError('Raw decoder frame geometry/dtype mismatch')
        record['input'] = decode_evidence
        prepared = timed('vision_preprocess', lambda: preprocess(frames))
        visual = timed('vision_forward', lambda: vision(**prepared))
        if visual.shape != (784,2560) or not np.isfinite(visual).all():
            raise ValueError('Full visual output invalid; do not silently prune')
        prompt = prompt_renderer(question, decode_evidence['actual_frame_times_s'])
        token_ids = timed('tokenization', lambda: tokenizer.encode(prompt).ids)
        record.update(prompt_sha256=hashlib.sha256(prompt.encode()).hexdigest(),
                      prompt_token_count=len(token_ids), input_token_ids=token_ids,
                      visual_fp32_sha256=hashlib.sha256(np.asarray(visual,dtype='<f4').tobytes()).hexdigest())
        hidden = timed('embedding_lookup', lambda: model.input_embeddings(token_ids,visual))
        before = board.evidence()
        record['board_before'] = before
        generated = generator(model,hidden,max_new_tokens=max_new_tokens,trace=trace,
            logical_calls_before=lambda:int(board.logical_calls),
            logical_calls_after=lambda:int(board.logical_calls),
            cpu_linear_fallback=cpu_linear_fallback,on_token=on_token)
        record['generation'] = generated
        record['answer'] = tokenizer.decode(generated['valid_token_ids'],skip_special_tokens=True)
        record['status'] = generated['status']
        if not record['answer'].strip():
            record['status']='FAIL'
            record['error']='No nonempty answer'
    except GenerationFailure as exc:
        record.update(status='FAIL',error=str(exc),generation=exc.result)
    except Exception as exc:
        record.update(status='FAIL',error=f'{type(exc).__name__}: {exc}')
        # Preserve partial timing, rather than turning input/vision failure into
        # a passing request or silently dropping it from the denominator.
        record['partial_top_level_stages']=list(trace.stages)
        record['partial_elapsed_s']=(trace.clock()-trace.start_ns)/1e9
    try:
        record['board_after']=board.evidence()
    except Exception as exc:
        record.update(status='FAIL',board_evidence_error=f'{type(exc).__name__}: {exc}')
    return record


def run_raw_contract_request(**kwargs):
    """Explicit version2 entry; legacy SYS adapter remains reproducible."""
    from video_contract_v2 import preprocess_raw_frames,render_raw_prompt
    actual_decoder=kwargs.pop('decoder',decode_raw_video)
    decoded={}
    def decode_and_bind(*args):
        frames,evidence=actual_decoder(*args)
        decoded['source_frame_indices']=evidence['selected_frame_indices']
        return frames,evidence
    # A local renderer argument avoids changing module globals across requests.
    kwargs['preprocess']=lambda frames:preprocess_raw_frames(frames,decoded['source_frame_indices'])
    return run_sys_request(**kwargs,decoder=decode_and_bind,prompt_renderer=render_raw_prompt)
