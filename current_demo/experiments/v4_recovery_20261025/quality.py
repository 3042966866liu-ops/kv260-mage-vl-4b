"""Original dual128 controls and recovered V4 whole-model first judgments."""
import sys,traceback,gc
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
from common_v4 import *
def main():
    p=verify();fit=read(FIT/'RESULT.json');assert fit['primary_rc']==0
    assert fit['selected_local_method'] is not None and sha(PKG/'PACKAGE_MANIFEST.json')==fit['candidate']['manifest_sha256']
    for r in read(PKG/'PACKAGE_MANIFEST.json')['files']:assert sha(PKG/r['path'])==r['sha256']
    out=RUNS/'M536-V4-3584-recovery-quality-01';out.mkdir(exist_ok=False);started=time.monotonic();e=None;override=None
    result=dict(status='FAIL_M536_FULL_SOFTWARE_QUALITY',primary_rc=1,board_commands=0,heldout_opened=False,
        selected_local_method=fit['selected_local_method'],fit_result_sha256=sha(FIT/'RESULT.json'),samples=[])
    try:
        sys.path.insert(0,str(ROOT/'experiments/augmented_student_20261025'))
        from common_joint import engine_class
        Engine=engine_class()
        import torch
        from v4_recovery_native import V4Recovery
        import m273_latest_multiscale_contract as m273
        base=read(RUNS/'M525-joint-augmented-student-128-protocol-02/RESULT.json')
        boardplan=read(PARENT/'DEMO_BOARD_PLAN.json')
        headpkg=OPT/'candidates/M523-fixed-demo-subset-board-07';sys.path.insert(0,str(headpkg))
        from learned_head import LearnedHead
        head=LearnedHead(headpkg,read(headpkg/'HEAD_MANIFEST.json'))
        e=Engine(base['runtime_protocol']);e.set_active(boardplan['retained_vision'],boardplan['retained_language'])
        override=V4Recovery(torch,core(e.original_vision[4]).mlp,PKG,lambda:None)
        versioned=[(q,q._version,q.data_ptr(),tuple(q.shape)) for m in override.new for q in m.parameters()]
        captured={}
        def observe(module,args):captured['x']=args[0].detach().float().cpu().numpy().reshape(-1,2560)[-1:].copy()
        e.hooks.append(e.model.lm_head.register_forward_pre_hook(observe,prepend=True))
        e.preprocess=m273.preprocess;ids=boardplan['token_ids'];assert len(ids)==128 and ids.count(151655)==98
        fixed=[]
        for r in boardplan['demo_requests']:
            f=PARENT/r['frame_path'];assert sha(f)==r['frame_sha256']
            fixed.append((r,np.load(f,allow_pickle=False),r['expected_decision'],'fixed-demo'))
        reserved=[]
        for r in p['reserved_requests']:
            f=ROOT/r['frames'];assert sha(f)==r['frames_sha256'];frame=np.load(f,allow_pickle=False)[r['timestamp_index']]
            reserved.append((r,frame,'Yes' if r['knife_present'] else 'No','reserved-cal'))
        control_features={}
        for arm in ('control4096','recovered3584'):
            override.select(arm=='recovered3584')
            for request,frame,expected,role in fixed+(reserved if arm=='recovered3584' else []):
                assert time.monotonic()-started<p['budgets']['quality_seconds']
                a=e.preprocess(np.ascontiguousarray(frame[None]));assert a['pixel_values'].shape==(392,768)
                x={k:torch.from_numpy(value.copy()) for k,value in a.items()};e.oracle.trace=[];before=dict(e.counts)
                with torch.inference_mode():
                    f=e.vision(a['pixel_values'],a['image_grid_thw'],a['patch_positions'])
                    assert f.shape==(98,2560) and np.isfinite(f).all()
                    assert len(e.oracle.trace)==104 and {r['layer'] for r in e.oracle.trace}=={13,14,15,23}
                    e.injected=dict(features=torch.from_numpy(f.copy()),pixels=x['pixel_values'].to(e.visual.embeddings.patch_embedding.weight.dtype),grid=x['image_grid_thw'],positions=x['patch_positions'])
                    e.visual_calls=0;cache=e.DynamicCache(config=e.model.config.text_config);assert cache.get_seq_length()==0
                    try:
                        output=e.model(**x,input_ids=torch.tensor([ids]),attention_mask=torch.ones((1,128),dtype=torch.long),past_key_values=cache,use_cache=True,logits_to_keep=1)
                        assert output.past_key_values is cache and cache.get_seq_length()==128 and len(cache.layers)==18
                        z0=output.logits[0,-1].float().cpu().numpy().copy();z=head.add(captured.pop('x'),z0[None])[0]
                    finally:e.discard(torch,cache)
                assert cache.get_seq_length()==0 and e.visual_calls==1 and z.shape==(151936,) and np.isfinite(z).all()
                e.unchanged();assert all(q._version==n and q.data_ptr()==ptr and tuple(q.shape)==shape for q,n,ptr,shape in versioned)
                for branch,size,active in [('vision',24,boardplan['retained_vision']),('language',36,boardplan['retained_language'])]:
                    assert all(e.counts.get(branch+'_'+str(i).zfill(2),0)-before.get(branch+'_'+str(i).zfill(2),0)==int(i in active) for i in range(size))
                token=int(z.argmax());text=e.tokenizer.decode([token],skip_special_tokens=True)
                answer={'yes':'Yes','true':'Yes','no':'No','false':'No'}.get(text.strip().casefold().rstrip('.,!?;:'),'Invalid')
                pp=np.exp(z.astype(np.float64)-float(z.max()));pp/=pp.sum();sign=1 if expected=='Yes' else -1
                key=arm+'_'+request['id'];file=out/(key+'.npz');npz(file,features=f,logits=z,base_logits=z0)
                row=dict(arm=arm,id=request['id'],role=role,expected=expected,actual=answer,token_id=token,raw_token=text,correct=answer==expected,
                    correct_direction_pp=float((pp[9454]-pp[2753])*sign*100),tokens=128,visual_slots=98,views=2,decode_calls=0,
                    full_vocab=151936,cache_before=0,cache_after_clear=0,retained_language=boardplan['retained_language'],
                    cache_layer_count=18,parameter_versions_unchanged=True,payload=rel(file),sha256=sha(file))
                if arm=='control4096':control_features[request['id']]=f.copy()
                elif role=='fixed-demo':row['complete_visual_feature_difference']=metric(f,control_features[request['id']])
                result['samples'].append(row);save(out/(key+'.json'),row)
                print('M536_FULL_QUALITY',arm,request['id'],text,row['correct'],row['correct_direction_pp'],flush=True)
                del output,cache,z,z0;gc.collect()
        controls=[r for r in result['samples'] if r['arm']=='control4096']
        candidates=[r for r in result['samples'] if r['arm']=='recovered3584' and r['role']=='fixed-demo']
        rest=[r for r in result['samples'] if r['role']=='reserved-cal']
        assert len(result['samples'])==12 and len(controls)==len(candidates)==len(rest)==4 and head.calls==12
        result.update(status='COMPLETE_M536_FULL_SOFTWARE_QUALITY_NOT_BOARD',primary_rc=0,
            control_correct=sum(r['correct'] for r in controls),fixed_candidate_correct=sum(r['correct'] for r in candidates),
            reserved_candidate_correct=sum(r['correct'] for r in rest),
            fixed_quality_pass=all(r['correct'] for r in controls+candidates) and all(r['actual']!='Invalid' for r in result['samples']),
            full_prefills=12,head_calls=head.calls,software_arithmetic_not_whole_board_exact=True,
            production_promoted=False,board_TTFT_pass=False)
    except BaseException:result['traceback']=traceback.format_exc()
    finally:
        if override is not None:override.close()
        if e is not None:e.close()
        result['elapsed_s']=time.monotonic()-started;save(out/'RESULT.json',result)
        print(result['status'],result.get('traceback',''),result.get('fixed_quality_pass'),flush=True)
    return result['primary_rc']
if __name__=='__main__':raise SystemExit(main())
