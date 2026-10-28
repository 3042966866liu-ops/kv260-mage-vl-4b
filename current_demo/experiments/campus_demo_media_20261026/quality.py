"""Actual unchanged recovered V4 model on predeclared new video frames."""
import sys,traceback,gc,time,json,hashlib
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT/'experiments/v4_recovery_20261025'))
from common_v4 import *
PROTO=RUNS/'M539-campus12-demo-quality-protocol-01/RESULT.json'
OUT=RUNS/'M539-campus12-demo-software-quality-01'
def main():
    p=read(PROTO)
    for f,h in p['frozen'].items():assert sha(ROOT/f)==h,f
    OUT.mkdir(exist_ok=False);started=time.monotonic();e=None;override=None
    result=dict(status='FAIL_M539_NEW_VIDEO_SOFTWARE_PREFILLS',primary_rc=1,samples=[],board_commands=0,heldout_opened=False,new_training_steps=0)
    try:
        sys.path.insert(0,str(ROOT/'experiments/augmented_student_20261025'));from common_joint import engine_class
        import torch
        from v4_recovery_native import V4Recovery
        base=read(RUNS/'M525-joint-augmented-student-128-protocol-02/RESULT.json');plan=read(PARENT/'DEMO_BOARD_PLAN.json')
        hp=OPT/'candidates/M523-fixed-demo-subset-board-07';sys.path.insert(0,str(hp));from learned_head import LearnedHead
        head=LearnedHead(hp,read(hp/'HEAD_MANIFEST.json'));e=engine_class()(base['runtime_protocol']);e.set_active(plan['retained_vision'],plan['retained_language'])
        import m273_latest_multiscale_contract as m273
        pkg=ROOT/p['package'];assert sha(pkg/'PACKAGE_MANIFEST.json')==p['package_manifest_sha256']
        override=V4Recovery(torch,core(e.original_vision[4]).mlp,pkg,lambda:None);override.select(True)
        versions=[(q,q._version,q.data_ptr(),tuple(q.shape)) for m in override.new for q in m.parameters()]
        observed={}
        def capture(module,args):observed['x']=args[0].detach().float().cpu().numpy().reshape(-1,2560)[-1:].copy()
        e.hooks.append(e.model.lm_head.register_forward_pre_hook(capture,prepend=True));ids=plan['token_ids'];assert len(ids)==128 and ids.count(151655)==98
        for c in p['cases']:
            assert time.monotonic()-started<p['budget']['seconds'];file=ROOT/c['frame'];assert sha(file)==c['frame_sha256']
            frame=np.load(file,allow_pickle=False);a=m273.preprocess(np.ascontiguousarray(frame[None]));assert a['pixel_values'].shape==(392,768)
            x={k:torch.from_numpy(v.copy()) for k,v in a.items()};counts=dict(e.counts);e.oracle.trace=[]
            with torch.inference_mode():
                f=e.vision(a['pixel_values'],a['image_grid_thw'],a['patch_positions']);assert f.shape==(98,2560) and np.isfinite(f).all()
                assert len(e.oracle.trace)==104 and {r['layer'] for r in e.oracle.trace}=={13,14,15,23}
                e.injected=dict(features=torch.from_numpy(f.copy()),pixels=x['pixel_values'].to(e.visual.embeddings.patch_embedding.weight.dtype),grid=x['image_grid_thw'],positions=x['patch_positions'])
                e.visual_calls=0;cache=e.DynamicCache(config=e.model.config.text_config);assert cache.get_seq_length()==0
                try:
                    output=e.model(**x,input_ids=torch.tensor([ids]),attention_mask=torch.ones((1,128),dtype=torch.long),past_key_values=cache,use_cache=True,logits_to_keep=1)
                    assert output.past_key_values is cache and cache.get_seq_length()==128 and len(cache.layers)==18
                    z0=output.logits[0,-1].float().cpu().numpy().copy();z=head.add(observed.pop('x'),z0[None])[0]
                finally:e.discard(torch,cache)
            assert cache.get_seq_length()==0 and e.visual_calls==1 and z.shape==(151936,) and np.isfinite(z).all()
            e.unchanged();assert all(q._version==n and q.data_ptr()==ptr and tuple(q.shape)==shape for q,n,ptr,shape in versions)
            for branch,size,active in [('vision',24,plan['retained_vision']),('language',36,plan['retained_language'])]:
                assert all(e.counts.get(branch+'_'+str(i).zfill(2),0)-counts.get(branch+'_'+str(i).zfill(2),0)==int(i in active) for i in range(size))
            token=int(z.argmax());raw=e.tokenizer.decode([token],skip_special_tokens=True);actual={'yes':'Yes','true':'Yes','no':'No','false':'No'}.get(raw.strip().casefold().rstrip('.,!?;:'),'Invalid')
            fpath=OUT/(c['id']+'.npz');npz(fpath,features=f,logits=z,base_logits=z0)
            top=sorted(range(len(z)),key=lambda j:(-float(z[j]),j))[:16]
            row=dict(id=c['id'],timestamp_s=c['timestamp_s'],source_frame_index=c['source_frame_index'],expected=c['expected'],actual=actual,raw_token=raw,token_id=token,
                matches_assistant_review=actual==c['expected'],label_origin=c['label_origin'],input_frame_sha256=c['frame_sha256'],
                top16=[dict(token_id=j,raw=e.tokenizer.decode([j],skip_special_tokens=True),logit=float(z[j])) for j in top],
                tokens=128,visual_slots=98,views=2,full_vocab=151936,decode_calls=0,cache_before=0,cache_after_clear=0,cache_layers=18,
                parameter_versions_unchanged=True,payload=rel(fpath),sha256=sha(fpath),logits_raw_sha256=digest(z))
            result['samples'].append(row);save(OUT/(c['id']+'.json'),row);print('M539_CAMPUS12',c['id'],repr(raw),row['matches_assistant_review'],flush=True)
            del output,cache,z,z0;gc.collect()
        assert len(result['samples'])==head.calls==p['budget']['full_prefills']
        result.update(status='COMPLETE_M539_NEW_VIDEO_SOFTWARE_PREFILLS_NOT_BOARD',primary_rc=0,
            full_prefills=len(result['samples']),matching_review=sum(r['matches_assistant_review'] for r in result['samples']),
            false_yes=sum(r['actual']=='Yes' for r in result['samples']),invalid=sum(r['actual']=='Invalid' for r in result['samples']),
            all_selected_frames_No=all(r['actual']=='No' for r in result['samples']),full_video_accepted=False,browser_input_accepted=False,board_accepted=False,
            new_TTFT=False,software_arithmetic_not_whole_board_exact=True)
    except BaseException:result['traceback']=traceback.format_exc()
    finally:
        if override is not None:override.close()
        if e is not None:e.close()
        result['elapsed_s']=time.monotonic()-started;save(OUT/'RESULT.json',result);print(result['status'],result.get('traceback',''),flush=True)
    return result['primary_rc']
if __name__=='__main__':raise SystemExit(main())
