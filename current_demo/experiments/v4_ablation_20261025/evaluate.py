"""Only the forty missing full software prefills. No optimization or board access."""
import sys,traceback,gc
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
from common_ablation import *

def main():
    p=verify();reused=read(REUSE/'RESULT.json');assert reused['primary_rc']==0
    OUT.mkdir(exist_ok=False);started=time.monotonic();e=None;override=None
    result=dict(status='FAIL_M537_MATCHED_FULL_SOFTWARE_ABLATION',primary_rc=1,samples=[],board_commands=0,
        heldout_opened=False,new_optimizer_updates=0,protocol_sha256=sha(PROTO),reuse_result_sha256=sha(REUSE/'RESULT.json'))
    try:
        sys.path.insert(0,str(ROOT/'experiments/augmented_student_20261025'))
        from common_joint import engine_class
        Engine=engine_class()
        import torch,importlib.util
        sys.path.insert(0,str(BASE));from v4_recovery_native import V4Recovery
        spec=importlib.util.spec_from_file_location('_m537_quality_head',HEAD/'learned_head.py');mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod)
        head=mod.LearnedHead(HEAD,read(HEAD/'HEAD_MANIFEST.json'))
        base=read(RUNS/'M525-joint-augmented-student-128-protocol-02/RESULT.json');plan=read(PARENT/'DEMO_BOARD_PLAN.json')
        e=Engine(base['runtime_protocol']);e.set_active(plan['retained_vision'],plan['retained_language'])
        import m273_latest_multiscale_contract as m273
        captured={}
        def observe(module,args):captured['x']=args[0].detach().float().cpu().numpy().reshape(-1,2560)[-1:].copy()
        e.hooks.append(e.model.lm_head.register_forward_pre_hook(observe,prepend=True))
        ids=plan['token_ids'];assert len(ids)==128 and ids.count(151655)==98
        cases={r['key']:r for r in p['cases']}
        for arm in p['new_arms']:
            package=ROOT/reused['variants'][arm]['package']
            assert sha(package/'PACKAGE_MANIFEST.json')==reused['variants'][arm]['manifest_sha256']
            for row in read(package/'PACKAGE_MANIFEST.json')['files']:assert sha(package/row['path'])==row['sha256']
            override=V4Recovery(torch,core(e.original_vision[4]).mlp,package,lambda:None);override.select(True)
            versioned=[(q,q._version,q.data_ptr(),tuple(q.shape)) for m in override.new for q in m.parameters()]
            for task in [r for r in p['todo'] if r['arm']==arm]:
                assert time.monotonic()-started<p['budgets']['evaluate_seconds']
                case=cases[task['case']];file=ROOT/case['frame'];assert sha(file)==case['frame_sha256']
                frame=np.load(file,allow_pickle=False);assert frame.shape==(448,448,3) and frame.dtype==np.uint8
                a=m273.preprocess(np.ascontiguousarray(frame[None]));assert a['pixel_values'].shape==(392,768)
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
                for branch,size,active in [('vision',24,plan['retained_vision']),('language',36,plan['retained_language'])]:
                    assert all(e.counts.get(branch+'_'+str(i).zfill(2),0)-before.get(branch+'_'+str(i).zfill(2),0)==int(i in active) for i in range(size))
                token=int(z.argmax());text=e.tokenizer.decode([token],skip_special_tokens=True);answer=classify(text)
                target=OUT/(arm+'_'+case['key']+'.npz');npz(target,features=f,logits=z,base_logits=z0)
                row=dict(case=case['key'],arm=arm,id=case['id'],view=case['view'],role=case['role'],expected=case['expected'],actual=answer,
                    raw_token=text,token_id=token,correct=answer==case['expected'],correct_direction_pp=metrics(z,case['expected']),
                    reused=False,source_payload=rel(target),source_sha256=sha(target),logits_raw_sha256=digest(z),frame_raw_sha256=digest(frame),
                    tokens=128,visual_slots=98,views=2,full_vocab=151936,decode_calls=0,cache_before=0,cache_after_clear=0,cache_layer_count=18,
                    parameter_versions_unchanged=True,weights_sha256=sha(package/'weights.npz'),head_manifest_sha256=sha(HEAD/'HEAD_MANIFEST.json'))
                result['samples'].append(row);save(OUT/(arm+'_'+case['key']+'.json'),row)
                print('M537_QUALITY',arm,case['key'],repr(text),row['correct'],row['correct_direction_pp'],flush=True)
                del output,cache,z,z0;gc.collect()
            override.close();override=None
            assert sha(package/'weights.npz')==reused['variants'][arm]['weights_sha256']
        assert len(result['samples'])==len(p['todo'])==head.calls
        assert {(r['arm'],r['case']) for r in result['samples']}=={(r['arm'],r['case']) for r in p['todo']}
        result.update(status='COMPLETE_M537_MATCHED_FULL_SOFTWARE_ABLATION_NOT_BOARD',primary_rc=0,new_full_prefills=len(result['samples']),
            frozen_head_calls=head.calls,software_arithmetic_not_whole_board_exact=True,new_training_steps=0,production_promoted=False,new_board_TTFT=False)
    except BaseException:result['traceback']=traceback.format_exc()
    finally:
        if override is not None:override.close()
        if e is not None:e.close()
        result['elapsed_s']=time.monotonic()-started;save(OUT/'RESULT.json',result)
        print(result['status'],result.get('traceback',''),flush=True)
    return result['primary_rc']
if __name__=='__main__':raise SystemExit(main())
