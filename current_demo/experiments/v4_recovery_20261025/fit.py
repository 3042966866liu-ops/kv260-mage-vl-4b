"""M536 training-only input capture, output-contribution groups and recovery."""
import sys,traceback,math,gc
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
from common_v4 import *

def main():
    p=verify();assert not FIT.exists();FIT.mkdir();started=time.monotonic()
    v=dict(status='FAIL_M536_V4_RECOVERY_FIT',primary_rc=1,board_commands=0,heldout_opened=False,
        prefix_captures=[],full_model_forwards=0,training_steps=0,conditional_fc2_started=False,variants=[])
    runtime=None;selector=None;subset=None
    try:
        torch,runtime,selector,subset,preprocess=cpu_setup()
        assert torch.cuda.is_available() and torch.cuda.mem_get_info()[0]>=2<<30
        v['GPU']=dict(name=torch.cuda.get_device_name(0),free_bytes=torch.cuda.mem_get_info()[0])
        mlp=core(subset.original[4]).mlp
        mlp_versions=[(q,q._version,q.data_ptr(),tuple(q.shape)) for q in mlp.parameters()]
        versions=[(id(q),q._version,q.data_ptr(),tuple(q.shape)) for q in runtime.vision.parameters()]
        sys.path.insert(0,str(ROOT/'experiments/speed_target_30s_20261020'))
        from generate_flap522 import FrozenCheckpoint
        cp=FrozenCheckpoint(read(OPT/'contracts/config.json'))
        module='model.visual.encoder.layers.4.mlp'
        (c1,s1),bits1=cp.packed(module+'.fc1');(c2,s2),bits2=cp.packed(module+'.fc2')
        assert bits1==bits2==4
        bias1,bias2=cp.bias(module+'.fc1'),cp.bias(module+'.fc2')
        w1=(c1.astype(np.float32)*s1.astype(np.float32)[...,None]).reshape(4096,1024)
        w2=(c2.astype(np.float32)*s2.astype(np.float32)[...,None]).reshape(1024,4096)
        assert np.array_equal(w1,mlp.fc1.store.decode(mlp.fc1.name)) and np.array_equal(w2,mlp.fc2.store.decode(mlp.fc2.name))
        assert np.array_equal(bias1,mlp.fc1.bias.numpy()) and np.array_equal(bias2,mlp.fc2.bias.numpy())
        data={};v['source_sections']=cp.sections
        def process(request,frame,kind):
            assert time.monotonic()-started<p['budgets']['fit_seconds']
            selector.begin_request();subset.bypass_calls.clear()
            x=prefix_input(torch,runtime,mlp,preprocess,frame)
            assert selector.calls=={2:1,3:1} and subset.bypass_calls=={0:1}
            with torch.inference_mode():
                h=mlp.activation_fn(mlp.fc1(x));y=mlp.forward(x)
                replay=torch.nn.functional.linear(h,torch.from_numpy(w2),mlp.fc2.bias)
            assert torch.equal(y,replay)
            row=dict(x=x.numpy()[0].copy(),h=h.numpy()[0].copy(),y=y.numpy()[0].copy())
            file=FIT/'captures'/(request['id']+'_'+kind+'.npz');npz(file,**row)
            v['prefix_captures'].append(dict(id=request['id'],kind=kind,source_group=request['source_group'],
                file=rel(file),sha256=sha(file),input_sha256=digest(row['x']),teacher_output_sha256=digest(row['y']),
                complete_model=False,original_V4_teacher=True,student_prefix_uses_old_V2_V3_R1=True))
            print('M536_CAPTURE',request['id'],kind,flush=True);return row
        for request in p['training_requests']:
            file=ROOT/request['frames'];assert sha(file)==request['frames_sha256']
            frames=np.load(file,allow_pickle=False);frame=frames[request['timestamp_index']]
            data[request['id']]=dict(clean=process(request,frame,'clean'))
            if request['id'] in p['hard_training']:
                item=p['hard_training'][request['id']];f=ROOT/item['student_file'];assert sha(f)==item['student_sha256']
                data[request['id']]['hard']=process(request,np.load(f,allow_pickle=False),'hard')
        assert len(v['prefix_captures'])==12
        assert versions==[(id(q),q._version,q.data_ptr(),tuple(q.shape)) for q in runtime.vision.parameters()]
        # No downstream visual/PL/language evaluation occurred in capture.
        subset.close();selector.close();runtime.close();runtime=None;subset=None;selector=None
        clean=[data[r['id']]['clean'] for r in p['training_requests']]
        xt_saved=RUNS/'M535-V4-local-screen-board-01/V4_input.npz'
        with np.load(xt_saved,allow_pickle=False) as z:anchor_x=z['MLP_input'].copy()
        with torch.inference_mode():
            tx=torch.from_numpy(anchor_x)
            anchor_h=mlp.activation_fn(torch.nn.functional.linear(tx,torch.from_numpy(w1),torch.from_numpy(bias1))).numpy()[0]
            anchor_y=torch.nn.functional.linear(torch.from_numpy(anchor_h),torch.from_numpy(w2),torch.from_numpy(bias2)).numpy()
        anchor=dict(h=anchor_h,y=anchor_y)
        gpu_w2=torch.from_numpy(w2).cuda();gram=torch.zeros((64,64),device='cuda',dtype=torch.float64)
        for row in clean:
            h=torch.from_numpy(row['h']).cuda()
            with torch.inference_mode():
                contributions=torch.stack([torch.nn.functional.linear(h[:,g*64:(g+1)*64],gpu_w2[:,g*64:(g+1)*64]).reshape(-1) for g in range(64)])
                gram+=(contributions@contributions.T).double()
            del h,contributions
        G=gram.cpu().numpy();assert np.isfinite(G).all() and np.allclose(G,G.T,atol=1e-6,rtol=1e-6)
        npz(FIT/'contribution_gram.npz',gram=G)
        removed=[];steps=[]
        for _ in range(8):
            costs={g:float(G[g,g]+2*G[g,removed].sum()) for g in range(64) if g not in removed}
            g=min(costs,key=lambda k:(costs[k],k));removed.append(g)
            steps.append(dict(removed_group=g,incremental_SSE=costs[g],cumulative_SSE=float(G[np.ix_(removed,removed)].sum())))
        keep=np.array(sorted(set(range(64))-set(removed)),np.int64);ids=(keep[:,None]*64+np.arange(64)).reshape(-1)
        assert len(ids)==3584
        npz(FIT/'selection.npz',kept_original_groups=keep,removed_original_groups=np.array(removed),gram=G)
        v['group_selection']=dict(removed_original_groups=removed,kept_original_groups=keep.tolist(),steps=steps,
            post_GELU_contributions_include_cross_terms=True,fit_windows=8,fit_source_groups=4,selection_uses_no_answers=True)
        new=dict(fc1_codes=c1[ids].copy(),fc1_scales=s1[ids].copy(),fc2_codes=c2[:,keep].copy(),fc2_scales=s2[:,keep].copy(),
                 bias1=bias1[ids].copy(),bias2=bias2.copy(),kept_original_groups=keep)
        cutw=w2[:,ids].copy();baselinew=torch.from_numpy(cutw)
        def evaluate(weight,bias):
            rows=[];refs=[];ys=[]
            with torch.inference_mode():
                for r in p['training_requests']:
                    item=data[r['id']]['clean'];h=torch.from_numpy(item['h'][:,ids].copy())
                    y=torch.nn.functional.linear(h,torch.from_numpy(weight),torch.from_numpy(bias)).numpy()
                    m=metric(y,item['y']);rows.append(dict(id=r['id'],**m));ys.append(y);refs.append(item['y'])
                ax=torch.from_numpy(anchor['h'][:,ids].copy())
                ay=torch.nn.functional.linear(ax,torch.from_numpy(weight),torch.from_numpy(bias)).numpy()
            aggregate=metric(np.concatenate(ys),np.concatenate(refs));am=metric(ay,anchor['y'])
            hard=[]
            with torch.inference_mode():
                for rid,items in data.items():
                    if 'hard' in items:
                        h=torch.from_numpy(items['hard']['h'][:,ids].copy())
                        y=torch.nn.functional.linear(h,torch.from_numpy(weight),torch.from_numpy(bias)).numpy()
                        hard.append(dict(id=rid,**metric(y,items['clean']['y'])))
            good=passes(rows+[aggregate,am])
            return dict(clean_fit=rows,aggregate=aggregate,saved_A53_input=am,hard_student_clean_teacher=hard,
                hard_mean_relativeL2=float(np.mean([r['relative_L2'] for r in hard])),passed_local_gate=good),ys
        # Preserve the old energy3584 recipe as an explicit unmodified control.
        prior=read(RUNS/'M535-V4-local-screen-board-01/BOARD_RESULT.json')
        oldkeep=np.array(next(r for r in prior['screen']['candidates'] if r['width']==3584)['selected_original_groups'])
        oldids=(oldkeep[:,None]*64+np.arange(64)).reshape(-1);oldrows=[]
        with torch.inference_mode():
            for item in clean:
                y=torch.nn.functional.linear(torch.from_numpy(item['h'][:,oldids].copy()),torch.from_numpy(w2[:,oldids].copy()),torch.from_numpy(bias2)).numpy()
                oldrows.append(metric(y,item['y']))
        v['old_energy3584_training_metrics']=oldrows
        raw,ys=evaluate(cutw,bias2);v['variants'].append(dict(name='contribution_R0',metrics=raw))
        residual=sum((item['y'].astype(np.float64)-y.astype(np.float64)).sum(0) for item,y in zip(clean,ys))/(8*392)
        r1=residual.astype(np.float32);fused=np.add(bias2,r1,dtype=np.float32)
        r1metrics,_=evaluate(cutw,fused);v['variants'].append(dict(name='contribution_R1_fused',metrics=r1metrics))
        npz(FIT/'R1_fused.npz',R1=r1,original_bias2=bias2,fused_bias2=fused)
        chosen='contribution_R1_fused' if r1metrics['passed_local_gate'] else None
        chosen_weights=dict(new,bias2=fused)
        v['R1_fp64_residual_mean_cast_once']=True;v['R1_fused_bias_actual_forward_evaluated']=True
        if chosen is None:
            v['conditional_fc2_started']=True
            sys.path.insert(0,str(ROOT/'deployment/mage_vl4b/scripts'))
            from mixed_bit_checkpoint import quantize_rows_for_storage
            batchdata={}
            for rid,items in data.items():
                batchdata[rid]={kind:torch.from_numpy(item['h'][:,ids].copy()).cuda() for kind,item in items.items()}
                batchdata[rid]['teacher']=torch.from_numpy(items['clean']['y']).cuda()
            arms={};baseW=baselinew.cuda();baseB=torch.from_numpy(fused).cuda()
            for arm in p['conditional_fc2']['arms']:
                torch.manual_seed(536);W=torch.nn.Parameter(baseW.clone());b=torch.nn.Parameter(baseB.clone())
                opt=torch.optim.Adam([W,b],lr=p['conditional_fc2']['lr']);trace=[]
                for step in range(p['conditional_fc2']['steps_per_arm']):
                    assert time.monotonic()-started<p['budgets']['fit_seconds']
                    rid=p['training_requests'][step%8]['id'];use_hard=arm=='paired_harder_student' and step>=64 and 'hard' in batchdata[rid]
                    item=batchdata[rid];h=item['hard' if use_hard else 'clean'];target=item['teacher']
                    opt.zero_grad(set_to_none=True);effective=W
                    if step>=64:
                        _,_,q=quantize_rows_for_storage(torch,W,4,64);effective=W+(q-W).detach()
                    y=torch.nn.functional.linear(h,effective,b)
                    loss=(y-target).square().mean()/target.square().mean().clamp_min(1e-8)
                    anchorloss=(W-baseW).square().mean()/baseW.square().mean().clamp_min(1e-8)
                    total=loss+p['conditional_fc2']['weight_anchor']*anchorloss
                    assert torch.isfinite(total);total.backward();torch.nn.utils.clip_grad_norm_([W,b],1.);opt.step()
                    trace.append(dict(step=step,request_id=rid,hard_student=use_hard,quantized_forward=step>=64,loss=float(loss.detach())))
                    if step%16==0:print('M536_FC2',arm,step,trace[-1]['loss'],flush=True)
                with torch.no_grad():u,s,restored=quantize_rows_for_storage(torch,W,4,64)
                signed=(u.to(torch.int16)-8).to(torch.int8).cpu().numpy();scale=s.cpu().numpy()
                dense=(signed.astype(np.float32)*scale.astype(np.float32)[...,None]).reshape(1024,3584)
                assert scale.dtype==np.float16 and (scale>0).all() and np.isfinite(scale).all()
                assert np.array_equal(dense,restored.detach().cpu().numpy())
                bias=b.detach().cpu().numpy();em,_=evaluate(dense,bias)
                fpmetrics,_=evaluate(W.detach().cpu().numpy(),bias)
                z=dict(new,fc2_codes=signed,fc2_scales=scale,bias2=bias)
                file=FIT/(arm+'_W4.npz');npz(file,**z)
                arms[arm]=dict(weights=z,metrics=em,file=rel(file),sha256=sha(file))
                v['variants'].append(dict(name=arm,metrics=em,FP32_before_export=fpmetrics,steps=128,
                    payload=rel(file),sha256=sha(file),trajectory=trace,fc1_codes_scales_bias_unchanged=True,
                    inference_has_no_extra_branch=True,export_W4_G64_FP16=True))
                v['training_steps']+=128;del W,b,opt;gc.collect();torch.cuda.empty_cache()
            cleanarm,aug=arms['clean_control'],arms['paired_harder_student']
            if aug['metrics']['passed_local_gate'] and (not cleanarm['metrics']['passed_local_gate'] or
                (aug['metrics']['hard_mean_relativeL2']<cleanarm['metrics']['hard_mean_relativeL2'] and
                 aug['metrics']['aggregate']['relative_L2']<=cleanarm['metrics']['aggregate']['relative_L2']+.02)):
                chosen='paired_harder_student';chosen_weights=aug['weights']
            elif cleanarm['metrics']['passed_local_gate']:chosen='clean_control';chosen_weights=cleanarm['weights']
        v['selected_local_method']=chosen
        if chosen:
            PKG.mkdir(exist_ok=False);npz(PKG/'V4_3584_weights.npz',**chosen_weights)
            plan=dict(status='LOCAL_RECOVERY_PASS_FULL_QUALITY_PENDING',method=chosen,target='model.visual.encoder.layers.4.mlp',width=3584,
                kept_original_groups=keep.tolist(),R1_fused_into_fc2_bias=True,
                source_protocol_sha256=sha(PROTOCOL),weights=dict(path='V4_3584_weights.npz',sha256=sha(PKG/'V4_3584_weights.npz')),
                fc1_original_codes_scales=True,fc2_requantized=chosen in ('clean_control','paired_harder_student'),full_quality_pass=False,TTFT_pass=False)
            save(PKG/'V4_PLAN.json',plan);(PKG/'v4_recovery_native.py').open('xb').write((HERE/'v4_recovery_native.py').read_bytes())
            files=[dict(path=f.name,bytes=f.stat().st_size,sha256=sha(f)) for f in sorted(PKG.iterdir())]
            save(PKG/'PACKAGE_MANIFEST.json',dict(files=files,file_count=len(files),total_bytes=sum(r['bytes'] for r in files)))
            v['candidate']=dict(package=rel(PKG),manifest_sha256=sha(PKG/'PACKAGE_MANIFEST.json'))
        assert all(q._version==version and q.data_ptr()==ptr and tuple(q.shape)==shape for q,version,ptr,shape in mlp_versions)
        v.update(status='COMPLETE_M536_V4_LOCAL_RECOVERY_NOT_FULL_QUALITY',primary_rc=0,
                 old_body_not_updated=True,full_quality_pass=False,board_TTFT_pass=False)
    except BaseException:v['traceback']=traceback.format_exc()
    finally:
        if subset is not None:subset.close()
        if selector is not None:selector.close()
        if runtime is not None:runtime.close()
        v['elapsed_s']=time.monotonic()-started
        v['files']=[dict(path=rel(f),bytes=f.stat().st_size,sha256=sha(f)) for f in sorted(FIT.rglob('*')) if f.is_file()]
        save(FIT/'RESULT.json',v);print(v['status'],v.get('traceback',''),v.get('selected_local_method'),flush=True)
    return v['primary_rc']
if __name__=='__main__':raise SystemExit(main())
