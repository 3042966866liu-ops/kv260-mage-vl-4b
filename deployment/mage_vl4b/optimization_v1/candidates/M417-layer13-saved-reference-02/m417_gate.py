"""Saved-input exact MLP arithmetic oracle. No visual forward or FPGA fallback."""
import base64
import gc
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import sys
import time
import traceback
import weakref
from m416_gate import verify,sha,tensor,RELEASE,HERE
from m408_mlp_capture04 import Capture,SHAPES,compare
from m416_target13 import resolve_target,verify_matrices
from m406_vision_observer import backend_evidence,proc_snapshot
from m409_ftz_reference import SoftwareMLPBinding
from m409_torch_component import component
from test_m409_ftz_reference import actual_host

OUTPUT=Path('/home/ubuntu/m417_layer13_reference_02/RESULT.json')
CAPTURE=Path('/home/ubuntu/m416_layer13_capture_01')

def export():
    if os.geteuid()!=0:raise RuntimeError('Root saved-only export required')
    raw=OUTPUT.read_bytes();parts=[raw[i:i+900] for i in range(0,len(raw),900)]
    print('M417_RESULT_SHA256='+hashlib.sha256(raw).hexdigest(),flush=True)
    for i,part in enumerate(parts):
        print(f'M417_RESULT_CHUNK={i}/{len(parts)}:'+base64.b64encode(part).decode('ascii'),flush=True);time.sleep(.025)

def save_blob(name,blob,artifacts):
    if '/' in name or '\\' in name or len(blob)>(8<<20):raise RuntimeError('Artifact whitelist/budget')
    p=OUTPUT.parent/name
    with p.with_suffix(p.suffix+'.partial').open('xb') as f:f.write(blob);f.flush();os.fsync(f.fileno())
    os.replace(p.with_suffix(p.suffix+'.partial'),p)
    artifacts.append(dict(path=name,bytes=len(blob),sha256=sha(p)))
    if sum(r['bytes'] for r in artifacts)>(64<<20):raise RuntimeError('Total reference artifact budget')

def load_capture(expected,np):
    if CAPTURE.is_symlink() or sha(CAPTURE/'CAPTURE_MANIFEST.json')!=expected['capture_manifest']['sha256']:
        raise RuntimeError('Exact retained capture manifest differs')
    cm=json.loads((CAPTURE/'CAPTURE_MANIFEST.json').read_bytes())
    if cm['files']!=expected['capture_manifest']['files'] or len(cm['files'])!=6:raise RuntimeError('Capture list differs')
    values={}
    for row in cm['files']:
        name=row['path'];key=name.removesuffix('.npy')
        if key not in SHAPES or name!=key+'.npy':raise RuntimeError('Capture whitelist differs')
        p=CAPTURE/name
        if p.is_symlink() or p.stat().st_size!=row['file_bytes'] or sha(p)!=row['file_sha256']:raise RuntimeError('Capture file differs')
        x=np.load(p,allow_pickle=False)
        if tensor(x)!=row['tensor'] or x.dtype!=np.float32 or tuple(x.shape)!=SHAPES[key]:raise RuntimeError('Capture tensor differs')
        values[key]=x
    return values

