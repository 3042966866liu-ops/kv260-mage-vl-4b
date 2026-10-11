"""Explicit diagnostic KV checkpoint. Never invoke inside a timed Decode span."""
import json
import os
from pathlib import Path
import time
import numpy as np
from measurement import sha256, write_json
from decode_trace import cache_geometry

MAX_BYTES=384*1024*1024


def save_checkpoint(directory, cache, next_token, identity):
    geometry=cache_geometry(cache)
    arrays=[array for pair in zip(cache.keys,cache.values) for array in pair]
    if any(a.dtype!=np.float32 or not np.isfinite(a).all() for a in arrays):
        raise ValueError('Checkpoint requires finite FP32 KV')
    if sum(a.nbytes for a in arrays)>MAX_BYTES:
        raise ValueError('Checkpoint exceeds memory/storage bound')
    if isinstance(next_token,bool) or not isinstance(next_token,int) or next_token<0:
        raise ValueError('Invalid next input token')
    root=Path(directory);root.mkdir(parents=True,exist_ok=False)
    start=time.perf_counter_ns();rows=[]
    manifest=dict(status='WRITING',identity=identity,next_token=next_token,
                  geometry=geometry,files=rows,timing_eligible=False)
    write_json(root/'manifest.json',manifest)
    try:
        for layer,(key,value) in enumerate(zip(cache.keys,cache.values)):
            for kind,array in (('key',key),('value',value)):
                path=root/f'layer{layer:02d}_{kind}.npy'
                with path.open('xb') as stream:
                    np.save(stream,array,allow_pickle=False)
                    stream.flush();os.fsync(stream.fileno())
                rows.append(dict(path=path.name,shape=list(array.shape),dtype=str(array.dtype),
                                 bytes=path.stat().st_size,sha256=sha256(path)))
        manifest.update(status='RECORDED',save_ns=time.perf_counter_ns()-start)
        write_json(root/'manifest.json',manifest)
        return manifest
    except BaseException as exc:
        manifest.update(status='FAIL',error=f'{type(exc).__name__}: {exc}')
        write_json(root/'manifest.json',manifest)
        raise


def load_checkpoint(directory, expected_manifest_sha256, expected_identity, cache_factory):
    root=Path(directory).resolve();manifest_path=root/'manifest.json'
    if sha256(manifest_path)!=expected_manifest_sha256:
        raise ValueError('Checkpoint manifest hash mismatch')
    manifest=json.loads(manifest_path.read_text())
    if manifest['status']!='RECORDED' or manifest['identity']!=expected_identity:
        raise ValueError('Checkpoint status/identity mismatch')
    rows=manifest['files'];layers=len(manifest['geometry']['layers'])
    names=[f'layer{i:02d}_{kind}.npy' for i in range(layers) for kind in ('key','value')]
    if [r['path'] for r in rows]!=names or not layers:
        raise ValueError('Checkpoint member order mismatch')
    if {p.name for p in root.iterdir()}!=set(names)|{'manifest.json'}:
        raise ValueError('Checkpoint unexpected members')
    if sum(r['bytes'] for r in rows)>MAX_BYTES+len(rows)*4096:
        raise ValueError('Checkpoint size bound exceeded')
    arrays=[]
    for row in rows:
        path=root/row['path']
        if path.is_symlink() or path.stat().st_size!=row['bytes'] or sha256(path)!=row['sha256']:
            raise ValueError('Checkpoint member hash/size mismatch')
        value=np.load(path,allow_pickle=False)
        if value.dtype!=np.float32 or list(value.shape)!=row['shape'] or not np.isfinite(value).all():
            raise ValueError('Checkpoint tensor mismatch')
        arrays.append(value)
    cache=cache_factory(arrays[::2],arrays[1::2])
    geometry=cache_geometry(cache)
    if [r['key_shape'] for r in geometry['layers']]!=[r['key_shape'] for r in manifest['geometry']['layers']]:
        raise ValueError('Checkpoint geometry mismatch')
    return manifest['next_token'],cache
