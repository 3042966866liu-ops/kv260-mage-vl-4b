"""Learn on the frozen deployment-numeric student, never on teacher inputs.

Only the actual full-vocabulary head residual is trained. This is a new recovery
recipe after full-body surrogate/export failure, not a claim that body LoRA ran
on hardware. All cached features come from real student forwards.
"""
from common_joint import *
import os, traceback, math, io
import numpy as np

def protocol():
    p=read(RUNS/(PREFIX+'-target-head-protocol-01/RESULT.json'))
    for n,h in p['sources'].items():assert sha(ROOT/n)==h,n
    return p,read(RUNS/(PREFIX+'-protocol-02/RESULT.json'))

def changed_frame(frame,settings,seed):
    from PIL import Image
    rng=np.random.default_rng(seed)
    gamma=float(rng.uniform(*settings['gamma']));brightness=float(rng.uniform(*settings['brightness']))
    quality=int(rng.integers(settings['JPEG_quality'][0],settings['JPEG_quality'][1]+1))
    noise=float(rng.uniform(*settings['gaussian_noise_std_RGB255']))
    image=np.clip((frame.astype(np.float32)/255)**gamma*brightness*255,0,255).round().astype(np.uint8)
    stream=io.BytesIO();Image.fromarray(image).save(stream,format='JPEG',quality=quality,subsampling=0);stream.seek(0)
    image=np.asarray(Image.open(stream).convert('RGB')).astype(np.float32)
    image=np.clip(image+rng.normal(0,noise,image.shape),0,255).round().astype(np.uint8)
    return image,dict(seed=seed,gamma=gamma,brightness=brightness,JPEG_quality=quality,noise_std_RGB255=noise)

def capture():
    import torch
    p,base=protocol();out=RUNS/(PREFIX+'-target-head-capture-01');assert not out.exists();out.mkdir()
    result=dict(status='FAIL_TARGET_NUMERIC_FEATURE_CAPTURE',original_rc=1,records=[],board_actions=0,heldout_opened=False)
    e=None;started=time.monotonic()
    try:
        e=engine_class()(base['runtime_protocol']);e.set_active(base['vision'],base['language']);hidden={}
        def observe(module,args):hidden['x']=args[0].detach().float().cpu().numpy().reshape(-1,2560)[-1].copy()
        e.hooks.append(e.model.lm_head.register_forward_pre_hook(observe,prepend=True))
        requests=[(r,'clean') for r in base['train_requests']+base['development_requests']]
        requests += [(r,v) for r in base['train_requests'] if r['id'] in base['safe_augmentation_ids'] for v in ('weak_train','moderate_train','moderate_check')]
        for request,view in requests:
            file=ROOT/request['frames'];assert sha(file)==request['frames_sha256']
            frame=np.load(file,allow_pickle=False)[request['timestamp_index']].copy();meta={}
            if view!='clean':
                stage=1 if view=='weak_train' else 2
                offset={'weak_train':100,'moderate_train':200,'moderate_check':300}[view]
                seed=p['seed']*10000+offset+int(request['id'][4:6])*2+request['timestamp_index']
                frame,meta=changed_frame(frame,base['augmentation_curriculum'][stage],seed)
            key=request['id']+'_'+view;framefile=out/(key+'.frame.npy')
            with framefile.open('xb') as f:np.save(f,frame,allow_pickle=False)
            arrays=e.preprocess(np.ascontiguousarray(frame[None]));x={k:torch.from_numpy(v.copy()) for k,v in arrays.items()};e.oracle.trace=[]
            with torch.inference_mode():
                features=e.vision(arrays['pixel_values'],arrays['image_grid_thw'],arrays['patch_positions'])
                assert features.shape==(98,2560) and len(e.oracle.trace)==26*len(set(base['vision'])&set(range(13,24)))
                e.injected=dict(features=torch.from_numpy(features.copy()),pixels=x['pixel_values'].to(e.visual.embeddings.patch_embedding.weight.dtype),grid=x['image_grid_thw'],positions=x['patch_positions']);e.visual_calls=0
                z=e.model(**x,input_ids=torch.tensor([base['token_ids']]),attention_mask=torch.ones((1,128),dtype=torch.long),use_cache=False,logits_to_keep=1).logits[0,-1].float().numpy().copy()
            assert z.shape==(151936,) and hidden['x'].shape==(2560,) and e.visual_calls==1 and np.isfinite(z).all() and np.isfinite(hidden['x']).all()
            payload=out/(key+'.npz')
            with payload.open('xb') as f:np.savez(f,x=hidden.pop('x'),z=z)
            row=dict(id=request['id'],view=view,split='fit' if request in base['train_requests'] else 'reserved-cal',target=9454 if request['knife_present'] else 2753,supervised=request['id'] not in base['ambiguous_positive_CE_mask_ids'],payload=relative(payload),sha256=sha(payload),frame=relative(framefile),frame_sha256=sha(framefile),augmentation=meta)
            result['records'].append(row);print('TARGET_NUMERIC_CAPTURE',key,int(z.argmax()),flush=True)
        e.unchanged();result.update(status='COMPLETE_TARGET_NUMERIC_FROZEN_BODY_CAPTURE',original_rc=0,student_prefills=len(result['records']),base_parameters_unchanged=True,full_vocab=151936,pre_A8_hidden=True)
    except BaseException:result['traceback']=traceback.format_exc()
    finally:
        if e:e.close()
        result['elapsed_s']=time.monotonic()-started;save(out/'RESULT.json',result);print(result['status'],result.get('traceback',''),flush=True)
    return result['original_rc']

