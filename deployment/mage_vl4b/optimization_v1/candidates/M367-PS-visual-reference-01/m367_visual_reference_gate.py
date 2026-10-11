"""Supplement only missing exact PS visual reference; no PYNQ/PL execution."""
import argparse
import fcntl
import hashlib
import importlib.abc
import importlib.util
import json
import os
from pathlib import Path
import sys
import threading
import time
import traceback
sys.dont_write_bytecode=True
import numpy as np
from measurement import sha256,write_json
from frozen_video_identity import module_paths,verify_m277_release_subset,FRAMES,STACK_SHA,ADDON,RELEASE
from m341_build_id_gate import verify_self,service_stopped,STABLE
from memory_lifecycle import memory_snapshot

HERE=Path(__file__).resolve().parent
EVIDENCE=Path('/home/ubuntu/m367_visual_reference_01')
MIB=1<<20
LIMIT=768*MIB
MARGIN=64*MIB


class DenyPynq(importlib.abc.MetaPathFinder):
    def find_spec(self,fullname,path=None,target=None):
        if fullname.split('.')[0]=='pynq':raise RuntimeError('PS reference forbids PYNQ import')
        return None


class NoBoard:
    def __getattr__(self,name):raise RuntimeError('PS reference forbids board runtime access: '+name)


def tensor(value):
    value=np.ascontiguousarray(value)
    if not np.isfinite(value).all():raise FloatingPointError('Nonfinite PS reference')
    return dict(shape=list(value.shape),dtype=str(value.dtype),bytes=int(value.nbytes),sha256=hashlib.sha256(value.tobytes()).hexdigest())


def assess(memory,baseline):
    available=memory['system_bytes']['MemAvailable'];rss=memory['process_bytes']['VmRSS']
    if type(available) is not int or type(rss) is not int or min(available,rss,baseline)<0:raise RuntimeError('Invalid PS memory')
    growth=max(0,rss-baseline)
    if growth>LIMIT:raise MemoryError('Visual observed PS growth exceeded768MiB')
    required=max(0,LIMIT-growth)+MARGIN
    if available<required:raise MemoryError('Visual remaining PS budget plus64MiB unavailable')
    return dict(observed_growth_bytes=growth,required_available_bytes=required)


