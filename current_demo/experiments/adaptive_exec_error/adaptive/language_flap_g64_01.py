"""FLAP WIFV-inspired G64 selection, not FLAP's bias/global allocation.

Population variance is computed over true calibration token rows in FP64.
Original W4 Down column energies weight channel fluctuations; group scores
are sums, and retained groups stay in their original order. No inference op
is added. See https://github.com/CASIA-LMC-Lab/FLAP/blob/main/lib/prune.py .
"""
import numpy as np


def group_scores(middle, column_energy, *, method='flap', group_size=64):
    x=np.asarray(middle);e=np.asarray(column_energy)
    if (x.dtype!=np.float32 or x.ndim!=2 or len(x)<2 or
            group_size!=64 or x.shape[1]%64 or e.shape!=(x.shape[1],) or
            not np.isfinite(x).all() or not np.isfinite(e).all() or (e<0).any()):
        raise ValueError('Finite FP32 calibration rows and nonnegative column energies, G64 required')
    if method not in ('flap','energy'):raise ValueError('Unknown selection metric')
    z=x.astype(np.float64);mean=z.mean(axis=0)
    statistic=((z-mean)**2).mean(axis=0) if method=='flap' else (z*z).mean(axis=0)
    return (statistic*e.astype(np.float64)).reshape(-1,64).sum(axis=1),mean,statistic


def select_groups(weights,middle,width,*,method='flap'):
    if width not in (8192,9216) or middle.shape[1:]!=(9728,):
        raise ValueError('Original 9728 ->8192/9216 only')
    c,s=weights[2]
    if c.shape!=(2560,152,64) or s.shape!=(2560,152):raise ValueError('Original Down W4/G64 required')
    if not np.isfinite(s).all() or (s<=0).any():raise ValueError('Positive finite FP16 scales required')
    # Chunk rows to avoid an extra full FP64 Down matrix allocation.
    energy=np.zeros(9728,np.float64)
    for start in range(0,2560,64):
        w=(c[start:start+64].astype(np.float64)*s[start:start+64].astype(np.float64)[...,None]).reshape(-1,9728)
        energy+=(w*w).sum(axis=0)
    scores,mean,statistic=group_scores(middle,energy,method=method)
    order=np.lexsort((np.arange(152),-scores))
    return np.sort(order[:width//64]).astype(np.int64),scores,dict(mean=mean,statistic=statistic,column_energy=energy)
