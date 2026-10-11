"""Opt-in CPU-only real fixed159 gate/up comparison. No model/Overlay imports."""
import argparse
import gc
import hashlib
import json
import os
from pathlib import Path
import platform
import time
import traceback
import weakref
import numpy as np
from m389_silu_workspace import SiluWorkspace
from original_silu import silu

HERE=Path(__file__).resolve().parent
OUT=Path('/home/ubuntu/m391_silu_component_01')
CAPTURE=Path('/home/ubuntu/m390_gate_up_capture_01/B1/load-memory.json')

def sha(p):
    h=hashlib.sha256()
    with p.open('rb') as f:
        while True:
            b=f.read(1024*1024)
            if not b:break
            h.update(b)
    return h.hexdigest()

def identity(p):
    a=p.lstat();b=p.stat()
    if a!=b or not p.is_file():raise RuntimeError('Not a regular unchanged direct path')
    return [a.st_dev,a.st_ino,a.st_size,a.st_mtime_ns,a.st_ctime_ns,a.st_mode,a.st_nlink]

def memory():
    result={}
    for path,keys in [('/proc/meminfo',('MemAvailable','CmaFree','Cached')),('/proc/self/status',('VmRSS','VmHWM'))]:
        for line in Path(path).read_text(encoding='utf-8').splitlines():
            key=line.split(':',1)[0]
            if key in keys:result[key]=int(line.split()[1])*1024
    return result

