"""CPU-only M120 group arithmetic reference; never a board fallback.

INT8 x W2/W4 integer dot, then two distinct FP32 multiplications and ordered
group accumulation, final FP16. Float32 CPU BLAS is an exact integer-dot
implementation here: every partial sum is bounded by 64*128*8 = 65536,
well below 2**24. Do not enable reduced-precision/TF32 GEMM for this oracle.
This covers decoded group arithmetic, not packet parsing or a whole model.
"""
import numpy as np


def group_reference(codes, activation_scales, weights, weight_scales, *, dot_mode='int32'):
    a=np.asarray(codes);w=np.asarray(weights)
    sa=np.asarray(activation_scales);sw=np.asarray(weight_scales)
    if a.ndim!=3 or w.ndim!=3 or a.shape[2]!=64 or w.shape[2]!=64 or a.shape[1]!=w.shape[0]:
        raise ValueError('Expected codes[T,G,64] and weights[G,R,64]')
    if min(*a.shape,*w.shape)<=0 or a.dtype.kind not in 'iu' or w.dtype.kind not in 'iu':
        raise ValueError('Nonempty integer codes required')
    if a.min() < -128 or a.max()>127 or w.min() < -8 or w.max()>8:
        raise ValueError('Codes outside proven exact integer-dot bound')
    if sa.shape!=a.shape[:2] or sw.shape!=w.shape[:2] or sa.dtype!=np.float16 or sw.dtype!=np.float16:
        raise ValueError('Scales must be transmitted FP16 with matching shape')
    if not np.isfinite(sa).all() or not np.isfinite(sw).all() or np.any(sa<0) or np.any(sw<0):
        raise ValueError('Nonnegative finite scales required')
    if dot_mode not in ('int32','fp32_exact'):raise ValueError('Unknown dot mode')
    dtype=np.int32 if dot_mode=='int32' else np.float32
    result=np.zeros((a.shape[0],w.shape[1]),np.float32)
    for group in range(a.shape[1]):
        dots=a[:,group,:].astype(dtype) @ w[group].astype(dtype).T
        term=dots.astype(np.float32)*sa[:,group,None].astype(np.float32)
        term=term*sw[group,None,:].astype(np.float32)
        result=(result+term).astype(np.float32)
    # Infinity is intentionally observable so the caller's frozen retry policy
    # can reject/retry it. Never clip overflow to obtain a passing comparison.
    with np.errstate(over='ignore'):
        return result.astype('<f2')
