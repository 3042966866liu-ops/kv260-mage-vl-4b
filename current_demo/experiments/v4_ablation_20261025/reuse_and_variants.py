"""Zero-model replay of old full-parent evidence and frozen matched weights."""
import importlib.util,sys,traceback
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
from common_ablation import *
def main():
    p=verify();REUSE.mkdir(exist_ok=False)
    v=dict(status='FAIL_M537_PARENT_REUSE_AND_MATCHED_VARIANTS',primary_rc=1,new_model_forwards=0,new_optimizer_updates=0,board_commands=0)
    try:
        import torch
        torch.set_num_threads(4);torch.set_num_interop_threads(1)
        from tokenizers import Tokenizer
        tokenizer=Tokenizer.from_file(str(ROOT/p['tokenizer']))
        spec=importlib.util.spec_from_file_location('_m537_frozen_head',HEAD/'learned_head.py');module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
        head=module.LearnedHead(HEAD,read(HEAD/'HEAD_MANIFEST.json'))
        oldpkg=OPT/'candidates/M525-10V18L-learned-head-augmented-01'
        for n in ('A.npy','B.npy'):assert sha(HEAD/n)==sha(oldpkg/n)
        base=read(RUNS/'M525-joint-augmented-student-128-protocol-02/RESULT.json');boardplan=read(PARENT/'DEMO_BOARD_PLAN.json')
        assert base['vision']==boardplan['retained_vision'] and base['language']==boardplan['retained_language'] and base['token_ids']==boardplan['token_ids']
        oldcap=read(RUNS/'M525-joint-augmented-student-128-target-head-capture-01/RESULT.json')
        oldreload=read(RUNS/'M525-joint-augmented-student-128-target-head-reload-01/RESULT.json')
        assert oldcap['original_rc']==oldreload['original_rc']==0 and oldreload['source_body_unchanged']
        cap={(r['id'],r['view']):r for r in oldcap['records']}
        oldrows={(r['id'],r['view']):r for r in oldreload['samples']}
        existing=read(RUNS/'M536-V4-3584-recovery-quality-01/RESULT.json');assert existing['primary_rc']==0
        parent_rows=[];child_rows=[];old_match=[]
        for case in p['cases']:
            key=(case['id'],'clean' if case['view']=='clean' else 'moderate_check');c=cap[key];old=oldrows[key]
            frame=ROOT/case['frame'];assert sha(frame)==case['frame_sha256']
            assert sha(ROOT/c['frame'])==c['frame_sha256']
            assert np.array_equal(np.load(frame,allow_pickle=False),np.load(ROOT/c['frame'],allow_pickle=False))
            payload=ROOT/c['payload'];assert sha(payload)==c['sha256']
            with np.load(payload,allow_pickle=False) as z:recomposed=head.add(z['x'][None],z['z'][None])[0]
            old_file=RUNS/'M525-joint-augmented-student-128-target-head-reload-01'/(case['id']+'_'+key[1]+'.logits.npy')
            old_logits=np.load(old_file,allow_pickle=False);assert old_logits.shape==(151936,) and old_logits.dtype==np.float32
            assert np.array_equal(recomposed,old_logits),'Frozen head reapplication differs from saved full parent forward'
            assert int(old_logits.argmax())==old['token']
            source=old_file;z=old_logits;history='M525_fresh_complete_parent_reload'
            if case['view']=='clean' and case['role']=='fixed-demo':
                current=next(r for r in existing['samples'] if r['id']==case['id'] and r['arm']=='control4096')
                source=ROOT/current['payload'];assert sha(source)==current['sha256']
                with np.load(source,allow_pickle=False) as a:new=a['logits'].copy()
                assert np.array_equal(new,old_logits)
                old_match.append(dict(id=case['id'],all151936_logits_bitwise_equal=True))
                z=new;history='M536_latest_complete_parent_control_equals_M525_full_logits'
            token=int(z.argmax());raw=tokenizer.decode([token],skip_special_tokens=True);decision=classify(raw)
            parent_rows.append(dict(case=case['key'],arm='parent4096',id=case['id'],view=case['view'],role=case['role'],
                expected=case['expected'],actual=decision,raw_token=raw,token_id=token,correct=decision==case['expected'],
                correct_direction_pp=metrics(z,case['expected']),logits_raw_sha256=digest(z),source_payload=rel(source),source_sha256=sha(source),
                reused=True,provenance=history,frame_raw_sha256=digest(np.load(frame,allow_pickle=False))))
            if case['view']=='clean':
                old=next(r for r in existing['samples'] if r['id']==case['id'] and r['arm']=='recovered3584')
                f=ROOT/old['payload'];assert sha(f)==old['sha256']
                with np.load(f,allow_pickle=False) as a:z=a['logits'].copy()
                token=int(z.argmax());raw=tokenizer.decode([token],skip_special_tokens=True);decision=classify(raw)
                assert token==old['token_id'] and decision==old['actual']
                child_rows.append(dict(case=case['key'],arm='harder_recovery',id=case['id'],view=case['view'],role=case['role'],
                    expected=case['expected'],actual=decision,raw_token=raw,token_id=token,correct=decision==case['expected'],
                    correct_direction_pp=metrics(z,case['expected']),logits_raw_sha256=digest(z),source_payload=rel(f),source_sha256=sha(f),reused=True))
        assert len(parent_rows)==12 and len(child_rows)==8 and len(old_match)==4
        # All matched learned weights are already trained; never update them here.
        fit=read(FIT/'RESULT.json');clean=next(r for r in fit['variants'] if r['name']=='clean_control');hard=next(r for r in fit['variants'] if r['name']=='paired_harder_student')
        assert clean['steps']==hard['steps']==128
        with np.load(ROOT/clean['payload'],allow_pickle=False) as z:clean_w={k:z[k].copy() for k in z.files}
        with np.load(ROOT/hard['payload'],allow_pickle=False) as z:hard_w={k:z[k].copy() for k in z.files}
        for key in ('fc1_codes','fc1_scales','bias1','kept_original_groups'):assert np.array_equal(clean_w[key],hard_w[key]),key
        assert fit['selected_local_method']=='paired_harder_student'
        sys.path.insert(0,str(ROOT/'experiments/speed_target_30s_20261020'))
        from generate_flap522 import FrozenCheckpoint
        cp=FrozenCheckpoint(read(OPT/'contracts/config.json'));target='model.visual.encoder.layers.4.mlp'
        (c1,s1),b1=cp.packed(target+'.fc1');(c2,s2),b2=cp.packed(target+'.fc2');assert b1==b2==4
        keep=clean_w['kept_original_groups'];ids=(keep[:,None]*64+np.arange(64)).reshape(-1)
        raw=dict(fc1_codes=c1[ids].copy(),fc1_scales=s1[ids].copy(),fc2_codes=c2[:,keep].copy(),fc2_scales=s2[:,keep].copy(),
            bias1=cp.bias(target+'.fc1')[ids].copy(),bias2=cp.bias(target+'.fc2').copy(),kept_original_groups=keep.copy())
        for key in ('fc1_codes','fc1_scales','bias1','kept_original_groups'):assert np.array_equal(raw[key],clean_w[key])
        sys.path.insert(0,str(ROOT/'deployment/mage_vl4b/scripts'));from mixed_bit_checkpoint import quantize_rows_for_storage
        dense=(raw['fc2_codes'].astype(np.float32)*raw['fc2_scales'].astype(np.float32)[...,None]).reshape(1024,3584)
        with torch.inference_mode():u,s,r=quantize_rows_for_storage(torch,torch.from_numpy(dense),4,64)
        reexport=dict(raw,fc2_codes=(u.to(torch.int16)-8).to(torch.int8).numpy(),fc2_scales=s.numpy())
        assert np.array_equal((reexport['fc2_codes'].astype(np.float32)*reexport['fc2_scales'].astype(np.float32)[...,None]).reshape(1024,3584),r.numpy())
        variants={}
        native=BASE/'v4_recovery_native.py'
        for name,weights in [('exact_crop',raw),('reexport_crop',reexport),('clean_recovery',clean_w),('harder_recovery',hard_w)]:
            folder=OPT/'candidates'/('M537-V4-ablation-'+name+'-01');folder.mkdir(exist_ok=False)
            f=folder/'weights.npz';npz(f,**weights)
            save(folder/'V4_PLAN.json',dict(status='FROZEN_MATCHED_V4_RESEARCH_ABLATION',method=name,width=3584,
                weights=dict(path='weights.npz',sha256=sha(f)),no_new_learning=True,source_fit_result_sha256=sha(FIT/'RESULT.json'),
                channel_groups_sha256=digest(keep),head_frozen=True))
            (folder/'v4_recovery_native.py').open('xb').write(native.read_bytes())
            files=[dict(path=x.name,bytes=x.stat().st_size,sha256=sha(x)) for x in sorted(folder.iterdir())]
            save(folder/'PACKAGE_MANIFEST.json',dict(files=files,file_count=len(files),total_bytes=sum(t['bytes'] for t in files)))
            variants[name]=dict(package=rel(folder),manifest_sha256=sha(folder/'PACKAGE_MANIFEST.json'),
                weights_sha256=sha(f),training_updates_this_round=0,original_training_updates=128 if 'recovery' in name else 0,
                codes_scales_FC1_sha256=digest(weights['fc1_codes'])+':'+digest(weights['fc1_scales']),kept_groups=keep.tolist())
        # Identify old errors separately from any new V4-induced failures.
        parent_by={r['case']:r for r in parent_rows};pairs=[]
        for child in child_rows:
            old=parent_by[child['case']]
            pairs.append(dict(case=child['case'],id=child['id'],role=child['role'],expected=child['expected'],
                parent_actual=old['actual'],child_actual=child['actual'],parent_token=old['token_id'],child_token=child['token_id'],
                parent_correct=old['correct'],child_correct=child['correct'],new_failure=old['correct'] and not child['correct'],
                shared_failure=not old['correct'] and not child['correct'],recovered=not old['correct'] and child['correct']))
        v.update(status='PASS_M537_REUSED_MATCHED_PARENT12_CHILD8_AND_FROZEN_VARIANTS',primary_rc=0,
            parent=parent_rows,child=child_rows,pairs=pairs,variants=variants,
            same_input_frames_and128_ids=True,same_model_runtime_and_retained_layers=True,frozen_head_A_B_equal=True,
            original_parent_full_logits_recomposition_all12_exact=True,parent_M536_control4_equals_M525_reload4_exact=old_match,
            old_parent_cache_note='M525 independent full reload used use_cache=False;current M536 uses empty DynamicCache. Same first-step source/IDs/weights and all4 overlap full logits equal. Reused parent rows remain tagged with original cache policy;no decode or cross-task KL.',
            fresh_for_V4_hard_inputs='M525 moderate_check4 were not used for M536 V4 fitting;they were earlier used for head validation,not an independent full-model test set.',
            same_channels=True,new_training_steps=0,old_fit_steps_per_learned_arm=128,
            quantization_control=dict(exact_crop_preserves_integer_slices=True,reexport_uses_same_final_quantizer_as_both_learned_arms=True,
                exact_vs_reexport_fc2_codes_equal=np.array_equal(raw['fc2_codes'],reexport['fc2_codes']),
                exact_vs_reexport_fc2_scales_equal=np.array_equal(raw['fc2_scales'],reexport['fc2_scales'])))
    except BaseException:v['traceback']=traceback.format_exc()
    save(REUSE/'RESULT.json',v);print(v['status'],v.get('traceback',''),flush=True);return v['primary_rc']
if __name__=='__main__':raise SystemExit(main())
