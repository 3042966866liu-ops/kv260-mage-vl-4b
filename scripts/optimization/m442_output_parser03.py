"""FP16 DMA views -> final FP32 slices, without full FP32 temporaries.

Independent candidate; importing this module never patches a runtime. The
caller retains the existing parser Future/DMA ownership and finite retry rules.
Unlike M332 this also fuses dtype conversion and interleave reconstruction.
"""
from __future__ import annotations

import numpy as np


def parse_into_and_check(chain, payload, targets, token_start, token_count,
                         output_scale_shift):
    if not isinstance(output_scale_shift, int) or not 0 <= output_scale_shift <= 10:
        raise ValueError("output_scale_shift must be an integer in [0, 10]")
    if not 1 <= token_count <= 32 or token_start < 0:
        raise ValueError("invalid token slice")
    raw = memoryview(payload).cast("B")
    if len(raw) != int(chain["output_bytes"]):
        raise RuntimeError("M442 output packet size mismatch")

    # Validate the entire write plan before touching any target. Output storage
    # must be independent of the DMA packet; only metadata/views are allocated.
    plan = []
    cursor = 0
    for descriptor in chain["descriptors"]:
        rows = int(descriptor["rows_per_shard"])
        size = int(descriptor["output_bytes"])
        valid = int(descriptor["valid_rows"])
        name = descriptor.get("module", "lm_head")
        start = int(descriptor["row_start"])
        if rows <= 0 or rows % 8 or size != 32 * 4 * rows * 4:
            raise RuntimeError("M442 descriptor geometry mismatch")
        if not 0 < valid <= 4 * rows or start < 0 or cursor + size > len(raw):
            raise RuntimeError("M442 descriptor bounds mismatch")
        target = targets.get(name)
        if (not isinstance(target, np.ndarray) or target.dtype != np.float32
                or target.ndim != 2 or not target.flags.writeable
                or target.shape[0] < token_start + token_count
                or target.shape[1] < start + valid
                or min(target.strides) <= 0):
            raise RuntimeError("M442 preallocated target is incomplete or unsafe")
        source = np.ndarray((rows // 8, 32, 4, 4, 2), dtype="<f2",
                            buffer=raw[cursor:cursor + size],
                            strides=(4096, 128, 32, 8, 4)).transpose(1, 2, 0, 3, 4)
        if np.may_share_memory(source, target):
            raise RuntimeError("M442 DMA packet aliases final output")
        destination = target[token_start:token_start + token_count, start:start + valid]
        plan.append((source, destination, rows, valid))
        cursor += size
    if cursor != len(raw) or not plan:
        raise RuntimeError("M442 output cursor mismatch")

    finite = True
    for source, destination, rows, valid in plan:
        # The wire channel order is shard -> block -> pair -> lane. Each copy
        # casts FP16 directly into its final FP32 channel locations. Padding and
        # inactive tokens are never copied, scaled, or checked.
        for shard in range(4):
            count = min(rows, max(0, valid - shard * rows))
            if not count:
                continue
            whole, tail = divmod(count, 8)
            offset = shard * rows
            if whole:
                view = destination[:, offset:offset + whole * 8].reshape(token_count, whole, 4, 2)
                if view.ctypes.data != destination[:, offset:offset + whole * 8].ctypes.data or any(n > 1 and actual != expected for n, actual, expected in zip(view.shape, view.strides, (destination.strides[0], 8 * destination.strides[1], 2 * destination.strides[1], destination.strides[1]))):
                    raise RuntimeError("M442 destination reshape unexpectedly copied")
                np.copyto(view, source[:token_count, shard, :whole], casting="unsafe")
            if tail:
                view = source[:token_count, shard, whole].reshape(token_count, 8)
                np.copyto(destination[:, offset + whole * 8:offset + count],
                          view[:, :tail], casting="unsafe")
        if output_scale_shift:
            # Preserve the accepted ldexp operation, including NaN/Inf behavior;
            # out= avoids both its result allocation and the redundant astype.
            np.ldexp(destination, -output_scale_shift, out=destination)
        finite = bool(np.isfinite(destination).all()) and finite
    # Like M236, false means the existing owner must retry/overwrite this slice
    # before publishing it. This function does not free, reuse, or own DMA.
    return finite
