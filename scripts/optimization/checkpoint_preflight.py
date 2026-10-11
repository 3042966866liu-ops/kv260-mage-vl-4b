"""Verify and actually restore saved KV, without loading model or overlay."""
import hashlib
import json
import os
from pathlib import Path
import sys
import time
from types import SimpleNamespace


def digest(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def main():
    script_sha,plan_sha=sys.argv[1:];here=Path(__file__).resolve().parent
    if digest(__file__)!=script_sha or digest(here/'plan.json')!=plan_sha:raise RuntimeError('Probe identity')
    plan=json.loads((here/'plan.json').read_text());out=here/'result.json'
    if out.exists():raise RuntimeError('Immutable result')
    result=dict(status='FAIL',scope='Real saved KV restore only; no model or FPGA execution',
        script_sha256=script_sha,plan_sha256=plan_sha,errors=[],overlay_loaded=False,model_executed=False)
    try:
        root=Path('/home/ubuntu/tellme_m120_m89x2_20260901');package=root/'optimization_v1/OP01-SYS-05'
        manifest=package/'PACKAGE_MANIFEST.json'
        if digest(manifest)!=plan['package_manifest_sha256']:raise RuntimeError('Frozen package hash')
        for row in json.loads(manifest.read_text())['files']:
            member=package/row['path']
            if member.stat().st_size!=row['bytes'] or digest(member)!=row['sha256']:raise RuntimeError('Package member changed')
        sys.path.insert(0,str(package))
        from decode_checkpoint import load_checkpoint
        from decode_trace import cache_geometry
        started=time.perf_counter_ns()
        token,cache=load_checkpoint(root/'optimization_v1/decode_checkpoints/SYS05-prefill',
            plan['checkpoint_manifest_sha256'],plan['identity'],lambda k,v:SimpleNamespace(keys=k,values=v))
        geometry=cache_geometry(cache)
        if token!=plan['next_token'] or len(geometry['layers'])!=36 or any(r['key_shape']!=[852,8,128] for r in geometry['layers']):
            raise RuntimeError('Restored real KV shape/token mismatch')
        result.update(status='RESTORED',next_token=token,layer_count=36,kv_length=852,
            manifest_sha256=plan['checkpoint_manifest_sha256'],arrays_verified=72,
            array_bytes=sum(a.nbytes for a in cache.keys+cache.values),
            restore_s=(time.perf_counter_ns()-started)/1e9,meminfo_loaded=Path('/proc/meminfo').read_text())
        del cache
    except Exception as exc:result['errors'].append(repr(exc))
    tmp=out.with_suffix('.partial');tmp.write_text(json.dumps(result,indent=2,allow_nan=False)+'\n');os.replace(tmp,out)
    print('CHECKPOINT_JSON_BEGIN');print(json.dumps(result));print('CHECKPOINT_JSON_END',flush=True)
    return 0 if result['status']=='RESTORED' else 1

if __name__=='__main__':raise SystemExit(main())
