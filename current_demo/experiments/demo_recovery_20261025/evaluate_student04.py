"""Evaluate composed HP merge and exported mixed-bit weights, no board claims."""
from common_recovery import *
import traceback,gc,types

def main():
    import numpy as np,torch
    import torch.nn.functional as F
    p=read(RUNS/(PREFIX+'-protocol-01/RESULT.json'));trained=RUNS/(PREFIX+'-local-LoRA-01/RESULT.json');t=read(trained)
    assert t['original_rc']==0 and len(t['blocks'])==41
    protocol=read(RUNS/(PREFIX+'-evaluation-protocol-04/RESULT.json'));assert protocol['source_sha256']==sha(__file__) and protocol['training_result_sha256']==sha(trained)
    out=RUNS/(PREFIX+'-composed-evaluation-04');assert not out.exists();out.mkdir()
    value=dict(status='FAIL_COMPOSED_STUDENT_EVALUATION',original_rc=1,arms={},new_board_actions=0,heldout_opened=False);engine=None;began=time.monotonic()
    try:
        engine_class()
        from mixed_bit_checkpoint import unpack_unsigned_codes,unpack_orientation_bits
        from adaptive.language_mlp_probe import PackedChain
        requests=p['train_requests']+p['development_requests'];assert len(requests)==12
        for mode in ('high_precision_merge',):
            print('RECOVERY_COMPOSED_LOAD',mode,flush=True);engine=engine_class()(p['runtime_protocol']);assert len(engine.vision.vision.encoder.layers)==24
            for record in t['blocks']:
                folder=(ROOT/record['result']).parent;r=read(folder/'RESULT.json');assert sha(folder/'RESULT.json')==record['sha256']
                branch,index=r['key'].rsplit('_',1);i=int(index)
                block=engine.prior.inner(engine.vision,i) if branch=='vision' else engine.original_language[i]
                if mode=='high_precision_merge':
                    assert sha(folder/'ADAPTERS.pt')==r['adapter_sha256'];adapters=torch.load(folder/'ADAPTERS.pt',map_location='cpu',weights_only=True)
                for m in r['modules']:
                    name=m['name'];module=block.get_submodule(name)
                    if mode=='high_precision_merge':
                        a=adapters[name]
                        if branch=='language':base=module.weight.detach().float()
                        else:
                            base=torch.from_numpy(module.store.decode(module.name).copy())
                            if i in engine.oracle.crops and name=='mlp.fc1':base=base[torch.from_numpy(engine.oracle.crops[i])]
                            if i in engine.oracle.crops and name=='mlp.fc2':base=base[:,torch.from_numpy(engine.oracle.crops[i])]
                        assert list(base.shape)==m['shape'];dense=base.contiguous()  # Matched precision control: zero adapter delta.
                    else:
                        files=m['files']
                        for entry in files.values():assert sha(ROOT/entry['path'])==entry['sha256']
                        shape=m['shape'];u=unpack_unsigned_codes((ROOT/files['codes.bin']['path']).read_bytes(),m['bits'],shape[0]*shape[1]).reshape(shape[0],shape[1]//64,64)
                        s=np.frombuffer((ROOT/files['scales_fp16.bin']['path']).read_bytes(),'<f2').reshape(shape[0],shape[1]//64).copy()
                        o=unpack_orientation_bits((ROOT/files['orientation.bin']['path']).read_bytes(),s.size).reshape(s.shape)
                        low=np.where(o!=0,-(1<<(m['bits']-1))+1,-(1<<(m['bits']-1)))
                        codes=(u.astype(np.int16)+low[...,None]).astype(np.int8)
                        dense=torch.from_numpy((codes.astype(np.float32)*s.astype(np.float32)[...,None]).reshape(shape))
                    if branch=='language':
                        if mode=='high_precision_merge':module._forward_pre_hooks.clear()
                        with torch.no_grad():module.weight.copy_(dense.to(module.weight.dtype))
                    elif mode=='target_format_export' and i>=13 and name.startswith('mlp.fc'):
                        part=name.split('.')[-1];chain=PackedChain([(m['global_name'] if 'global_name' in m else 'model.visual.encoder.layers.'+str(i)+'.'+name,codes,s)],device='cuda')
                        chain.dense=engine.oracle.factory['modules']['m455_runtime_abi01'].convert_chain(chain.chain);engine.oracle.chains[i,part]=chain
                    elif mode=='target_format_export':module.store=engine.prior.CropStore(dense.numpy())
                    else:
                        bias=None if module.bias is None else module.bias.detach().float().clone()
                        if i in engine.oracle.crops and name=='mlp.fc1':bias=bias[torch.from_numpy(engine.oracle.crops[i])]
                        if i in engine.oracle.r1 and name=='mlp.fc2':bias=bias+torch.from_numpy(engine.oracle.r1[i])
                        dtype=module.output_dtype
                        def forward(x,weight=dense,bias=bias,dtype=dtype):return F.linear(x.float(),weight,bias).to(dtype)
                        module.forward=forward
            if mode=='high_precision_merge':engine.model.lm_head._forward_pre_hooks.clear()
            engine.set_active(p['student']['vision'],p['student']['language'])
            samples=[]
            for request in requests:
                print('RECOVERY_COMPOSED_BEGIN',mode,request['id'],flush=True)
                torch=engine.torch;x=engine.prior.inputs(torch,engine.preprocess,request)
                with torch.inference_mode():
                    feature=engine.vision(x['pixel_values'].numpy(),x['image_grid_thw'].numpy(),x['patch_positions'].numpy())
                    if mode=='target_format_export':
                        assert {r['layer'] for r in engine.oracle.trace[-26*len(set(engine.v)&set(range(13,24))):]}==set(engine.v)&set(range(13,24))
                    engine.injected=dict(features=torch.from_numpy(feature.copy()),pixels=x['pixel_values'].to(engine.visual.embeddings.patch_embedding.weight.dtype),grid=x['image_grid_thw'],positions=x['patch_positions']);engine.visual_calls=0
                    z=engine.model(**x,input_ids=torch.tensor([p['token_ids']]),attention_mask=torch.ones((1,128),dtype=torch.long),use_cache=False,logits_to_keep=1).logits[0,-1].float().numpy().copy()
                assert z.shape==(151936,) and np.isfinite(z).all() and feature.shape==(98,2560) and engine.visual_calls==1
                token=int(z.argmax());text=engine.tokenizer.decode([token],skip_special_tokens=True).strip();answer={'yes':'Yes','true':'Yes','no':'No','false':'No'}.get(text.casefold().rstrip('.,!?;:'),'Invalid')
                expected='Yes' if request['knife_present'] else 'No';folder=out/mode/request['id'];folder.mkdir(parents=True)
                for filename,array in [('first_logits.npy',z),('visual_features.npy',feature)]:
                    with (folder/filename).open('xb') as stream:np.save(stream,array,allow_pickle=False)
                row=dict(request_id=request['id'],split='fit' if request in p['train_requests'] else 'reserved-cal',expected=expected,actual_token=token,raw_first_token=text,decision=answer,correct=answer==expected,No_minus_Yes_raw_logit=float(z[2753]-z[9454]),first_logits_sha256=sha(folder/'first_logits.npy'),features_sha256=sha(folder/'visual_features.npy'),board_TTFT=None)
                save(folder/'RESULT.json',row);samples.append(row);print('RECOVERY_COMPOSED_SAVED',mode,row,flush=True)
            value['arms'][mode]=dict(samples=samples,fit_correct=sum(r['correct'] for r in samples if r['split']=='fit'),reserved_cal_correct=sum(r['correct'] for r in samples if r['split']=='reserved-cal'),fixed_demo_correct=sum(r['correct'] for r in samples if r['request_id'] in ('cal_00_t0','cal_00_t1','cal_04_t0','cal_04_t1')))
            engine.close();engine=None;gc.collect();torch.cuda.empty_cache()
        value.update(status='COMPLETE_UNTRAINED_HP_PRECISION_CONTROL',original_rc=0,student_original_shape='14V27L',actual_new_model_prefills=12,adapter_delta_applied=False,board_quality_proven=False,board_speed_proven=False)
    except BaseException:value['traceback']=traceback.format_exc()
    finally:
        if engine:engine.close()
        value['elapsed_s']=time.monotonic()-began;save(out/'RESULT.json',value);print(value['status'],value.get('traceback',''),flush=True)
    return value['original_rc']
if __name__=='__main__':raise SystemExit(main())
