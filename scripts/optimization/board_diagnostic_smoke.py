"""Target-Python software smoke; no PYNQ allocations, overlay or inference."""
import hashlib
import json
from pathlib import Path
import sys
import tempfile
from types import SimpleNamespace

def digest(p):return hashlib.sha256(p.read_bytes()).hexdigest()
if digest(Path(__file__))!=sys.argv[1]:raise RuntimeError('Smoke identity mismatch')
root=Path('/home/ubuntu/tellme_m120_m89x2_20260901')
package=root/'optimization_v1/OP01-SYS-05'
manifest=package/'PACKAGE_MANIFEST.json'
expected='a6028ce4b6da1f9b5e94b3e121a070b3f17c3f1d299c52f90a73b71e5bee2a2b'
if digest(manifest)!=expected:raise RuntimeError('Package mismatch')
for row in json.loads(manifest.read_text())['files']:
    if digest(package/row['path'])!=row['sha256']:raise RuntimeError('Member mismatch')
config=json.loads((package/'sys_config.json').read_text())
sys.path[:0]=[str(package)]+[str(root/p) for p in config['python_path']]
import numpy as np
import board_runtime
from decode_trace import DecodeTrace
from transfer_trace import instrument
from decode_checkpoint import save_checkpoint,load_checkpoint

class Buffer:
    def __init__(self):self.array=np.zeros(128,np.uint8);self.syncs=0
    def __setitem__(self,key,value):self.array[key]=value
    def sync_to_device(self):self.syncs+=1

with tempfile.TemporaryDirectory(prefix='decode_smoke_',dir='/dev/shm') as temp:
    folder=Path(temp);weight=folder/'weight.bin';weight.write_bytes(bytes(range(256)))
    trace=DecodeTrace();original=Buffer();observed=Buffer()
    board_runtime.copy_window_to_buffer(weight,19,128,original)
    measured=instrument(board_runtime.copy_window_to_buffer,trace)
    with trace.span('copy_total'):measured(weight,19,128,observed)
    assert np.array_equal(original.array,observed.array)
    assert original.syncs==observed.syncs==1
    short=Buffer()
    try:measured(weight,256,128,short)
    except RuntimeError:pass
    else:raise RuntimeError('Short read unexpectedly accepted')
    assert short.syncs==0
    cache=SimpleNamespace(keys=[np.arange(12,dtype=np.float32).reshape(3,2,2)],
                          values=[np.ones((3,2,2),np.float32)])
    identity=dict(scope='synthetic software smoke, not model checkpoint')
    saved=save_checkpoint(folder/'checkpoint',cache,1291,identity)
    token,reloaded=load_checkpoint(folder/'checkpoint',digest(folder/'checkpoint/manifest.json'),identity,
                                  lambda k,v:SimpleNamespace(keys=k,values=v))
    assert token==1291 and np.array_equal(cache.keys[0],reloaded.keys[0])
    assert np.array_equal(cache.values[0],reloaded.values[0])
    result=dict(status='PASS_SOFTWARE_SMOKE_ONLY',package_manifest_sha256=expected,
                byte_exact=True,sync_count=observed.syncs,short_read_rejected=True,
                checkpoint_exact=True,overlay_loaded=False,model_executed=False,
                trace=trace.report(),python=sys.version)
print('DIAGNOSTIC_SMOKE_JSON_BEGIN')
print(json.dumps(result))
print('DIAGNOSTIC_SMOKE_JSON_END')