def main():
    parser=argparse.ArgumentParser();parser.add_argument('manifest_sha');parser.add_argument('--enable-ps-reference',action='store_true');args=parser.parse_args()
    if not args.enable_ps_reference:raise RuntimeError('PS reference disabled by default')
    if EVIDENCE.exists():raise RuntimeError('Immutable result exists; Collect only')
    EVIDENCE.mkdir(mode=0o700,parents=True)
    r=dict(status='FAIL_PS_VISUAL_REFERENCE',gate_level='missing-PS-visual-reference-only',build_id='0x4D395832',errors=[],gate_return_code=1,overlay_loads=0,pynq_allocate_calls=0,fpga_transactions=0,language_forward_calls=0,vision_forward_calls=0,performance_pass=False,promoted=False,stage_memory=[],progress=[],extra_cma_budget_bytes=0,ps_growth_limit_bytes=LIMIT,ps_available_margin_bytes=MARGIN)
    started=time.monotonic();stop=threading.Event();observer=None;lock=None;vision=language=None;baseline=None;latched=[];extrema={};samples=[0]
    blocker=DenyPynq();sys.meta_path.insert(0,blocker)
    def point(label,check=False):
        if latched:raise RuntimeError('Latched PS stop: '+latched[0])
        m=memory_snapshot();decision=assess(m,baseline) if check else None
        r['stage_memory'].append(dict(label=label,elapsed_s=time.monotonic()-started,memory=m,decision=decision))
        print('M367_STAGE '+label,flush=True)
        return m
    def progress(name,payload):
        r['progress'].append(dict(event=name,payload=payload))
        point(name+':'+str(payload.get('index')),True)
    heartbeat_stop=threading.Event()
    def heartbeat():
        while not heartbeat_stop.wait(30):print('M367_HEARTBEAT elapsed_s='+str(round(time.monotonic()-started,1)),flush=True)
    heartbeat_thread=threading.Thread(target=heartbeat,name='m367-heartbeat',daemon=True);heartbeat_thread.start()
    try:
        verify_self(HERE,args.manifest_sha);r['manifest_sha256']=args.manifest_sha
        if os.geteuid()!=0:raise RuntimeError('Same-terminal root required')
        r['platform']=dict(euid=os.geteuid(),uname=list(os.uname()))
        prerequisite=json.loads((HERE/'TEXT_PREREQUISITE.json').read_text(encoding='utf-8'))
        if prerequisite['status']!='PASS_INDEPENDENT_FIXED_TEXT_CAPACITY_AND_NUMERICS' or prerequisite['raw_sha256']!='b7c2532715f6b90201c9c092e83bcf5245ad7e6ad0b3e5d9bdace60618406ebb':raise RuntimeError('Fixed-text prerequisite differs')
        r['stable_service']=service_stopped()
        lock=os.open('/tmp/tellme_kv260_execution.lock',os.O_CREAT|os.O_RDWR,0o600);fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        boot=Path('/boot/firmware/boot.scr.uimg');boot_sha=sha256(boot);cmdline=Path('/proc/cmdline').read_text(encoding='utf-8')
        point('before-source-imports')
        closure=json.loads((HERE/'SOURCE_CLOSURE.json').read_text(encoding='utf-8'))
        for row in closure['files']:
            p=RELEASE/row['path']
            if p.stat().st_size!=row['bytes'] or sha256(p)!=row['sha256']:raise RuntimeError('Frozen source drift: '+row['path'])
        if sha256(RELEASE/'INSTALL_PACKAGE_MANIFEST.json')!='fc69e69c0396e29e06d4852b06f680b2365cb31fdd1ffb036b0f85037b6f6d6e' or sha256(ADDON/'PACKAGE_MANIFEST.json')!='4eb8c6c95752208b5848e0e52efb2a713f98487f5b88518dbd5b58801d236568':raise RuntimeError('Release/addon manifest drift')
        r['release_subset']=verify_m277_release_subset(RELEASE/'deployment/mage_vl4b/m277_m276_fixed_window_board_candidate')
        sys.path[:0]=[str(p) for p in module_paths()]
        import m276_m254_video_server
        import m276_video_runtime
        import m273_latest_vision_runtime
        import m241_video_language_runtime
        import video_server
        for name,relative in closure['modules'].items():
            if name in sys.modules and Path(sys.modules[name].__file__).resolve()!=(RELEASE/relative).resolve():raise RuntimeError('Actual import path drift: '+name)
        spec=importlib.util.spec_from_file_location('release_preflight',RELEASE/'scripts/preflight.py');preflight=importlib.util.module_from_spec(spec);spec.loader.exec_module(preflight)
        checked=preflight.inspect(json.loads((RELEASE/'configs/deployment.example.json').read_text(encoding='utf-8')),port_check=True)
        if checked['status']!='READY_FOR_BOARD_PREFLIGHT':raise RuntimeError('Original complete asset preflight rejected')
        r['asset_preflight']={k:checked[k] for k in ('status','missing','hash_or_identity_mismatch','port_free')}
        point('after-original-asset-preflight')
        d=RELEASE/'deployment/mage_vl4b'
        config=video_server.make_config(d/'m181_m120_video_board_candidate',STABLE,RELEASE/'external_assets/weights',RELEASE/'tmp/m223_realtime/m223_realtime_delta/M223_PREDECESSOR_SUMMARY.json')
        frames=[]
        for name,digest in FRAMES.items():
            p=ADDON/'fixtures'/name
            if sha256(p)!=digest:raise RuntimeError('Frame identity differs')
            frames.append(np.load(p,allow_pickle=False))
        frames=np.ascontiguousarray(np.stack(frames))
        if frames.shape!=(4,448,448,3) or frames.dtype!=np.uint8 or hashlib.sha256(frames.tobytes()).hexdigest()!=STACK_SHA:raise RuntimeError('Ordered frame tensor differs')
        r['frames_sha256']=STACK_SHA
        point('before-original-PS-constructors')
        vision=m273_latest_vision_runtime.M273LatestPSVisionRuntime(config['model_code'],config['vision_layout'],config['raw_vision_manifest'],progress_callback=progress)
        import torch
        r['thread_environment']=dict(torch_num_threads=torch.get_num_threads(),torch_interop_threads=torch.get_num_interop_threads(),environment={k:os.environ.get(k) for k in ('OMP_NUM_THREADS','MKL_NUM_THREADS','OPENBLAS_NUM_THREADS')})
        language=m241_video_language_runtime.M241VideoLanguageModel(NoBoard(),config['auxiliary'])
        baseline=point('after-original-PS-constructors')['process_bytes']['VmRSS']
        point('PS-visual-admission',True)
        def sample():
            while not stop.wait(.02):
                try:
                    m=memory_snapshot();assess(m,baseline);samples[0]+=1
                    values=dict(max_rss=m['process_bytes']['VmRSS'],max_hwm=m['process_bytes']['VmHWM'],min_available=m['system_bytes']['MemAvailable'],min_cma=m['system_bytes']['CmaFree'])
                    for k,v in values.items():extrema[k]=v if k not in extrema else (max(extrema[k],v) if k.startswith('max') else min(extrema[k],v))
                    if time.monotonic()-started>420:raise RuntimeError('PS reference soft budget exceeded420s')
                except BaseException as exc:latched.append(type(exc).__name__+': '+str(exc));return
        observer=threading.Thread(target=sample,name='m367-PS-memory-observer',daemon=True);observer.start()
        tensors=m276_video_runtime.preprocess(np.ascontiguousarray(frames[-1:]))
        r['preprocessed']={k:tensor(v) for k,v in sorted(tensors.items())}
        point('before-original-visual-forward',True);r['vision_forward_calls']=1
        visual=vision(tensors['pixel_values'],tensors['image_grid_thw'],tensors['patch_positions'])
        point('after-original-visual-forward',True)
        r['visual_features']=tensor(visual);r['decoder']=vision.decoder_evidence()
        ids=m276_video_runtime.tokenize(config['tokenizer'],m276_video_runtime.M276_KNIFE_PROMPT,3.0)
        hidden=m276_video_runtime.latest_input_embeddings(language,ids,visual)
        r['prompt_token_ids']=ids;r['video_input']=tensor(hidden)
        expected=json.loads((HERE/'VIDEO_EXPECTED.json').read_text(encoding='utf-8'))
        if r['video_input']!=expected['baseline']['input'] or len(ids)!=159 or r['visual_features']['shape']!=[98,2560]:raise RuntimeError('PS composition differs from saved actual stable159 video input')
        dec=r['decoder']
        if dec['cache_entries']!=26 or dec['cache_bytes']!=66699264 or dec['cache_misses']!=26 or not dec['cache_within_budget']:raise RuntimeError('Original visual cache contract differs')
        point('after-original159-embedding-composition',True)
        r['boot_unchanged']=sha256(boot)==boot_sha;r['cmdline_unchanged']=Path('/proc/cmdline').read_text(encoding='utf-8')==cmdline
        if not r['boot_unchanged'] or not r['cmdline_unchanged'] or 'pynq' in sys.modules:raise RuntimeError('Protected identity/PYNQ boundary differs')
        r['status']='PASS_MISSING_PS_VISUAL_REFERENCE';r['gate_return_code']=0
    except BaseException as exc:
        r['errors'].append(type(exc).__name__+': '+str(exc));r['traceback']=traceback.format_exc()
    finally:
        stop.set()
        if observer:
            observer.join(2)
            if observer.is_alive():r['errors'].append('PS observer did not join');r['status']='FAIL_PS_VISUAL_REFERENCE';r['gate_return_code']=1
        r['sampled_memory']=dict(sample_interval_s=.02,sample_count=samples[0],extrema=extrema,stop_reason=latched,exact_native_peak_proven=False)
        try:
            if vision is not None:
                for mapping in vision.store.maps:mapping.close()
                for handle in vision.store.handles:handle.close()
                r['vision_store_maps_and_handles_closed']=True
            if language is not None:language.embedding._mmap.close();language._norm_archive.close();r['language_aux_maps_and_archive_closed']=True
        except BaseException as exc:
            r['errors'].append('PS resource close: '+type(exc).__name__+': '+str(exc));r['status']='FAIL_PS_VISUAL_REFERENCE';r['gate_return_code']=1
        heartbeat_stop.set();heartbeat_thread.join(2)
        if heartbeat_thread.is_alive():r['errors'].append('Heartbeat did not join');r['status']='FAIL_PS_VISUAL_REFERENCE';r['gate_return_code']=1
        r['elapsed_s_diagnostic_not_performance']=time.monotonic()-started
        r['no_PL_boundary_enforced']=bool('pynq' not in sys.modules)
        r['next_step']='Only use this missing visual reference plus oldM345 language outputs for independent video gate; no performance unlocked.'
        write_json(EVIDENCE/'RESULT.json',r)
        print('M367_RESULT_SAVED status='+r['status']+' sha256='+sha256(EVIDENCE/'RESULT.json'),flush=True)
        if lock is not None:fcntl.flock(lock,fcntl.LOCK_UN);os.close(lock)
        sys.meta_path.remove(blocker)
    raise SystemExit(r['gate_return_code'])


if __name__=='__main__':main()
