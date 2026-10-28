"""Same current22 software language path, injected new software A/B visual features.

The vision evidence is explicitly software PS plus late M455 oracle; native A53 validation is pending. Language remains the explicitly limited
BF16+A8 development execution, not exact whole-model M455 arithmetic.
"""
import hashlib,json,os,shutil,sys,time,traceback
from pathlib import Path
import numpy as np
sys.dont_write_bytecode=True
H=Path(__file__).resolve().parent;ROOT=H.parents[1];OPT=ROOT/'deployment/mage_vl4b/optimization_v1';R=OPT/'runs'
sys.path[:0]=[str(ROOT/'experiments/speed_target_30s_20261020'),str(ROOT/'deployment/mage_vl4b/scripts'),
    str(ROOT/'deployment/mage_vl4b/m276_short_prompt_source'),str(ROOT/'deployment/mage_vl4b/m273_latest_binary_source'),str(ROOT/'scripts/optimization')]
from generate_flap522 import read,sha,save
PREP=R/'M523-PS-V2-V3-V6-3072-protocol-02/RESULT.json';OUT=R/'M523-PS-V2-V3-V6-3072-quality-01'

def main():
    p=read(PREP)
    for n,h in p['frozen'].items():assert sha(ROOT/n)==h,n
    feature_root=R/'M523-PS-V2-V3-V6-3072-features-01'
    feature_result=read(feature_root/'RESULT.json')
    assert feature_result['original_rc']==0 and feature_result['feature_gate_pass'],'Complete feature gate must pass first'
    for row in feature_result['files']:assert sha(feature_root/row['path'])==row['sha256']
    for request in p['requests']:
        request['features']={arm:dict(path=(feature_root/arm/request['id']/'features_FP32.npy').relative_to(ROOT).as_posix(),sha256=sha(feature_root/arm/request['id']/'features_FP32.npy')) for arm in ('A','B')}

    assert not OUT.exists();OUT.mkdir();started=time.monotonic()
    v=dict(status='FAIL_PS_V236_3072_FEATURE_SOFTWARE_LANGUAGE_ANSWERS',original_rc=1,cases=[],sequences=0,
        source_sha256=sha(__file__),protocol_sha256=sha(PREP),heldout_model_calls=0,training_steps=0,board_commands=0,
        quality_pass=False,exact_M455_whole_model_arithmetic=False,
        scope='WSL actual PS runtime plus unchanged late M455 oracle current22/PS3072 A/B features; identical packed BF16+A8 software language execution. FP32 features cast at original model embedding boundary. Not exact M455 language or board timing.')
    model=None;a8=[];handles=[];caches=[];visual=None;old_visual_owned=False;old_visual_forward=None;selected=None;visual_calls=0
    try:
        mem={k:int(x.split()[0])*1024 for k,x in (line.split(':',1) for line in Path('/proc/meminfo').read_text().splitlines())}
        assert mem['MemAvailable']>=12<<30 and shutil.disk_usage(OUT).free>=2<<30
        import torch
        from transformers import AutoModelForCausalLM,AutoTokenizer
        from transformers.cache_utils import DynamicCache
        from transformers.modeling_outputs import BaseModelOutputWithPooling
        from packed_checkpoint_artifact import load_packed_checkpoint
        from mage_a8_runtime import install_packed_linear_a8_hooks
        from m276_prompt_contract import preprocess
        from m454_cache_lifecycle02 import discard_completed_cache
        torch.set_num_threads(16);torch.set_num_interop_threads(1);torch.manual_seed(523115)
        torch.backends.cuda.matmul.allow_tf32=False;torch.backends.cudnn.allow_tf32=False
        cfg=read(OPT/'contracts/config.json');pf=read(R/'M454-model-interface-preflight-01/RESULT.json')
        for n,row in pf['model_files'].items():assert sha(Path(n))==row['sha256']
        model=AutoModelForCausalLM.from_pretrained(cfg['model'],trust_remote_code=True,local_files_only=True,torch_dtype=torch.bfloat16,
            low_cpu_mem_usage=True,attn_implementation='eager',device_map={'':'cpu'}).eval();model.requires_grad_(False)
        v['checkpoint']=load_packed_checkpoint(torch,model,Path(cfg['checkpoint']),verify_blob=True,row_chunk=32)
        tokenizer=AutoTokenizer.from_pretrained(cfg['model'],trust_remote_code=True,local_files_only=True)
        v['decision_token_ids']={word:tokenizer.encode(word,add_special_tokens=False) for word in ('Yes','No','Unclear')}
        package=ROOT/p['package'];plan=read(package/'TWENTYTWO_LAYER_PLAN.json')
        layers=[r for r in plan['layers'] if r['key'].startswith('language')];assert len(layers)==19
        counts={};swaps=[];biases={}
        for row in layers:
            parent=model.get_submodule(row['module']);file=package/row['codes']['path'];assert sha(file)==row['codes']['sha256']
            with np.load(file,allow_pickle=False) as z:
                for attr,stem in [('gate_proj','gate'),('up_proj','up'),('down_proj','down')]:
                    old=getattr(parent,attr);c=z[stem+'_codes'];s=z[stem+'_scales'];dense=(c.astype(np.float32)*s.astype(np.float32)[...,None]).reshape(len(c),-1)
                    new=torch.nn.Linear(dense.shape[1],dense.shape[0],bias=False,device='cpu',dtype=old.weight.dtype)
                    with torch.no_grad():new.weight.copy_(torch.from_numpy(dense))
                    new.requires_grad_(False);swaps.append((parent,attr,old));setattr(parent,attr,new)
            b=row['R1'];raw=(package/b['path']).read_bytes();assert hashlib.sha256(raw).hexdigest()==b['sha256']
            biases[row['key']]=torch.from_numpy(np.frombuffer(raw,np.float32).copy())
            def correct(_m,args,y,key=row['key']):
                counts[key]=counts.get(key,0)+1
                return torch.add(y.float(),biases[key]).to(y.dtype)
            handles.append(parent.register_forward_hook(correct))
        assert len(swaps)==57
        a8,names=install_packed_linear_a8_hooks(torch,model,Path(cfg['checkpoint']))
        assert names==read(R/'M522-training-capture-protocol-03/RESULT.json')['A8_module_names_expected']
        visual=model.get_submodule('model.visual');old_visual_owned='forward' in visual.__dict__;old_visual_forward=visual.__dict__.get('forward')
        def native_features(pixel_values,*args,**kwargs):
            nonlocal visual_calls
            assert selected is not None and visual_calls==0
            assert tuple(pixel_values.shape)==(392,768) and torch.equal(pixel_values,selected['pixels'])
            assert torch.equal(kwargs['grid_thw'],selected['grid']) and torch.equal(kwargs['patch_positions'],selected['positions'])
            visual_calls+=1
            return BaseModelOutputWithPooling(last_hidden_state=selected['features'])
        visual.forward=native_features
        versions=[(n,z._version,tuple(z.shape),str(z.dtype),z.data_ptr()) for n,z in model.named_parameters()]
        total_bytes=0
        for request in p['requests']:
            frames=ROOT/request['frames'];assert sha(frames)==request['frames_sha256']
            array=np.load(frames,allow_pickle=False);assert array.shape==(2,448,448,3)
            pixels=preprocess(array[request['timestamp_index']:request['timestamp_index']+1]);vision={k:torch.from_numpy(a.copy()) for k,a in pixels.items()}
            ids=p['token_ids'];assert len(ids)==160 and ids.count(151655)==98
            for arm in ('A','B'):
                assert time.monotonic()-started<=p['budget_seconds'] and v['sequences']<24
                feature=ROOT/request['features'][arm]['path'];assert sha(feature)==request['features'][arm]['sha256']
                f=np.load(feature,allow_pickle=False);assert f.shape==(98,2560) and f.dtype==np.float32 and np.isfinite(f).all()
                selected=dict(features=torch.from_numpy(f.copy()),pixels=vision['pixel_values'].to(visual.embeddings.patch_embedding.weight.dtype),
                    grid=vision['image_grid_thw'],positions=vision['patch_positions'])
                visual_calls=0;counts.clear();folder=OUT/arm/request['id'];folder.mkdir(parents=True)
                cache=DynamicCache(config=model.config.text_config);assert cache.get_seq_length()==0 and all(cache is not old for old in caches)
                caches.append(cache);generated=[];logits=[];tick=time.monotonic()
                with torch.inference_mode():
                    for step in range(32):
                        if step==0:tokens=torch.tensor([ids]);kwargs=dict(vision)
                        else:tokens=torch.tensor([[generated[-1]]]);kwargs=dict(position_ids=torch.tensor([[160+step-1]]),cache_position=torch.tensor([160+step-1]))
                        output=model(**kwargs,input_ids=tokens,attention_mask=torch.ones((1,160+step),dtype=torch.long),
                            past_key_values=cache,use_cache=True,logits_to_keep=1)
                        assert output.past_key_values is cache and cache.get_seq_length()==160+step
                        z=output.logits[0,-1].float().numpy().copy();assert z.shape==(151936,) and np.isfinite(z).all()
                        logits.append(z);generated.append(int(z.argmax()))
                        if generated[-1]==p['eos_id']:break
                assert visual_calls==1 and all(counts.get(r['key'])==len(generated) for r in layers)
                text=tokenizer.decode(generated,skip_special_tokens=True,clean_up_tokenization_spaces=False)
                values=np.stack(logits);total_bytes+=values.nbytes;assert total_bytes<=512<<20
                with (folder/'logits.npy').open('xb') as stream:np.save(stream,values,allow_pickle=False)
                before=cache.get_seq_length();assert before==160+len(generated)-1
                discard_completed_cache(torch,cache);assert cache.get_seq_length()==0
                result=dict(arm=arm,request_id=request['id'],text=text,token_ids=generated,token_count=len(generated),
                    ended_with_eos=generated[-1]==p['eos_id'],reached_cap=generated[-1]!=p['eos_id'],
                    software_feature_sha256=sha(feature),feature_embedding_boundary_dtype=str(visual.embeddings.patch_embedding.weight.dtype),
                    full_logits_sha256=sha(folder/'logits.npy'),MLP_calls=dict(counts),injected_visual_calls=visual_calls,
                    cache_initial_length=0,cache_final_length=before,cache_cleared_length=0,cache_ordinal=len(caches)-1,
                    software_wall_s=time.monotonic()-tick,software_timing_not_FPGA=True,free_answer=True,teacher_forced=False)
                save(folder/'RESULT.json',result);v['cases'].append(result);v['sequences']+=1
                assert versions==[(n,z._version,tuple(z.shape),str(z.dtype),z.data_ptr()) for n,z in model.named_parameters()]
                print('PS_V236_3072_FEATURE_ANSWER',request['id'],arm,repr(text),len(generated),'EOS' if result['ended_with_eos'] else 'CAP',flush=True)
        assert v['sequences']==24 and all(c.get_seq_length()==0 for c in caches)
        v.update(status='COMPLETE_PS_V236_3072_FEATURE_SOFTWARE_LANGUAGE_ANSWERS_REVIEW_PENDING',original_rc=0,
            all_caches_independent_and_cleared=True,parameter_updates=0,actual_input_tokens=160,cap=32,heldout_still_closed=True)
    except BaseException:v['traceback']=traceback.format_exc()
    finally:
        for handle in handles+a8:handle.remove()
        if visual is not None:
            if old_visual_owned:visual.forward=old_visual_forward
            elif 'forward' in visual.__dict__:del visual.__dict__['forward']
        model=None;v['elapsed_s']=time.monotonic()-started;save(OUT/'RESULT.json',v)
        print(v['status'],v.get('traceback',''),flush=True)
    return v['original_rc']
if __name__=='__main__':raise SystemExit(main())
