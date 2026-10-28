"""Training-mean compensation for removed G64 channels.

Vision folds this into its existing FC2 bias. Language requires one explicit
broadcast add after the completed Down family: it is not zero-cost hardware.
"""
import numpy as np


def removed_mean_bias(down, groups, mean, original_bias=None):
    codes,scales=down
    keep=np.asarray(groups)
    mu=np.asarray(mean)
    if codes.dtype!=np.int8 or codes.ndim!=3 or codes.shape[2]!=64 or scales.dtype!=np.float16 or scales.shape!=codes.shape[:2]:
        raise ValueError('Frozen signed-code FP16-scale G64 matrix required')
    if keep.ndim!=1 or keep.dtype.kind not in 'iu' or not 0<len(keep)<codes.shape[1] or np.any(np.diff(keep.astype(np.int64))<=0) or keep.min()<0 or keep.max()>=codes.shape[1]:
        raise ValueError('Strictly sorted retained groups required')
    if mu.shape!=(codes.shape[1]*64,) or not np.isfinite(mu).all() or not np.isfinite(scales).all():
        raise ValueError('Finite original training mean and scales required')
    bias=np.zeros(len(codes),np.float64) if original_bias is None else np.asarray(original_bias,np.float64).copy()
    if bias.shape!=(len(codes),) or not np.isfinite(bias).all():raise ValueError('Original output bias shape differs')
    removed=np.ones(codes.shape[1],bool);removed[keep]=False
    values=mu.reshape(-1,64)[removed].astype(np.float64)
    for start in range(0,len(codes),64):
        block=codes[start:start+64,removed].astype(np.float64)*scales[start:start+64,removed].astype(np.float64)[...,None]
        bias[start:start+64]+=np.einsum('ogc,gc->o',block,values)
    bias=bias.astype(np.float32)
    if not np.isfinite(bias).all():raise ValueError('Removed-channel mean compensation overflow')
    return bias