def main():
    if sys.argv[1:]==['Collect']:export();return 0
    if len(sys.argv)!=3 or sys.argv[2]!='--enable-saved-MLP-reference':raise RuntimeError('Default-off exact software reference')
    if os.geteuid()!=0:raise RuntimeError('Same-terminal root required')
    if OUTPUT.parent.exists():raise RuntimeError('Original result directory exists; Collect only')
    OUTPUT.parent.mkdir();started=time.monotonic()
    result=dict(status='FAIL_M417_SAVED_MLP_EXACT_SOFTWARE_REFERENCE',gate_return_code=1,errors=[],
        manifest_sha256=sys.argv[1],gate_level='PS-only-saved-input-exact-MLP-FTZ-reference',selected_layer=13,
        overlay_loaded=False,dma_allocations=0,fpga_transactions=0,visual_forward_calls=0,language_forward_calls=0,
        local_mlp_forward_calls=0,semantic_quality_proven=False,PL_hardware_proven=False,
        performance_pass=False,formal_promotion_allowed=False,bindings_restored=False,visual_owner_closed=False)
    runtime=layer=mlp=replay=candidate=binding=None
    artifacts=[]
    try:
        ids=verify(sys.argv[1]);result['source_identities_verified']=len(ids['files'])
        expected=json.loads((HERE/'M416_CAPTURE_EXPECTED.json').read_bytes())
        from frozen_video_identity import module_paths,verify_m277_release_subset
        result['m277_release_subset']=verify_m277_release_subset(RELEASE/'deployment/mage_vl4b/m277_m276_fixed_window_board_candidate')
        sys.path[:0]=[str(p) for p in module_paths()]
        spec=importlib.util.spec_from_file_location('release_preflight',RELEASE/'scripts/preflight.py')
        preflight=importlib.util.module_from_spec(spec);spec.loader.exec_module(preflight)
        checked=preflight.inspect(json.loads((RELEASE/'configs/deployment.example.json').read_bytes()),port_check=True)
        result['release_preflight']={k:checked[k] for k in ('status','missing','hash_or_identity_mismatch','port_free')}
        if checked['status']!='READY_FOR_BOARD_PREFLIGHT':raise RuntimeError('Original full 35-asset preflight rejected')
        import numpy as np
        import torch
        from m273_latest_vision_runtime import M273LatestPSVisionRuntime
        from m207_ps_vision_runtime import M207FP32GemmW4Linear
        from m206_ps_vision_runtime import M206ProgressLayer
        from ps_vision_runtime import M196PrecisionBoundary
        result['backend_before']=backend_evidence(torch)
        host,initial=actual_host(RELEASE)
        from m414_entry import run_component
        result['component'],result['component_isolation']=run_component(RELEASE,OUTPUT.parent,HERE/'m417_component_entry.py')
        print('M417_REAL_TORCH_COMPONENT_PASS',flush=True)
        values=load_capture(expected,np);result['capture_manifest_sha256']=expected['capture_manifest']['sha256']
        result['capture_source_raw_sha256']=expected['raw_sha256'];result['capture_tensors']={k:tensor(v) for k,v in values.items()}
        available=int(next(l.split()[1] for l in Path('/proc/meminfo').read_text().splitlines() if l.startswith('MemAvailable:')))*1024
        if available<(1<<30)+(256<<20)+(64<<20):raise RuntimeError('PS constructor/reference temporary memory budget insufficient')
        result['memory_before_constructor']=proc_snapshot()
        base=RELEASE/'deployment/mage_vl4b/m181_m120_video_board_candidate'
        runtime=M273LatestPSVisionRuntime(base/'ps_vision_payload',base/'vision_layout',base/'auxiliary/M90_VISION_RAW_AUX_MANIFEST.json')
        owner=weakref.ref(runtime)
        layer,result['target_resolution']=resolve_target(runtime.vision,M206ProgressLayer,M196PrecisionBoundary,torch)
        result['target_matrices']=verify_matrices(layer,M207FP32GemmW4Linear,torch)
        if result['target_matrices']!=expected['target_matrices'] or result['target_resolution']!=expected['target_resolution']:raise RuntimeError('Frozen constructor target differs')
        mlp=layer.mlp
        layout_path=base/'vision_layout/SIXPORT_LAYOUT_MANIFEST.json'
        layout=json.loads(layout_path.read_bytes())
        chains=json.loads((HERE/'MLP_CHAINS.json').read_bytes())['chains']
        selected={k:next(c for c in chains if c['module']==f'model.visual.encoder.layers.13.mlp.{k}') for k in ('fc1','fc2')}
        from m407_mlp_contract import chain_for
        entries={e['module']:e for e in layout['modules']}
        windows={};result['windows']={}
        for part,c in selected.items():
            if chain_for(entries[c['module']],c['chain_index'])!=c:raise RuntimeError('Actual layout chain differs')
            parts=[];rows=[]
            for row in layout['files']:
                p=base/'vision_layout'/row['path']
                if p.stat().st_size!=row['bytes'] or sha(p)!=row['sha256']:raise RuntimeError('Full W4 shard identity differs')
                with p.open('rb') as f:f.seek(c['stage_base_words']*16);raw=f.read(c['stage_bytes_per_shard'])
                if len(raw)!=c['stage_bytes_per_shard']:raise RuntimeError('Weight staging short read')
                parts.append(raw);rows.append(dict(path=row['path'],offset=c['stage_base_words']*16,bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest()))
            windows[part]=parts;result['windows'][part]=rows
        with torch.inference_mode():
            x=torch.from_numpy(values['input']).unsqueeze(0)
            result['local_mlp_forward_calls']+=1
            with Capture(mlp) as replay:mlp(x)
            replay.require_complete()
            if any(not np.array_equal(values[k].view(np.uint32),v.view(np.uint32)) for k,v in replay.values.items()):raise RuntimeError('Retained CPU replay differs')
            result['original_replay_bit_exact']=True
            def sink(part,start,shift,packet,raw):
                save_blob(f'{part}_{start:03d}_shift{shift}.packet',packet,artifacts)
                save_blob(f'{part}_{start:03d}_shift{shift}.raw',raw,artifacts)
                print(f'M417_REFERENCE_BATCH {part} start={start} selected_shift={shift} elapsed={time.monotonic()-started:.3f}',flush=True)
                if time.monotonic()-started>900:raise RuntimeError('Reference budget expired; no automatic rerun')
            binding=SoftwareMLPBinding(torch,mlp,selected,windows,initial,host.pack_chain_input,host.parse_chain_output,raw_sink=sink)
            result['local_mlp_forward_calls']+=1
            with Capture(mlp) as candidate:
                with binding:mlp(x)
            candidate.require_complete()
            result['reference_batches']=binding.batches
            result['quality_metrics'],result['local_exact_arithmetic_screen_pass']=compare(values,candidate.values)
            result['candidate_tensors']={k:tensor(v) for k,v in candidate.values.items()}
            # Preserve actual precision boundary separately; no complete visual/semantic claim.
            ref=(torch.from_numpy(values['residual']+values['output']).to(torch.bfloat16).float().numpy())
            alt=(torch.from_numpy(values['residual']+candidate.values['output']).to(torch.bfloat16).float().numpy())
            from m407_mlp_contract import metrics,local_screen
            result['boundary_residual_bf16']=metrics(ref,alt)
            result['local_exact_arithmetic_screen_pass'] &= local_screen(result['boundary_residual_bf16'])
            import io
            for key,arr in candidate.values.items():
                buf=io.BytesIO();np.save(buf,arr,allow_pickle=False);save_blob(key+'.npy',buf.getvalue(),artifacts)
            result['artifacts']=artifacts
        result['logical_reference_calls']=sum(len(v) for v in binding.batches.values())
        result['physical_reference_attempts']=sum(b['physical_reference_attempts'] for v in binding.batches.values() for b in v)
        if result['logical_reference_calls']!=26:raise RuntimeError('Complete MLP logical reference count differs')
        result['bindings_restored']=all(o.restored for o in (binding,replay,candidate))
        result['backend_after']=backend_evidence(torch)
        if result['backend_before']!=result['backend_after']:raise RuntimeError('Backend settings changed')
        result['memory_before_release']=proc_snapshot()
        del x,sink,ref,alt
        binding=replay=candidate=mlp=layer=None
        runtime.close();runtime=None;gc.collect()
        result['visual_owner_closed']=owner() is None
        result['memory_after_release']=proc_snapshot()
        result['no_pynq_import']=not any(n=='pynq' or n.startswith('pynq.') for n in sys.modules)
        if not result['bindings_restored'] or not result['visual_owner_closed'] or not result['no_pynq_import']:raise RuntimeError('PS lifecycle/forbidden import differs')
        if not result['local_exact_arithmetic_screen_pass']:raise RuntimeError('Exact PL arithmetic local screen rejected; stop before hardware')
        result.update(status='PASS_M417_SAVED_MLP_EXACT_SOFTWARE_REFERENCE',gate_return_code=0)
    except BaseException as error:
        result['errors'].append(dict(type=type(error).__name__,message=str(error),traceback=traceback.format_exc()))
    finally:
        for obj in (replay,candidate):
            if obj is not None and obj.handles:obj.__exit__(None,None,None)
        if binding is not None and binding.previous:binding.__exit__(None,None,None)
        result['bindings_restored']=all(obj.restored for obj in (replay,candidate,binding) if obj is not None)
        replay=candidate=binding=mlp=layer=None
        if runtime is not None:runtime.close();runtime=None;gc.collect();result['failure_PS_owner_close_called']=True
        result['elapsed_s_diagnostic_not_performance']=time.monotonic()-started
        blob=(json.dumps(result,indent=2,allow_nan=False)+'\n').encode('utf-8')
        with OUTPUT.with_suffix('.partial').open('xb') as f:f.write(blob);f.flush();os.fsync(f.fileno())
        os.replace(OUTPUT.with_suffix('.partial'),OUTPUT)
    return result['gate_return_code']
if __name__=='__main__':raise SystemExit(main())
