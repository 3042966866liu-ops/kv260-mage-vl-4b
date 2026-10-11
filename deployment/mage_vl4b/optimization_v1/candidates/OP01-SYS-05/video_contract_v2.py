"""Raw-video adapter matching frozen official preprocessing primitives.

Separate candidate: do not modify the stable legacy browser/RGB runtime.
Actual source indices carry temporal positions; PTS tags use training precision.
"""
import math
import numpy as np


def preprocess_raw_frames(frames,source_frame_indices):
    rgb=np.asarray(frames)
    indices=np.asarray(source_frame_indices)
    if rgb.shape!=(4,448,448,3) or rgb.dtype!=np.uint8:
        raise ValueError('Expected four448 RGB uint8 frames')
    if (indices.shape!=(4,) or indices.dtype.kind not in 'iu' or
        np.any(indices<0) or np.any(np.diff(indices.astype(np.int64))<=0)):
        raise ValueError('Four increasing source frame indices required')
    # Frozen Transformers5.15 Qwen2VL processor fuses rescale into mean/std.
    # Despite old model comments calling it slow, the installed class uses Torchvision.
    pixels=rgb.transpose(0,3,1,2).astype(np.float32)
    mean=(np.asarray((0.48145466,0.4578275,0.40821073),np.float32)*np.float32(255.0)).reshape(1,3,1,1)
    std=(np.asarray((0.26862954,0.26130258,0.27577711),np.float32)*np.float32(255.0)).reshape(1,3,1,1)
    pixels=(pixels-mean)/std
    pixels=pixels.reshape(4,3,14,2,16,14,2,16).transpose(0,2,5,3,6,1,4,7).reshape(3136,768)
    h=np.tile(np.repeat(np.arange(28),28),4)
    w=np.tile(np.arange(28),112)
    t=np.repeat(indices.astype(np.int64),784)
    positions=np.stack([t,h,w],axis=1)
    order=np.arange(3136).reshape(4,14,2,14,2).transpose(0,1,3,2,4).reshape(-1)
    return dict(pixel_values=np.ascontiguousarray(pixels),patch_positions=positions[order],
                image_grid_thw=np.tile(np.asarray([[1,28,28]],np.int64),(4,1)))


def render_raw_prompt(question,sample_times_s):
    question=question.strip();times=list(sample_times_s)
    if not 1<=len(question)<=3000 or len(times)!=4:
        raise ValueError('Question and four timestamps required')
    if any(not math.isfinite(t) or not 0<=t<4 for t in times) or any(a>=b for a,b in zip(times,times[1:])):
        raise ValueError('Invalid four-second PTS')
    blocks=''.join(f'<{t:.1f} seconds><|vision_start|>'+ '<|image_pad|>'*196+'<|vision_end|>' for t in times)
    return ('<|im_start|>system\nYou are a helpful assistant.<|im_end|>\n'
            f'<|im_start|>user\n{blocks}{question}<|im_end|>\n<|im_start|>assistant\n')
