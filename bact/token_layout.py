"""Offline, single unpadded sample adapter for post-merger visual pruning.

Does not change vectors or weights. Retains every non-image token and original
order. Language positions are compacted, matching Mage-VL's default 1D policy;
visual 3D positions have already been applied before this adapter.
"""
from dataclasses import dataclass
import numpy as np


@dataclass(frozen=True)
class TokenLayout:
    sequence_indices: np.ndarray
    visual_indices: np.ndarray
    input_ids: np.ndarray
    attention_mask: np.ndarray
    position_ids: np.ndarray
    cache_position: np.ndarray


def select_layout(input_ids, attention_mask, visual_indices, *, image_token_id,
                  frame_counts):
    ids, mask = np.asarray(input_ids), np.asarray(attention_mask)
    keep = np.asarray(visual_indices)
    counts = np.asarray(frame_counts)
    if ids.ndim != 2 or ids.shape[0] != 1 or ids.dtype.kind not in 'iu':
        raise ValueError('only one integer-token sample is supported')
    if mask.shape != ids.shape or not np.all(mask == 1):
        raise ValueError('padding/batched inputs are not supported in this gate')
    visual = np.flatnonzero(ids[0] == image_token_id)
    if counts.ndim != 1 or counts.dtype.kind not in 'iu' or np.any(counts <= 0):
        raise ValueError('positive frame token counts required')
    if counts.sum() != len(visual):
        raise ValueError('visual placeholders do not match frame counts')
    if keep.ndim != 1 or not len(keep) or keep.dtype.kind not in 'iu':
        raise ValueError('nonempty integer visual indices required')
    if np.any(keep < 0) or np.any(keep >= len(visual)) or np.any(np.diff(keep.astype(np.int64)) <= 0):
        raise ValueError('visual indices must be unique, ascending and in range')
    ends = np.cumsum(counts)
    for start, end in zip(np.r_[0, ends[:-1]], ends):
        if not np.any((keep >= start) & (keep < end)):
            raise ValueError('every frame must retain at least one token')
    selected = ids[0] != image_token_id
    selected[visual[keep]] = True
    seq = np.flatnonzero(selected)
    new_ids = ids[:, seq].copy()
    n = len(seq)
    return TokenLayout(seq, keep.copy(), new_ids, mask[:, seq].copy(),
                       np.arange(n, dtype=np.int64)[None, :], np.arange(n, dtype=np.int64))
