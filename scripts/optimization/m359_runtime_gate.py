"""M357 circuit with original M238/M241 math, layer then fixed-text gates."""
import argparse
import fcntl
import hashlib
import importlib
import json
import os
from pathlib import Path
import subprocess
import sys
import threading
import time
import traceback
import numpy as np
from board_safety import safe_to_release
from owned_buffer_release import OwnedBufferRelease
from measurement import sha256,write_json
from m341_build_id_gate import verify_self,service_stopped,STABLE,STABLE_SHA,ROOT
from m120_board_common import KERNEL_NAME,DMA_NAME
from m343_layer_scope import bind

HERE=Path(__file__).resolve().parent
CAND=Path('/home/ubuntu/m357_candidate_01')
CAND_SHA='2e9cbd00d0d01edf05e171674f71f86a94ce389a0658ce6c5466cebb77220d18'
EVIDENCE=Path('/home/ubuntu/m359_runtime_evidence_01')
READY_FOR_EXECUTION=False  # Draft only: M358 capacity failed; no frozen/tested package.

def tensor(value):
    x=np.ascontiguousarray(value)
    if not np.isfinite(x).all():raise FloatingPointError('Nonfinite numerical result')
    return dict(shape=list(x.shape),dtype=str(x.dtype),bytes=x.nbytes,sha256=hashlib.sha256(x.tobytes()).hexdigest())

def exact(a,b):
    return a.dtype==b.dtype and a.shape==b.shape and np.ascontiguousarray(a).tobytes()==np.ascontiguousarray(b).tobytes()

class Lifetime:
    """Own all allocations before an original constructor or launch can fail."""
    def __init__(self,base,result):
        self.base=base;self.result=result;self.runtime=None;self.buffers=[]
        self.active=False;self.ever=False;self.complete=False;self.build=0
    def safe(self):
        rt=self.runtime
        if self.active or rt is None or not hasattr(rt,'kernel') or not hasattr(rt,'dma'):return False
        s=self.base.transaction_snapshot(rt.kernel,rt.dma)
        if any(s.get(k)!='' for k in ('kernel_read_error','return_read_error','dma_read_error')):return False
        if self.ever:return self.complete and safe_to_release(s) and s['ap_return']==self.build
        return s['ap_ctrl']==4 and s['ap_return']==0 and s['mm2s_dmasr']==s['s2mm_dmasr']==0 and not s['mm2s_error'] and not s['s2mm_error']
    def allocate(self,original,*a,**kw):
        b=original(*a,**kw);self.buffers.append(b)
        row=dict(bytes=int(b.nbytes),address=int(self.base.physical_address(b)))
        self.result['allocations'].append(row)
        b.freebuffer=OwnedBufferRelease(b.freebuffer,self.safe,lambda:self.result['releases'].append(row))
        return b
    def release(self):
        if self.buffers and not self.safe():raise RuntimeError('Unresolved lifecycle; retain process and buffers')
        while self.buffers:self.buffers[-1].freebuffer();self.buffers.pop()

