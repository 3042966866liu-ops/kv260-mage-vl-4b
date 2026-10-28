"""Exact crop, original PS-path inputs and mean-residual R1; training only."""
import sys,traceback
from pathlib import Path
sys.dont_write_bytecode=True
sys.path.insert(0,str(Path(__file__).resolve().parent))
from common import *

class PrefixComplete(Exception):pass

def main():
    p=verify();assert not FIT.exists();FIT.mkdir();start=time.monotonic()
    v=dict(status='FAIL_PS_V236_3072_TRAINING_FIT',original_rc=1,protocol_sha256=sha(PREP/'RESULT.json'),
        board_commands=0,gradient_steps=0,new_quantization=False,heldout_opened=0,local=[],requests=[],
        full_visual_forwards=0,prefix_forwards=0,native_A53=False)
    runtime=None;hooks=[]
    try:
        from generate_flap522 import FrozenCheckpoint
        torch,runtime,linear,preprocess=setup()
        cp=FrozenCheckpoint(read(OPT/'contracts/config.json'))
        crops={};captures={};original_modules={}
        for selected in p['selected']:
            i=selected['index'];module=inner(runtime,i).mlp;original_modules[i]=(module.fc1,module.fc2)
            keep=np.array(selected['kept_original_G64_groups'],np.int64);ids=(keep[:,None]*64+np.arange(64)).reshape(-1)
            original={}
            for part in ('fc1','fc2'):
                (c,s),bits=cp.packed(selected['module']+'.'+part);assert bits==4
                actual=getattr(module,part);d=(c.astype(np.float32)*s.astype(np.float32)[...,None]).reshape(len(c),-1)
                assert runtime.store.decode(actual.name).tobytes()==d.tobytes()
                original[part+'_codes']=c;original[part+'_scales']=s
                expected=cp.bias(selected['module']+'.'+part)
                assert expected.tobytes()==actual.bias.detach().float().numpy().tobytes()
                original['bias1' if part=='fc1' else 'bias2']=expected
            z=dict(fc1_codes=original['fc1_codes'][ids].copy(),fc1_scales=original['fc1_scales'][ids].copy(),
                fc2_codes=original['fc2_codes'][:,keep].copy(),fc2_scales=original['fc2_scales'][:,keep].copy(),
                bias1=original['bias1'][ids].copy(),bias2=original['bias2'].copy(),kept_original_groups=keep)
            assert z['fc1_codes'].shape==(3072,16,64) and z['fc2_codes'].shape==(1024,48,64)
            for name in ('fc1_codes','fc1_scales','fc2_codes','fc2_scales','bias1','bias2'):
                expected=(original[name][ids] if name.startswith('fc1') or name=='bias1' else
                    original[name][:,keep] if name.startswith('fc2') else original[name])
                assert z[name].dtype==expected.dtype and z[name].tobytes()==expected.tobytes(),name
            file=FIT/'codes'/(selected['key']+'.npz');file.parent.mkdir(parents=True,exist_ok=True)
            with file.open('xb') as stream:np.savez(stream,**z)
            crops[i]=z
            hooks.append(module.register_forward_pre_hook(lambda m,a,i=i:captures.__setitem__(i,a[0].detach().float().numpy().copy())))
        def stop(m,a,y):raise PrefixComplete()
        hooks.append(runtime.vision.encoder.layers[6].register_forward_hook(stop))
        rows=[r for r in p['requests'] if r['id'] in p['training_ids']]
        assert len(rows)==8 and len({r['source_group'] for r in rows})==4
        all_ref={i:[] for i in crops};all_cut={i:[] for i in crops}
        versions=[(name,x._version,tuple(x.shape),x.data_ptr()) for name,x in runtime.vision.named_parameters()]
        for request in rows:
            assert time.monotonic()-start<p['budgets']['fit_seconds'];captures.clear()
            arrays=inputs(torch,preprocess,request)
            with torch.inference_mode():
                try:runtime(**arrays)
                except PrefixComplete:pass
                else:raise AssertionError('Prefix did not stop before layer7')
            assert set(captures)=={2,3,6};v['prefix_forwards']+=1
            v['requests'].append(dict(id=request['id'],source_group=request['source_group'],role='training_only',captured_layers=[2,3,6]))
            for i,z in crops.items():
                x=captures[i];assert x.shape==(1,392,1024) and x.dtype==np.float32 and np.isfinite(x).all()
                module=inner(runtime,i).mlp
                # Capture hook must not fire during local output evaluation.
                # Use the original forward directly: identical original GELU and Linears.
                with torch.inference_mode():reference=module.forward(torch.from_numpy(x.copy())).float().numpy().copy()
                mlp,old=replace_PS(torch,runtime,linear,i,z)
                try:
                    with torch.inference_mode():cut=mlp.forward(torch.from_numpy(x.copy())).float().numpy().copy()
                finally:mlp.fc1,mlp.fc2=old
                assert module.fc1 is original_modules[i][0] and module.fc2 is original_modules[i][1]
                assert reference.shape==cut.shape==(1,392,1024) and np.isfinite(cut).all()
                root=FIT/request['id']/('vision_'+str(i).zfill(2))
                array(root/'input_FP32.npy',x[0]);array(root/'original_PS_FP32.npy',reference[0]);array(root/'cropped_PS_FP32.npy',cut[0])
                all_ref[i].append(reference[0]);all_cut[i].append(cut[0])
            assert versions==[(name,x._version,tuple(x.shape),x.data_ptr()) for name,x in runtime.vision.named_parameters()]
            print('PS_V236_TRAINING',request['id'],'3 same-input full/crop PS MLP pairs',flush=True)
        for selected in p['selected']:
            i=selected['index'];ref=np.concatenate(all_ref[i]);cut=np.concatenate(all_cut[i])
            r1=np.mean(ref.astype(np.float64)-cut.astype(np.float64),axis=0).astype(np.float32)
            assert r1.shape==(1024,) and np.isfinite(r1).all()
            file=FIT/'R1'/(selected['key']+'_FP32.bin');file.parent.mkdir(parents=True,exist_ok=True);file.open('xb').write(r1.tobytes())
            compensated=np.add(cut,r1,dtype=np.float32)
            v['local'].append(dict(key=selected['key'],width=3072,input_rows=len(ref),original_PS_path=True,
                R0=metric(cut,ref),R1=metric(compensated,ref),R1_sha256=sha(file),R1_FP32_sha256=digest(r1),
                R1_FP64_residual_mean_cast_once=True))
        assert len(v['requests'])==8 and v['prefix_forwards']==8
        v.update(status='PASS_PS_V236_3072_EXACT_CROP_TRAINING_R1_NOT_COMBINED_QUALITY',original_rc=0,
            source_sections=cp.sections,original_GELU_unchanged=True,original_PS_FP32_boundary_unchanged=True,
            parent22_unchanged=True,full_visual_quality_pass=False,performance_pass=False)
    except BaseException:v['traceback']=traceback.format_exc()
    finally:
        for h in hooks:h.remove()
        if runtime is not None:runtime.close()
        v['elapsed_s']=time.monotonic()-start;v['files']=files(FIT);save(FIT/'RESULT.json',v)
        print(v['status'],v.get('traceback',''),flush=True)
    return v['original_rc']
if __name__=='__main__':raise SystemExit(main())
