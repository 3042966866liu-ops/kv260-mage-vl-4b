"""Identical bounded read preparation in each lifecycle state; no cache eviction."""
import hashlib
from pathlib import Path
import time


def prepare_reads(plan, *, snapshot, progress=lambda text:None):
    rows=plan['windows']
    if len(rows)!=648 or sum(r['bytes'] for r in rows)!=2034890752:
        raise RuntimeError('Unexpected Decode read plan')
    root=Path('/home/ubuntu/tellme_m120_m89x2_20260901/m120_fulltext_weights_0x4D395832').resolve()
    for row in rows:
        path=Path(row['path']).resolve()
        if root not in path.parents or not 0<row['bytes']<=8*1024*1024 or row['offset']<0:
            raise RuntimeError('Read outside verified weight scope')
    passes=[]
    for iteration in range(2):
        read_ns=hash_ns=storage=0
        started=time.perf_counter_ns()
        for index,row in enumerate(rows):
            before=snapshot();begin=time.perf_counter_ns()
            with Path(row['path']).open('rb',buffering=0) as stream:
                stream.seek(row['offset']);raw=stream.read(row['bytes'])
            read_ns+=time.perf_counter_ns()-begin
            after=snapshot();storage+=after['read_bytes']-before['read_bytes']
            begin=time.perf_counter_ns()
            if len(raw)!=row['bytes'] or hashlib.sha256(raw).hexdigest()!=row['sha256']:
                raise RuntimeError('Read preparation identity mismatch')
            hash_ns+=time.perf_counter_ns()-begin
            del raw
            if index%128==0:progress(f'LIFECYCLE_READ pass={iteration} window={index}/648')
        passes.append(dict(iteration=iteration,wall_s=(time.perf_counter_ns()-started)/1e9,
            read_s=read_ns/1e9,hash_s=hash_ns/1e9,process_storage_read_bytes=storage))
    return dict(passes=passes,protocol='two verified Decode-order scans; no drop_caches',
        identical_residency_claimed=False,total_bytes_per_pass=2034890752)