def main(digest,enabled=False):
    if not enabled or os.geteuid()!=0:raise RuntimeError('Explicit enabled root required')
    if OUT.exists():raise RuntimeError('Existing result scope; export saved only')
    OUT.mkdir()
    result=dict(status='FAIL_M391_CPU_COMPONENT',gate_level='CPU-only-real159-SiLU-workspace',build_id='0x4D333537',
                gate_return_code=1,errors=[],manifest_sha256=digest,overlay_loaded=False,model_forward_calls=0,fpga_transactions=0,
                production_changed=False,full_request_performance_pass=False,formal_promotion_allowed=False,memory_capacity_proven=False,
                default_enabled=False,numerical_pass=False,component_performance_pass=False,cache_eviction=False,
                environment=dict(python=platform.python_version(),numpy=np.__version__,uname=list(platform.uname()),euid=os.geteuid()),
                batches=[],memory=[],input_file_identities={},input_tensors={},workspace_bytes=6187008,
                timed_scope='File load and numerical hashes outside timers; A includes original astype and result deletion, B lease+five ufunc out+borrow release; workspace create/close separate',
                cache_policy='Natural existing cache, two array inputs retained, equal four-call warmup per variant; no eviction or cache reset',
                planned_rounds=6,calls_per_batch=6,planned_order='ABBABAAB',budget_s=60)
    ws=None;gate=up=None;start=time.perf_counter();input_paths={};refs=[]
    def budget():
        if time.perf_counter()-start>60:raise RuntimeError('Component soft budget exceeded at safe batch boundary')
    try:
        if sha(HERE/'PACKAGE_MANIFEST.json')!=digest:raise RuntimeError('Package manifest differs')
        m=json.loads((HERE/'PACKAGE_MANIFEST.json').read_text(encoding='utf-8'))
        if {p.name for p in HERE.iterdir()}!={r['path'] for r in m['files']}|{'PACKAGE_MANIFEST.json'}:raise RuntimeError('Package whitelist differs')
        if len(m['files'])!=m['file_count'] or sum(r['bytes'] for r in m['files'])!=m['total_bytes']:raise RuntimeError('Count/bytes differ')
        for row in m['files']:
            if Path(row['path']).name!=row['path'] or sha(HERE/row['path'])!=row['sha256'] or (HERE/row['path']).stat().st_size!=row['bytes']:raise RuntimeError('Payload differs')
        spec=json.loads((HERE/'INPUT_IDENTITY.json').read_text(encoding='utf-8'))
        if sha(CAPTURE)!=spec['capture_raw_sha256']:raise RuntimeError('Saved capture raw differs')
        saved=json.loads(CAPTURE.read_text(encoding='utf-8'))
        if saved['status']!='PASS_M390_ACTUAL_GATE_UP_CAPTURE' or not saved['capture_pass'] or saved['actual_gate_up_fixtures']!=spec['fixtures']:raise RuntimeError('Capture scope differs')
        result['capture_raw_sha256']=spec['capture_raw_sha256']
        result['memory'].append(dict(stage='before-inputs',values=memory()))
        arrays={}
        for n in ('gate','up'):
            row=spec['fixtures'][n];p=Path(row['path']);input_paths[n]=p;before=identity(p)
            if p!=CAPTURE.parent/(n+'.npy') or before[2]!=row['file_bytes'] or sha(p)!=row['file_sha256']:raise RuntimeError('Actual fixture file differs')
            a=np.load(p,allow_pickle=False)
            if a.shape!=(159,9728) or a.dtype!=np.float32 or not a.flags.c_contiguous or not np.isfinite(a).all():raise RuntimeError('Fixture shape/dtype/finite differs')
            tensor=dict(shape=list(a.shape),dtype=str(a.dtype),bytes=a.nbytes,sha256=hashlib.sha256(a.tobytes(order='C')).hexdigest())
            if tensor!=row['tensor'] or identity(p)!=before:raise RuntimeError('Fixture tensor/identity differs')
            a.flags.writeable=False;arrays[n]=a;result['input_file_identities'][n]=before;result['input_tensors'][n]=tensor
        gate,up=arrays.pop('gate'),arrays.pop('up');del arrays,a
        t=time.perf_counter_ns();ws=SiluWorkspace((159,9728),enabled=True);result['workspace_create_ns']=time.perf_counter_ns()-t
        refs=[weakref.ref(ws),weakref.ref(ws._buffer)]
        result['memory'].append(dict(stage='inputs-workspace',values=memory()))
        with np.errstate(over='ignore',under='ignore',invalid='raise',divide='raise'):
            reference=silu(gate)*up
            expected_output=hashlib.sha256(reference.tobytes(order='C')).hexdigest()
            with ws.lease(gate,up) as output:
                if not np.array_equal(reference.view(np.uint32),output.view(np.uint32)):raise RuntimeError('Real-input output bits differ')
            del reference,output
            def call(kind):
                if kind=='A':
                    y=silu(gate)*up
                    del y
                else:
                    with ws.lease(gate,up) as y:pass
                    del y
            for kind in 'ABBAABBA':call(kind)
            result['warmup_calls_each']=4;budget()
            for r in range(6):
                for i,kind in enumerate('ABBABAAB'):
                    budget();t=time.perf_counter_ns()
                    for j in range(6):call(kind)
                    dt=time.perf_counter_ns()-t
                    result['batches'].append(dict(round=r,position=i,variant=kind,calls=6,total_ns=dt,ns_per_call=dt/6))
                result['memory'].append(dict(stage='round:'+str(r),values=memory()))
                print('M391_ROUND_COMPLETE',r,flush=True)
            # Fresh post-measurement results and immutable original inputs, no hashing inside timers.
            reference=silu(gate)*up
            if hashlib.sha256(reference.tobytes(order='C')).hexdigest()!=expected_output:raise RuntimeError('Reference changed')
            with ws.lease(gate,up) as output:
                if not np.array_equal(reference.view(np.uint32),output.view(np.uint32)):raise RuntimeError('Post-measurement output bits differ')
            del reference,output
        for n,value in [('gate',gate),('up',up)]:
            if hashlib.sha256(value.tobytes(order='C')).hexdigest()!=result['input_tensors'][n]['sha256'] or identity(input_paths[n])!=result['input_file_identities'][n] or sha(input_paths[n])!=spec['fixtures'][n]['file_sha256']:raise RuntimeError('Input changed')
        del value
        result['output_sha256']=expected_output;result['numerical_pass']=True
        groups=[]
        for r in range(6):
            for order,indexes in [('ABBA',range(4)),('BAAB',range(4,8))]:
                rows=[x for x in result['batches'] if x['round']==r and x['position'] in indexes]
                a=[x['ns_per_call'] for x in rows if x['variant']=='A'];b=[x['ns_per_call'] for x in rows if x['variant']=='B']
                am=sum(a)/2;bm=sum(b)/2
                groups.append(dict(round=r,order=order,A_ns=am,B_ns=bm,gain_ns=am-bm,gain_pct=(am-bm)/am*100,A_range_ns=max(a)-min(a),B_range_ns=max(b)-min(b)))
        av=[x['ns_per_call'] for x in result['batches'] if x['variant']=='A'];bv=[x['ns_per_call'] for x in result['batches'] if x['variant']=='B']
        smallest=min(x['gain_ns'] for x in groups);noise=max(max(x['A_range_ns'],x['B_range_ns']) for x in groups)
        result['groups']=groups
        result['performance_criteria']=dict(all_twelve_order_groups_positive=smallest>0,min_order_gain_exceeds_largest_group_range=smallest>noise,slowest_B_faster_than_fastest_A=max(bv)<min(av),min_gain_ns=smallest,max_group_range_ns=noise,min_A_minus_max_B_ns=min(av)-max(bv))
        result['component_performance_pass']=all(result['performance_criteria'][k] for k in ('all_twelve_order_groups_positive','min_order_gain_exceeds_largest_group_range','slowest_B_faster_than_fastest_A'))
        result['status']='PASS_M391_CPU_MEASUREMENTS'
        result['gate_return_code']=0
    except BaseException as exc:
        result['errors'].append(type(exc).__name__+': '+str(exc));result['traceback']=traceback.format_exc()
    finally:
        try:
            if ws is not None:
                t=time.perf_counter_ns();ws.close();result['workspace_close_ns']=time.perf_counter_ns()-t;ws=None
            gate=up=None;gc.collect()
            result['workspace_object_and_buffer_released']=all(x() is None for x in refs)
            result['memory'].append(dict(stage='after-release',values=memory()))
            if not result['workspace_object_and_buffer_released']:raise RuntimeError('Workspace reference retained')
        except BaseException as exc:
            result['errors'].append('release: '+str(exc));result['gate_return_code']=1;result['status']='FAIL_M391_CPU_COMPONENT'
        result['elapsed_s']=time.perf_counter()-start
        if result['elapsed_s']>60:result['errors'].append('Final elapsed budget exceeded');result['gate_return_code']=1;result['status']='FAIL_M391_CPU_COMPONENT'
        raw=(json.dumps(result,ensure_ascii=True,indent=2)+'\n').encode('utf-8');part=OUT/'RESULT.json.part'
        with part.open('xb') as f:f.write(raw);f.flush();os.fsync(f.fileno())
        os.replace(part,OUT/'RESULT.json')
    print('M391_CPU_RESULT',result['status'],result['gate_return_code'],flush=True)
    return result['gate_return_code']

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('manifest');p.add_argument('--enable-component',action='store_true');args=p.parse_args()
    raise SystemExit(main(args.manifest,args.enable_component))
