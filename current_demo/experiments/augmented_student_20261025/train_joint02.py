"""Matched clean vs harder-view full-student recovery. No device deployment."""
from common_joint import *
import os,traceback,gc,io,math

def main():
    import torch,numpy as np
    import torch.nn.functional as F
    from PIL import Image
    from joint_runtime02 import JointStudent
    protocol=RUNS/(PREFIX+'-protocol-02/RESULT.json');p=read(protocol)
    for name,h in p['frozen'].items():assert sha(ROOT/name)==h
    out=RUNS/(PREFIX+'-training-02');assert not out.exists();out.mkdir();started=time.monotonic()
    result=dict(status='FAIL_FULL_STUDENT_PAIRED_AUGMENTATION',original_rc=1,arms={},evaluations={},board_actions=0,heldout_opened=False);student=None
    try:
        assert torch.cuda.is_available() and torch.cuda.mem_get_info()[0]>6<<30
        student=JointStudent(p);e=student.engine;result['GPU']=dict(device=torch.cuda.get_device_name(0),total_bytes=torch.cuda.mem_get_info()[1])
        result['trainable_parameters']=sum(x.numel() for x in student.params)
        # Load only teacher targets, never feed teacher hidden states into student.
        teacher={}
        capture=read(ROOT/p['teacher_capture_result'])
        for row in capture['teacher_requests']:
            file=ROOT/row['file'];assert sha(file)==row['sha256'];z=torch.load(file,map_location='cpu',weights_only=True)
            teacher[row['request_id']]=dict(logits=z['logits'],features=z['features'],hidden={k:z['blocks'][k]['y'] for k in ['vision_'+str(i).zfill(2) for i in p['vision']]+['language_'+str(i).zfill(2) for i in p['language']]})
        frames={}
        for r in p['train_requests']+p['development_requests']:
            file=ROOT/r['frames'];assert sha(file)==r['frames_sha256'];frames[r['id']]=np.load(file,allow_pickle=False)[r['timestamp_index']].copy()
        preview=read(ROOT/p['augmentation_preview']);hard={}
        for row in preview['records']:
            if row['student_view']=='moderate':
                assert sha(ROOT/row['student_file'])==row['student_sha256'];hard[row['source_request']]=np.load(ROOT/row['student_file'],allow_pickle=False)
        def prepare(request,stage=0,seed=0,fixed_hard=False):
            frame=frames[request['id']];meta=dict(stage=0,changed=False)
            if fixed_hard:frame=hard[request['id']];meta=dict(stage=2,changed=True,fixed_preview=True)
            elif stage and request['id'] in p['safe_augmentation_ids']:
                rng=np.random.default_rng(seed);settings=p['augmentation_curriculum'][stage]
                gamma=float(rng.uniform(*settings['gamma']));brightness=float(rng.uniform(*settings['brightness']));quality=int(rng.integers(settings['JPEG_quality'][0],settings['JPEG_quality'][1]+1));noise=float(rng.uniform(*settings['gaussian_noise_std_RGB255']))
                adjusted=np.clip((frame.astype(np.float32)/255)**gamma*brightness*255,0,255).round().astype(np.uint8)
                stream=io.BytesIO();Image.fromarray(adjusted).save(stream,format='JPEG',quality=quality,subsampling=0);stream.seek(0)
                image=np.asarray(Image.open(stream).convert('RGB')).astype(np.float32)
                frame=np.clip(image+rng.normal(0,noise,image.shape),0,255).round().astype(np.uint8)
                meta=dict(stage=stage,changed=True,gamma=gamma,brightness=brightness,JPEG_quality=quality,noise_std_RGB255=noise,seed=seed)
            arrays=e.preprocess(np.ascontiguousarray(frame[None]));assert arrays['pixel_values'].shape==(392,768)
            return arrays,meta
        def evaluate(name):
            folder=out/name;folder.mkdir();rows=[]
            requests=[(r,False) for r in p['train_requests']+p['development_requests']]+[(r,True) for r in p['train_requests'] if r['id'] in p['safe_augmentation_ids']]
            for request,hard_view in requests:
                arrays,meta=prepare(request,fixed_hard=hard_view)
                with torch.no_grad():z,features,_=student.forward(arrays)
                assert torch.isfinite(z).all() and torch.isfinite(features).all()
                token=int(z.argmax());raw=e.tokenizer.decode([token],skip_special_tokens=True).strip();answer={'yes':'Yes','no':'No','true':'Yes','false':'No'}.get(raw.casefold().rstrip('.,!?;:'),'Invalid')
                expected='Yes' if request['knife_present'] else 'No';key=request['id']+('_moderate' if hard_view else '_clean')
                path=folder/(key+'.logits.npy')
                with path.open('xb') as stream:np.save(stream,z.detach().cpu().numpy(),allow_pickle=False)
                row=dict(id=request['id'],hard_view=hard_view,split='fit' if request in p['train_requests'] else 'reserved-cal',expected=expected,actual=answer,raw_first_token=raw,token_id=token,correct=answer==expected,logits_path=relative(path),logits_sha256=sha(path),augmentation=meta)
                rows.append(row);print('JOINT_EVAL',name,key,answer,row['correct'],flush=True)
            record=dict(rows=rows,fit_correct=sum(r['correct'] for r in rows if r['split']=='fit' and not r['hard_view']),reserved_cal_correct=sum(r['correct'] for r in rows if r['split']=='reserved-cal'),fixed_demo_correct=sum(r['correct'] for r in rows if r['id'] in p['safe_augmentation_ids'] and not r['hard_view']),fixed_hard_correct=sum(r['correct'] for r in rows if r['hard_view']))
            save(folder/'RESULT.json',record);student.hidden={};student.feature=None;gc.collect();torch.cuda.empty_cache();return record
        def losses(request,arrays):
            z,features,hidden=student.forward(arrays);target=teacher[request['id']]
            expected=9454 if request['knife_present'] else 2753
            # cal02t1 retains its registered label in all evaluation reports; its
            # acknowledged visibility ambiguity is not silently trained as Yes.
            supervised=request['id'] not in p['ambiguous_positive_CE_mask_ids']
            ce=F.cross_entropy(z.reshape(1,-1),torch.tensor([expected],device='cuda')) if supervised else z.sum()*0
            teacher_z=target['logits'].to('cuda').float();teacher_correct=int(teacher_z.argmax())==expected
            kl=F.kl_div(F.log_softmax(z/2,dim=-1),F.softmax(teacher_z/2,dim=-1),reduction='sum')*4 if teacher_correct and supervised else z.sum()*0
            v=target['features'].to('cuda').float();vkd=F.mse_loss(features.float(),v)/v.square().mean().clamp_min(1e-8)
            terms=[]
            for key,actual in hidden.items():
                t=target['hidden'][key].to('cuda').float();terms.append(F.mse_loss(actual.float(),t)/t.square().mean().clamp_min(1e-8))
            mid=torch.stack(terms).mean();loss=ce+p['loss_weights']['teacher_KL']*kl+p['loss_weights']['visual_features']*vkd+p['loss_weights']['mapped_hidden']*mid
            assert torch.isfinite(loss)
            student.last_ce=ce;student.last_z=z
            return loss,dict(loss=float(loss.detach()),CE=float(ce.detach()),teacher_KL=float(kl.detach()),visual_KD=float(vkd.detach()),hidden_KD=float(mid.detach()),supervised_label_used=supervised,teacher_correct=teacher_correct,predicted_token=int(z.detach().argmax()),target_token=expected)
        # One real full-path backward, no optimizer update, proves both branches
        # receive decision gradients under the actual streamed GPU interfaces.
        arrays,_=prepare(p['train_requests'][0]);loss,metrics=losses(p['train_requests'][0],arrays)
        saved_baseline=RUNS/(PREFIX+'-training-01/baseline/cal_00_t0_clean.logits.npy')
        assert np.array_equal(student.last_z.detach().cpu().numpy(),np.load(saved_baseline,allow_pickle=False)), 'Zero-head-adapter baseline changed'
        student.last_ce.backward()
        gradients={branch:sum(float(m.B.grad.float().norm()) for name,m in student.linears.items() if name.startswith(branch+':')) for branch in ('vision','language','head')}
        assert all(v>0 and math.isfinite(v) for v in gradients.values()) and all(x.grad is not None and torch.isfinite(x.grad).all() for x in student.params)
        save(out/'FULL_PATH_GRADIENT_SMOKE.json',dict(status='PASS_REAL_FULL_VISUAL_LANGUAGE_GRADIENTS',branch_gradient_norm_sums=gradients,metrics=metrics,optimizer_updates=0,source_sha256=sha(HERE/'joint_runtime02.py'),CE_only_backward=True,matched_original_baseline_bit_exact=True))
        print('JOINT_FULL_PATH_GRADIENT_PASS',gradients,flush=True);del loss;student.hidden={};student.feature=None;student.reset();gc.collect();torch.cuda.empty_cache()
        result['evaluations']['untrained']=read(ROOT/p['source_baseline'])['evaluations']['untrained']
        student.last_ce=None;student.last_z=None
        baseline_hashes={k:hashlib.sha256(m.A.detach().cpu().numpy().tobytes()+m.B.detach().cpu().numpy().tobytes()).hexdigest() for k,m in student.linears.items()}
        for arm in ('clean_control','progressive_augmented'):
            student.reset();assert {k:hashlib.sha256(m.A.detach().cpu().numpy().tobytes()+m.B.detach().cpu().numpy().tobytes()).hexdigest() for k,m in student.linears.items()}==baseline_hashes
            body=[x for k,m in student.linears.items() if not k.startswith('head:') for x in (m.A,m.B)];head=[e.model.lm_head.A,e.model.lm_head.B]
            optimizer=torch.optim.AdamW([{'params':body,'lr':p['learning_rate']},{'params':head,'lr':p['head_learning_rate']}],weight_decay=0.);trajectory=[]
            eligible=[r for r in p['train_requests'] if r['id'] not in p['ambiguous_positive_CE_mask_ids']]
            negatives=[r for r in eligible if not r['knife_present']];positives=[r for r in eligible if r['knife_present']]
            ambiguous=next(r for r in p['train_requests'] if r['id']=='cal_02_t1')
            for step in range(p['steps_per_arm']):
                assert time.monotonic()-started<p['wall_seconds']
                pair=[negatives[step%len(negatives)],positives[step%len(positives)]]
                stage=0 if arm=='clean_control' or step<8 else 1 if step<16 else 2
                optimizer.zero_grad(set_to_none=True);batch=[]
                for j,request in enumerate(pair):
                    arrays,augmentation=prepare(request,stage,p['seed']*10000+step*3+j)
                    loss,metrics=losses(request,arrays);(loss/2).backward()
                    batch.append(dict(request_id=request['id'],augmentation=augmentation,**metrics))
                    del loss;student.hidden={};student.feature=None;student.last_ce=None;student.last_z=None
                if (step+1)%p['ambiguous_feature_replay_every']==0:
                    arrays,augmentation=prepare(ambiguous);loss,metrics=losses(ambiguous,arrays);(loss*.25).backward()
                    batch.append(dict(request_id=ambiguous['id'],augmentation=augmentation,feature_only_weight=.25,**metrics))
                    del loss;student.hidden={};student.feature=None;student.last_ce=None;student.last_z=None
                assert all(x.grad is not None and torch.isfinite(x.grad).all() for x in student.params)
                norm=float(torch.nn.utils.clip_grad_norm_(student.params,1.));assert norm>0 and math.isfinite(norm)
                optimizer.step();row=dict(step=step,gradient_norm=norm,batch=batch);trajectory.append(row)
                print('JOINT_BALANCED_STEP',arm,step,row,flush=True)
            checkpoint=out/(arm+'.ADAPTERS.pt')
            with checkpoint.open('xb') as stream:torch.save(student.state(),stream)
            record=dict(trajectory=trajectory,steps=len(trajectory),adapter_path=relative(checkpoint),adapter_sha256=sha(checkpoint),initialization_hashes=baseline_hashes)
            save(out/(arm+'.RESULT.json'),record);result['arms'][arm]=record
            result['evaluations'][arm]=evaluate(arm)
            del optimizer;gc.collect();torch.cuda.empty_cache()
        result.update(status='COMPLETE_BALANCED_FULL_STUDENT_CLEAN_AND_HARDER_VIEW_TRAINING',original_rc=0,full_student_decision_gradients_verified=True,inference_augmentation_required=False,board_quality_proven=False,exported_quality_proven=False,all6_test_still_closed=True)
    except BaseException:result['traceback']=traceback.format_exc()
    finally:
        if student:student.close()
        result['elapsed_s']=time.monotonic()-started;save(out/'RESULT.json',result);print(result['status'],result.get('traceback',''),flush=True)
    return result['original_rc']
if __name__=='__main__':raise SystemExit(main())