def main():
    if not READY_FOR_EXECUTION:raise RuntimeError('Draft disabled: complete runtime capacity prerequisite failed')
    p=argparse.ArgumentParser();p.add_argument('manifest_sha');p.add_argument('mode',choices=('Layer','Text'));p.add_argument('prior_sha');p.add_argument('--enable-runtime-gate',action='store_true');a=p.parse_args()
    if not a.enable_runtime_gate:raise RuntimeError('Default disabled')
    out=EVIDENCE/a.mode
    if out.exists():raise RuntimeError('Immutable attempt exists; collect only')
    out.mkdir(parents=True,mode=0o700)
    r=dict(status='FAIL',gate_level=a.mode,build_id='0x4D333537',manifest_sha256=a.manifest_sha,prior_sha256=a.prior_sha,errors=[],passes=[],allocations=[],releases=[],memory=[],physical_launches=[],full_model=False,video=False,promoted=False,performance_pass=False,gate_return_code=1)
    base=owner=lock=None;old_build=None;phase=['package'];stop=threading.Event()
    def beat():
        while not stop.wait(30):print('M359_HEARTBEAT '+a.mode+' '+phase[0],flush=True)
    threading.Thread(target=beat,daemon=True).start()
    def mem(label):
        m={}
        for line in Path('/proc/meminfo').read_text(encoding='utf-8').splitlines():
            if line.split(':')[0] in ('CmaFree','MemAvailable'):m[line.split(':')[0]]=int(line.split()[1])*1024
        r['memory'].append(dict(label=label,**m,required_bytes=64<<20))
        if len(m)!=2 or min(m.values())<64<<20:raise MemoryError('Actual runtime reserve below64MiB: '+repr(m))
    def environment(target,digest,label):
        phase[0]='environment:'+label
        checked=subprocess.run([sys.executable,'-B',str(HERE/'m120_board_env_preflight.py'),'--candidate',str(target),'--expected-package-manifest-sha256',digest,'--result',str(out/(label+'_environment.json'))],timeout=90)
        if checked.returncode:raise RuntimeError('Fixed environment rejected')
    def zero(label):
        rt=owner.runtime;packet=(CAND/'build_packet.bin').read_bytes();golden=(CAND/'build_golden.bin').read_bytes()
        for b in rt.staged_buffers:b[:144]=0;b.sync_to_device()
        rt.input_buffer[:len(packet)]=np.frombuffer(packet,np.uint8);rt.input_buffer.sync_to_device()
        rt.output_buffer[:len(golden)]=0xa5;rt.output_buffer.sync_to_device()
        for reg,b in zip(base.REG_POINTERS,rt.staged_buffers):base.write_u64(rt.kernel,reg,base.physical_address(b))
        rt.kernel.write(base.REG_CONFIG,0x10201);mem('zero:'+label)
        owner.active=owner.ever=True;owner.complete=False
        r['physical_launches'].append(dict(label=label,kind='minimal-zero',input_bytes=len(packet),output_bytes=len(golden)))
        rt.dma.recvchannel.transfer(rt.output_buffer,nbytes=len(golden));rt.kernel.write(base.REG_AP_CTRL,1);rt.dma.sendchannel.transfer(rt.input_buffer,nbytes=len(packet))
        snap=base.wait_transaction(rt.kernel,rt.dma,10.0)
        if not safe_to_release(snap) or snap['ap_return']!=owner.build:raise RuntimeError('Minimal completion unsafe')
        owner.active=False;owner.complete=True
        rt.output_buffer.sync_from_device();assert bytes(memoryview(rt.output_buffer)[:len(golden)])==golden
        if hasattr(rt,'_programmed_weight_addresses'):rt._programmed_weight_addresses=None;rt._programmed_config=None
        r.setdefault('zero_proofs',[]).append(dict(label=label,build=hex(owner.build),output_bytes=len(golden),output_exact=True,snapshot=snap))
    try:
        verify_self(HERE,a.manifest_sha);verify_self(CAND,CAND_SHA)
        if os.geteuid()!=0:raise RuntimeError('Root required')
        prior_path=Path('/home/ubuntu/m358_candidate_capacity_01/load-memory.json') if a.mode=='Layer' else EVIDENCE/'Layer/BOARD_RESULT.json'
        assert sha256(prior_path)==a.prior_sha
        prior=json.loads(prior_path.read_text(encoding='utf-8'))
        if a.mode=='Layer':assert prior['status']=='PASS_M357_COMPLETE_RUNTIME_CAPACITY' and prior['memory_capacity_proven'] and not prior['unsafe_buffers_retained']
        else:assert prior['status']=='PASS_M359_LAYER' and prior['exact_numerical_pass'] and not prior['unsafe_buffers_retained']
        lock=os.open('/tmp/tellme_kv260_execution.lock',os.O_CREAT|os.O_RDWR,0o600);fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        r['initial_service']=service_stopped();boot=Path('/boot/firmware/boot.scr.uimg');boot_sha=sha256(boot);cmd=Path('/proc/cmdline').read_text(encoding='utf-8')
        closure=json.loads((HERE/'SOURCE_CLOSURE.json').read_text(encoding='utf-8'))
        for row in closure['files']:
            f=ROOT/row['path'];assert f.stat().st_size==row['bytes'] and sha256(f)==row['sha256']
        sys.path[:0]=[str(ROOT/d) for d in closure['module_dirs']]
        modules={name:importlib.import_module(name) for name in closure['modules']}
        for name,m in modules.items():assert Path(m.__file__).resolve()==(ROOT/closure['modules'][name]).resolve()
        base=modules['board_runtime'];old_build=base.BUILD_ID
        cls=modules['m238_prefill_runtime'].M238PrefillRuntime;m241=modules['m241_video_language_runtime']
        contract=json.loads((HERE/('LAYER_INPUT.json' if a.mode=='Layer' else 'TEXT_INPUT.json')).read_text(encoding='utf-8'))
        with np.load(STABLE/'auxiliary/m77_text_aux_fp16.npz',allow_pickle=False) as z:norms={k:z[k] for k in z.files}
        rows=np.asarray(norms['model.language_model.embed_tokens.weight'],np.float32)
        hidden=np.stack([rows[contract['selected_embedding_ids'].index(t)] for t in contract['prompt_token_ids']])
        if a.mode=='Layer':hidden=np.tile(hidden,(6,1))[:159].copy()
        assert tensor(hidden)==contract['input_tensor']
        layer_fn=bind(m241,(HERE/'frozen_one_layer.py').read_text(encoding='utf-8')) if a.mode=='Layer' else None
        direct=[]
        for variant in ('A','B'):
            phase[0]=variant+':constructor';target,digest=(STABLE,STABLE_SHA) if variant=='A' else (CAND,CAND_SHA)
            environment(target,digest,variant)
            owner=Lifetime(base,r);owner.build=0x4d395832 if variant=='A' else 0x4d333537;base.BUILD_ID=owner.build
            owner.runtime=cls.__new__(cls)
            import pynq
            original_allocate=pynq.allocate
            pynq.allocate=lambda *aa,**kw:owner.allocate(original_allocate,*aa,**kw)
            try:cls.__init__(owner.runtime,target/'overlay/m120_m89x2_t32.bit',ROOT/'external_assets/weights/language_fourport',ROOT/'external_assets/weights/lmhead_fourport',STABLE/'contracts/M126_LANGUAGE_RUNTIME_CONTRACT_RESULT.json',STABLE/'contracts/M126_LMHEAD_RUNTIME_CONTRACT_RESULT.json')
            finally:pynq.allocate=original_allocate
            rt=owner.runtime;assert len(owner.buffers)==7 and rt.maximum_weight_window_bytes==6963200
            mem(variant+':actual-runtime-loaded');zero(variant)
            for name in ('_launch_prepacked','_launch_once','_execute'):
                original=getattr(rt,name)
                def observe(chain,*aa,_original=original,_name=name,**kw):
                    mem(variant+':'+_name)
                    r['physical_launches'].append(dict(variant=variant,kind=_name,chain=chain['chain_index'],layer=chain.get('layer'),family=chain.get('family','lm_head'),input_bytes=chain['input_bytes'],output_bytes=chain['output_bytes']))
                    owner.active=owner.ever=True;owner.complete=False
                    answer=_original(chain,*aa,**kw)
                    snap=base.transaction_snapshot(rt.kernel,rt.dma)
                    if not safe_to_release(snap) or snap['ap_return']!=owner.build:raise RuntimeError('Original launch completion unsafe')
                    owner.active=False;owner.complete=True;return answer
                setattr(rt,name,observe)
            model=m241.M241VideoLanguageModel.__new__(m241.M241VideoLanguageModel);model.runtime=rt;model.norms=norms;model.grouped_attention_calls=0;model.grouped_attention_wall_ms=0.0;model.rope_cache_used=False
            families=[];family_original=model._family
            def family(layer,name,value):
                phase[0]=variant+':layer'+str(layer)+':'+name
                if name in ('q','qkv'):print('M359_LAYER '+phase[0],flush=True)
                outputs=family_original(layer,name,value)
                families.append(dict(layer=layer,family=name,input=tensor(value),output={k:tensor(v) for k,v in sorted(outputs.items())}));return outputs
            model._family=family
            if a.mode=='Layer':output,kv=layer_fn(model,hidden.copy());token=None
            else:token,output,kv=model.prefill(hidden.copy())
            evidence=rt.evidence();row=dict(variant=variant,token=token,output=tensor(output),keys=[tensor(v) for v in kv.keys],values=[tensor(v) for v in kv.values],families=families,attention_calls=model.grouped_attention_calls,evidence={k:evidence[k] for k in ('logical_calls','host_calls','scale_retry_count','pipeline_retry_launches','fused_nonfinite_detections','scale_attempts','stage_bytes','logical_expected_macros','expected_macros')})
            r['passes'].append(row);direct.append((output.copy(),[v.copy() for v in kv.keys+kv.values]))
            if a.mode=='Layer':assert row['attention_calls']==1 and row['evidence']['logical_calls']==25 and [x['family'] for x in families]==['q','kv','attention_out','gate_up','mlp_down']
            else:assert output.shape==(151936,) and len(kv.keys)==len(kv.values)==36 and token==17 and row['attention_calls']==36 and row['evidence']['logical_calls']==162
            assert row['evidence']['host_calls']==row['evidence']['logical_calls']+row['evidence']['scale_retry_count']
            owner.release();assert not owner.buffers
        arow,brow=r['passes'];arow=dict(arow);brow=dict(brow);arow.pop('variant');brow.pop('variant')
        assert arow==brow and exact(direct[0][0],direct[1][0]) and len(direct[0][1])==len(direct[1][1]) and all(exact(x,y) for x,y in zip(direct[0][1],direct[1][1]))
        r['exact_numerical_pass']=True;r['status']='PASS_M359_'+a.mode.upper()
        r['boot_unchanged']=sha256(boot)==boot_sha;r['cmdline_unchanged']=Path('/proc/cmdline').read_text(encoding='utf-8')==cmd
        assert r['boot_unchanged'] and r['cmdline_unchanged']
    except BaseException as exc:
        r['errors'].append(type(exc).__name__+': '+str(exc));r['traceback']=traceback.format_exc()
    finally:
        unsafe=owner is not None and bool(owner.buffers) and not owner.safe()
        if owner is not None and owner.runtime is not None and hasattr(owner.runtime,'kernel'):r['final_snapshot']=base.transaction_snapshot(owner.runtime.kernel,owner.runtime.dma)
        if not unsafe and owner is not None:
            try:owner.release()
            except BaseException as exc:unsafe=True;r['errors'].append('Release retained: '+str(exc))
        if not unsafe and base is not None:
            try:
                environment(STABLE,STABLE_SHA,'stable-restore')
                from pynq import Overlay,allocate
                restored=Overlay(str(STABLE/'overlay/m120_m89x2_t32.bit'),download=True)
                owner=Lifetime(base,r);owner.build=0x4d395832;base.BUILD_ID=owner.build
                class Minimal:pass
                rt=Minimal();rt.kernel=getattr(restored,KERNEL_NAME);rt.dma=getattr(restored,DMA_NAME);owner.runtime=rt
                rt.staged_buffers=[owner.allocate(allocate,(144,),dtype=np.uint8) for _ in range(4)]
                rt.input_buffer=owner.allocate(allocate,(2576,),dtype=np.uint8);rt.output_buffer=owner.allocate(allocate,(4096,),dtype=np.uint8)
                zero('stable-restore');owner.release();r['stable_restored']=True;r['stable_final_snapshot']=base.transaction_snapshot(rt.kernel,rt.dma)
            except BaseException as exc:
                r['errors'].append('Stable recovery failed: '+str(exc));unsafe=bool(owner.buffers) and not owner.safe()
            base.BUILD_ID=old_build
        r['unsafe_buffers_retained']=unsafe;r['safe_buffers_released']=not unsafe and len(r['allocations'])==len(r['releases'])
        if unsafe:r['status']='FAIL_UNSAFE_RETAINED'
        elif r['errors']:r['status']='FAIL'
        r['gate_return_code']=0 if r['status']=='PASS_M359_'+a.mode.upper() else 1
        print('M359_DEVICE_FINAL '+json.dumps(dict(rc=r['gate_return_code'],snapshot=r.get('final_snapshot'),stable_snapshot=r.get('stable_final_snapshot'),last_transaction=r['physical_launches'][-1:])),flush=True)
        write_json(out/'BOARD_RESULT.json',r);stop.set()
        from m359_export_result import emit_saved
        if unsafe:
            emit_saved(a.mode);print('M359_RETAIN_PROCESS_BUFFERS_OVERLAY_LOCK_DO_NOT_INTERRUPT',flush=True)
            while True:time.sleep(30)
        if lock is not None:os.close(lock)
    return r['gate_return_code']

if __name__=='__main__':raise SystemExit(main())
