"""Fixed-width G64 FLAP primitives for language and vision MLPs.

Uses the existing WIFV-inspired population-variance metric. It performs no
width/layer search. Attention/residual dimensions and channel order stay fixed.
Vision's existing output bias can absorb the mean of removed channels. Language
keeps its bias-free interface and can reuse the separate Down-refit pipeline.
"""
import numpy as np
from .language_flap_g64_01 import group_scores


def _quantized(pair):
    codes, scales = pair
    if not isinstance(codes,np.ndarray) or not isinstance(scales,np.ndarray):
        raise ValueError('Explicit quantized arrays required')
    if codes.dtype != np.int8 or codes.ndim != 3 or codes.shape[2] != 64 or scales.dtype != np.float16 or scales.shape != codes.shape[:2]:
        raise ValueError('Signed codes and FP16 G64 scales required')
    if not np.isfinite(scales).all() or (scales <= 0).any() or (codes < -8).any() or (codes > 8).any() or (codes.max(axis=2).astype(np.int16)-codes.min(axis=2).astype(np.int16) > 15).any():
        raise ValueError('Finite positive W2/W4 endpoint-grid arrays required')
    return codes,scales


def _groups(groups, count):
    keep = np.asarray(groups)
    if keep.ndim != 1 or keep.dtype.kind not in 'iu' or not 0 < len(keep) < count or np.any(keep < 0) or np.any(keep >= count) or np.any(np.diff(keep.astype(np.int64)) <= 0):
        raise ValueError('Strictly increasing retained original G64 groups required')
    return keep.astype(np.int64)


def select_fixed_width(down, middle, width):
    codes,scales = _quantized(down)
    full = codes.shape[1]*64
    if type(width) is not int or not 64 <= width < full or width % 64:
        raise ValueError('Fixed smaller G64 width required')
    x = np.asarray(middle)
    if x.ndim != 2 or x.shape[1] != full:
        raise ValueError('Original post-activation training rows required')
    energy = np.zeros(full,np.float64)
    for start in range(0,len(codes),64):
        block = (codes[start:start+64].astype(np.float64)*scales[start:start+64].astype(np.float64)[...,None]).reshape(-1,full)
        energy += (block*block).sum(axis=0)
    scores,mean,variance = group_scores(x,energy,method='flap')
    order = np.lexsort((np.arange(len(scores)),-scores))
    keep = np.sort(order[:width//64]).astype(np.int64)
    return keep,dict(group_scores=scores,mean=mean,variance=variance,column_energy=energy)


def crop_gated_language(weights, groups):
    if len(weights) != 3:
        raise ValueError('Linked Gate/Up/Down required')
    gate,up,down = [_quantized(w) for w in weights]
    keep = _groups(groups,down[0].shape[1])
    full = down[0].shape[1]*64
    if gate[0].shape != up[0].shape or gate[0].shape[0] != full or gate[0].shape[1]*64 != down[0].shape[0]:
        raise ValueError('Complete gated MLP residual dimensions differ')
    rows = (keep[:,None]*64+np.arange(64)).ravel()
    result = [(c[rows].copy(),s[rows].copy()) for c,s in (gate,up)]
    result.append((down[0][:,keep].copy(),down[1][:,keep].copy()))
    return result


def crop_vision_mlp(fc1,fc2,bias1,bias2,groups,mean):
    c1,s1 = _quantized(fc1)
    c2,s2 = _quantized(fc2)
    keep = _groups(groups,c2.shape[1])
    full = c2.shape[1]*64
    b1,b2,mu = np.asarray(bias1),np.asarray(bias2),np.asarray(mean)
    if c1.shape[0] != full or c1.shape[1]*64 != c2.shape[0] or b1.shape != (full,) or b2.shape != (len(c2),) or mu.shape != (full,):
        raise ValueError('Complete biased vision MLP dimensions differ')
    if any(a.dtype.kind != 'f' or not np.isfinite(a).all() for a in (b1,b2,mu)):
        raise ValueError('Finite original biases and training mean required')
    rows = (keep[:,None]*64+np.arange(64)).ravel()
    removed = np.ones(c2.shape[1],bool)
    removed[keep] = False
    # Fixed mean compensation folds into the already-present FC2 bias.
    # FP64 reference accumulation, one final FP32 serialization.
    mu_removed = mu.reshape(-1,64)[removed].astype(np.float64)
    corrected = b2.astype(np.float64).copy()
    for start in range(0,len(c2),64):
        w = c2[start:start+64,removed].astype(np.float64)*s2[start:start+64,removed].astype(np.float64)[...,None]
        corrected[start:start+64] += np.einsum('ogc,gc->o',w,mu_removed)
    corrected = corrected.astype(np.float32)
    if not np.isfinite(corrected).all():
        raise ValueError('Vision mean compensation overflow')
    return dict(fc1=(c1[rows].copy(),s1[rows].copy()),
                fc2=(c2[:,keep].copy(),s2[:,keep].copy()),
                bias1=b1[rows].astype(np.float32).copy(),bias2=corrected,
                kept_groups=keep,extra_inference_operations=0)
