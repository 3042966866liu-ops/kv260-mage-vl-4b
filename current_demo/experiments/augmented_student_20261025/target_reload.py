"""Fresh full student forwards with the actual portable exported FP32 residual."""
from common_joint import *
import traceback
import numpy as np

def main():
    import torch
    from learned_head import LearnedHead
    protofile=RUNS/(PREFIX+'-target-head-reload-protocol-01/RESULT.json');p=read(protofile);assert sha(__file__)==p['source_sha256']
    base=read(RUNS/(PREFIX+'-protocol-02/RESULT.json'));cap=read(RUNS/(PREFIX+'-target-head-capture-01/RESULT.json'));training=read(RUNS/(PREFIX+'-target-head-training-01/RESULT.json'))
    assert sha(RUNS/(PREFIX+'-target-head-training-01/RESULT.json'))==p['training_result_sha256']
    package=ROOT/p['package'];assert sha(package/'PACKAGE_MANIFEST.json')==p['manifest_sha256'] and sha(package/'HEAD_MANIFEST.json')==p['head_manifest_sha256']
    manifest=read(package/'HEAD_MANIFEST.json');assert sha(HERE/'learned_head.py')==manifest['source_sha256']
    head=LearnedHead(package,manifest);expected={(r['id'],r['view']):r for r in training['arms'][p['selected_arm']]['records']}
    for row in cap['records']:
        file=ROOT/row['payload'];assert sha(file)==row['sha256']
        with np.load(file,allow_pickle=False) as z:y=head.add(z['x'][None],z['z'][None])[0]
        assert int(y.argmax())==expected[row['id'],row['view']]['token']
    out=RUNS/(PREFIX+'-target-head-reload-01');assert not out.exists();out.mkdir();started=time.monotonic();e=None
    result=dict(status='FAIL_REAL_FULL_STUDENT_PORTABLE_HEAD_RELOAD',original_rc=1,samples=[],component_cached24_argmax_identical=True,board_actions=0,heldout_opened=False)
    try:
        e=engine_class()(base['runtime_protocol']);e.set_active(base['vision'],base['language']);hidden={}
        def before(module,args):hidden['x']=args[0].detach().float().numpy().reshape(-1,2560)[-1:].copy()
        def after(module,args,y):return torch.from_numpy(head.add(hidden.pop('x'),y.detach().float().numpy().reshape(1,151936))).reshape(y.shape)
        e.hooks.extend([e.model.lm_head.register_forward_pre_hook(before,prepend=True),e.model.lm_head.register_forward_hook(after)])
        requests=[r for r in cap['records'] if r['view']=='moderate_check' or r['view']=='clean' and (r['id'] in base['safe_augmentation_ids'] or r['split']=='reserved-cal')]
        assert len(requests)==12
        for row in requests:
            file=ROOT/row['frame'];assert sha(file)==row['frame_sha256'];frame=np.load(file,allow_pickle=False)
            arrays=e.preprocess(np.ascontiguousarray(frame[None]));x={k:torch.from_numpy(v.copy()) for k,v in arrays.items()};e.oracle.trace=[]
            with torch.inference_mode():
                f=e.vision(arrays['pixel_values'],arrays['image_grid_thw'],arrays['patch_positions']);assert f.shape==(98,2560)
                e.injected=dict(features=torch.from_numpy(f.copy()),pixels=x['pixel_values'].to(e.visual.embeddings.patch_embedding.weight.dtype),grid=x['image_grid_thw'],positions=x['patch_positions']);e.visual_calls=0
                z=e.model(**x,input_ids=torch.tensor([base['token_ids']]),attention_mask=torch.ones((1,128),dtype=torch.long),use_cache=False,logits_to_keep=1).logits[0,-1].float().numpy().copy()
            token=int(z.argmax());assert token==expected[row['id'],row['view']]['token']
            record=dict(id=row['id'],view=row['view'],split=row['split'],token=token,target=row['target'],correct=token==row['target'],full_vocab=151936)
            with (out/(row['id']+'_'+row['view']+'.logits.npy')).open('xb') as stream:np.save(stream,z,allow_pickle=False)
            result['samples'].append(record);print('REAL_RELOAD',record,flush=True)
        e.unchanged();result.update(status='COMPLETE_REAL_FULL_STUDENT_PORTABLE_HEAD_RELOAD',original_rc=0,fixed_demo_correct=sum(r['correct'] for r in result['samples'] if r['view']=='clean' and r['split']=='fit'),fresh_hard_correct=sum(r['correct'] for r in result['samples'] if r['view']=='moderate_check'),reserved_cal_correct=sum(r['correct'] for r in result['samples'] if r['split']=='reserved-cal'),source_body_unchanged=True,board_quality_proven=False)
    except BaseException:result['traceback']=traceback.format_exc()
    finally:
        if e:e.close()
        result['elapsed_s']=time.monotonic()-started;save(out/'RESULT.json',result);print(result['status'],result.get('traceback',''),flush=True)
    return result['original_rc']
if __name__=='__main__':raise SystemExit(main())