def train():
    import torch
    import torch.nn.functional as F
    p,base=protocol();capturefile=RUNS/(PREFIX+'-target-head-capture-01/RESULT.json');captured=read(capturefile);assert captured['original_rc']==0
    out=RUNS/(PREFIX+'-target-head-training-01');assert not out.exists();out.mkdir();started=time.monotonic()
    result=dict(status='FAIL_TARGET_HEAD_MATCHED_TRAINING',original_rc=1,arms={},board_actions=0,heldout_opened=False,capture_sha256=sha(capturefile))
    try:
        torch.manual_seed(p['seed']);torch.backends.cuda.matmul.allow_tf32=False
        rows=captured['records'];data={}
        for row in rows:
            f=ROOT/row['payload'];assert sha(f)==row['sha256']
            with np.load(f,allow_pickle=False) as z:data[row['id'],row['view']]={k:torch.from_numpy(z[k].copy()).cuda() for k in ('x','z')}
        teacher={};tc=read(ROOT/base['teacher_capture_result'])
        for row in tc['teacher_requests']:
            f=ROOT/row['file'];assert sha(f)==row['sha256'];teacher[row['request_id']]=torch.load(f,map_location='cpu',weights_only=True)['logits'].float().cuda()
        initial_A=torch.randn(p['rank'],2560,device='cuda')*.01;initial_B=torch.zeros(151936,p['rank'],device='cuda')
        eligible=[r for r in rows if r['view']=='clean' and r['split']=='fit' and r['supervised']]
        negatives=[r for r in eligible if r['target']==2753];positives=[r for r in eligible if r['target']==9454]
        for arm in ('clean_control','progressive_augmented'):
            A=torch.nn.Parameter(initial_A.clone());B=torch.nn.Parameter(initial_B.clone());optimizer=torch.optim.AdamW([A,B],lr=p['learning_rate'],weight_decay=0);history=[]
            for step in range(p['steps_per_arm']):
                optimizer.zero_grad(set_to_none=True);losses=[];batch=[]
                for r in (negatives[step%len(negatives)],positives[step%len(positives)]):
                    view='clean' if arm=='clean_control' or step<16 or r['id'] not in base['safe_augmentation_ids'] else 'weak_train' if step<32 else 'moderate_train'
                    item=data[r['id'],view];z=item['z']+F.linear(F.linear(item['x'],A),B)
                    ce=F.cross_entropy(z[None],torch.tensor([r['target']],device='cuda'));t=teacher[r['id']]
                    kl=F.kl_div(F.log_softmax(z/2,-1),F.softmax(t/2,-1),reduction='sum')*4 if int(t.argmax())==r['target'] else z.sum()*0
                    loss=ce+p['teacher_KL']*kl;losses.append(loss/2);batch.append(dict(id=r['id'],view=view,CE=float(ce.detach()),teacher_KL=float(kl.detach())))
                loss=sum(losses);assert torch.isfinite(loss);loss.backward();norm=float(torch.nn.utils.clip_grad_norm_([A,B],1.));assert math.isfinite(norm)
                optimizer.step();history.append(dict(step=step,loss=float(loss.detach()),gradient_norm=norm,batch=batch))
            payload=out/(arm+'.npz')
            with payload.open('xb') as f:np.savez(f,A=A.detach().cpu().numpy(),B=B.detach().cpu().numpy(),scale=np.array(1.,np.float32))
            records=[]
            for row in rows:
                item=data[row['id'],row['view']]
                with torch.no_grad():z=(item['z']+F.linear(F.linear(item['x'],A),B)).cpu().numpy().copy()
                token=int(z.argmax());records.append(dict(id=row['id'],view=row['view'],split=row['split'],target=row['target'],token=token,correct=token==row['target'],target_gap=float(z[row['target']]-np.max(np.delete(z,row['target'])))))
            evals=dict(fixed_demo_correct=sum(r['correct'] for r in records if r['id'] in base['safe_augmentation_ids'] and r['view']=='clean'),fresh_hard_correct=sum(r['correct'] for r in records if r['view']=='moderate_check'),fit_correct=sum(r['correct'] for r in records if r['split']=='fit' and r['view']=='clean'),reserved_cal_correct=sum(r['correct'] for r in records if r['split']=='reserved-cal'))
            result['arms'][arm]=dict(evaluations=evals,records=records,history=history,adapter_path=relative(payload),adapter_sha256=sha(payload),same_initialization_sha256=hashlib.sha256(initial_A.cpu().numpy().tobytes()+initial_B.cpu().numpy().tobytes()).hexdigest())
            print('TARGET_HEAD_RESULT',arm,evals,flush=True)
        result.update(status='COMPLETE_TARGET_NUMERIC_MATCHED_HEAD_TRAINING',original_rc=0,training_scope='Only rank8 full-vocabulary head residual; frozen deployed body, no body LoRA',extra_MACs=1235968,software_cached_eval_only=True,board_quality_proven=False,base_body_unchanged=True)
    except BaseException:result['traceback']=traceback.format_exc()
    result['elapsed_s']=time.monotonic()-started;save(out/'RESULT.json',result);print(result['status'],result.get('traceback',''),flush=True);return result['original_rc']

if __name__=='__main__':
    action=sys.argv[1];assert action in ('capture','train');raise SystemExit(capture() if action=='capture' else train())
