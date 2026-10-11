"""Bounded paired Decode experiment; caller owns hardware and persistence.

No timing result here is a performance gate. The same warm-up protocol is not
proof of identical page-cache contents under different memory pressure.
"""
import gc
import hashlib
import time
import numpy as np
from memory_lifecycle import memory_snapshot, release_vision, glibc_trim


def run_trial(*, vision_holder, restore, prepare_reads, decode,
              snapshot=memory_snapshot, release=release_vision, trim=glibc_trim,
              on_record=lambda record:None):
    records=[]
    baseline=None
    for state in ('A-retained','B-released','C-trimmed'):
        transition={}
        if state=='B-released':
            transition=release(vision_holder,snapshot=snapshot,trim=False)
            if not transition['object_released']:
                raise RuntimeError('Vision retains an external reference; stop before claiming release')
        elif state=='C-trimmed':
            transition=dict(before=snapshot(),trim=trim(),after=snapshot())
            if not transition['trim'].get('called'):
                raise RuntimeError('malloc_trim unavailable; no C observation')
        # Restore before the common read preparation, never copy 250MB into a
        # second permanent cache just to reset a mutated KV cache.
        started=time.perf_counter()
        token,cache=restore()
        restore_s=time.perf_counter()-started
        preparation=prepare_reads()
        before=snapshot()
        started=time.perf_counter()
        output,logits,detail=decode(token,cache)
        elapsed=time.perf_counter()-started
        logits=np.asarray(logits)
        if logits.dtype!=np.float32 or not np.isfinite(logits).all():
            raise RuntimeError('Invalid Decode logits')
        identity=dict(token=int(output),shape=list(logits.shape),
            sha256=hashlib.sha256(logits.tobytes()).hexdigest())
        if baseline is None:baseline=identity
        record=dict(state=state,transition=transition,restore_s=restore_s,
            preparation=preparation,memory_before=before,memory_after=snapshot(),
            decode_callback_wall_s=elapsed,token_ready_s=detail.get('token_ready_s'),
            output=identity,logits_bit_exact_vs_A=identity==baseline,
            detail=detail,timing_eligible=False)
        records.append(record);on_record(record)
        if identity!=baseline:
            raise RuntimeError('Full logits differ; retained mismatch evidence and stopped')
        del cache,logits,detail
        gc.collect()
    return dict(status='MEASURED',records=records,performance_pass=False,
        caveat='A-B-C order confounded; independent order replication required. Read preparation changes real serving cost.')
