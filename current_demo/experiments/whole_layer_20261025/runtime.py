"""Physical ModuleList contraction, original weights, compact KV indices."""
from common import *
class Experiment:
    def __init__(self,p):
        import importlib.util
        # Load the previous helper under a distinct name; it imports no hardware APIs.
        spec=importlib.util.spec_from_file_location('frozen_ps_helpers',OLD/'common.py')
        prior=importlib.util.module_from_spec(spec);spec.loader.exec_module(prior)
        # late_oracle imports its frozen common by name. Keep the two namespaces explicit.
        current=sys.modules['common'];sys.modules['common']=prior
        try:
            from late_oracle import LateOracle
            torch,vision,linear,preprocess=prior.setup()
            self.torch=torch;self.vision=vision;self.preprocess=preprocess;self.prior=prior
            self.oracle=LateOracle(torch,p['old_protocol']);self.bound=self.oracle.bind(vision)
        finally:sys.modules['common']=current
        self.hooks=[];fit=R/'M523-PS-V2-V3-V6-3072-fit-02'
        for i in (2,3,6):
            with np.load(fit/'codes'/('vision_'+str(i).zfill(2)+'.npz'),allow_pickle=False) as z:mlp,_=prior.replace_PS(torch,vision,linear,i,z)
            b=torch.from_numpy(np.frombuffer((fit/'R1'/('vision_'+str(i).zfill(2)+'_FP32.bin')).read_bytes(),np.float32).copy())
            def add(m,a,y,bias=b):return torch.add(y,bias)
            self.hooks.append(mlp.register_forward_hook(add))
        from transformers import AutoModelForCausalLM,AutoTokenizer
        from packed_checkpoint_artifact import load_packed_checkpoint
        from mage_a8_runtime import install_packed_linear_a8_hooks
        from transformers.cache_utils import DynamicCache
        from transformers.modeling_outputs import BaseModelOutputWithPooling
        from m454_cache_lifecycle02 import discard_completed_cache
        self.DynamicCache=DynamicCache;self.discard=discard_completed_cache
        cfg=read(OPT/'contracts/config.json')
        for path,row in read(R/'M454-model-interface-preflight-01/RESULT.json')['model_files'].items():assert sha(path)==row['sha256']
        self.model=AutoModelForCausalLM.from_pretrained(cfg['model'],trust_remote_code=True,local_files_only=True,torch_dtype=torch.bfloat16,low_cpu_mem_usage=True,attn_implementation='eager',device_map={'':'cpu'}).eval()
        self.model.requires_grad_(False)
        self.checkpoint=load_packed_checkpoint(torch,self.model,Path(cfg['checkpoint']),verify_blob=True,row_chunk=32)
        self.tokenizer=AutoTokenizer.from_pretrained(cfg['model'],trust_remote_code=True,local_files_only=True)
        assert self.tokenizer.encode('Yes',add_special_tokens=False)==[9454] and self.tokenizer.encode('No',add_special_tokens=False)==[2753]
        package=ROOT/p['old_protocol']['package'];plan=read(package/'TWENTYTWO_LAYER_PLAN.json')
        for row in plan['layers']:
            if not row['key'].startswith('language'):continue
            mlp=self.model.get_submodule(row['module'])
            with np.load(package/row['codes']['path'],allow_pickle=False) as z:
                for attr,stem in [('gate_proj','gate'),('up_proj','up'),('down_proj','down')]:
                    old=getattr(mlp,attr);c=z[stem+'_codes'];s=z[stem+'_scales'];dense=(c.astype(np.float32)*s.astype(np.float32)[...,None]).reshape(len(c),-1)
                    new=torch.nn.Linear(dense.shape[1],dense.shape[0],bias=False,dtype=old.weight.dtype)
                    with torch.no_grad():new.weight.copy_(torch.from_numpy(dense))
                    new.requires_grad_(False);setattr(mlp,attr,new)
            b=torch.from_numpy(np.frombuffer((package/row['R1']['path']).read_bytes(),np.float32).copy())
            def add(m,a,y,bias=b):return torch.add(y.float(),bias).to(y.dtype)
            self.hooks.append(mlp.register_forward_hook(add))
        a8,names=install_packed_linear_a8_hooks(torch,self.model,Path(cfg['checkpoint']))
        assert names==read(R/'M522-training-capture-protocol-03/RESULT.json')['A8_module_names_expected'];self.hooks+=a8
        self.visual=self.model.model.visual;self.injected=None;self.visual_calls=0
        def inject(pixel_values,*args,**kwargs):
            assert self.injected is not None and self.visual_calls==0
            assert tuple(pixel_values.shape)==(392,768)
            assert torch.equal(pixel_values,self.injected['pixels']) and torch.equal(kwargs['grid_thw'],self.injected['grid']) and torch.equal(kwargs['patch_positions'],self.injected['positions'])
            self.visual_calls+=1
            return BaseModelOutputWithPooling(last_hidden_state=self.injected['features'])
        self.visual.forward=inject
        self.language=self.model.model.language_model
        self.original_vision=list(self.vision.vision.encoder.layers);self.original_language=list(self.language.layers)
        assert len(self.original_vision)==24 and len(self.original_language)==36
        self.text_config=copy.deepcopy(self.language.config)
        self.bank={};self.counts={};self.capture=False;self.ids=p['token_ids'];self.calls=0
        for branch,modules in [('vision',self.original_vision),('language',self.original_language)]:
            for i,module in enumerate(modules):
                key=branch+'_'+str(i).zfill(2)
                def observer(m,args,out,key=key):
                    self.counts[key]=self.counts.get(key,0)+1
                    if self.capture:stats_hook(torch,self.bank,key)(m,args,out)
                self.hooks.append(module.register_forward_hook(observer))
        params=list(self.model.parameters())+list(self.vision.vision.parameters())
        self.params={id(x):(x,x._version,tuple(x.shape),x.data_ptr()) for x in params}
        self.set_active(list(range(24)),list(range(36)))
    def set_active(self,v,l):
        assert v==sorted(set(v)) and l==sorted(set(l)) and {0,1,23}<=set(v) and {0,35}<=set(l)
        torch=self.torch;self.v=list(v);self.l=list(l)
        self.vision.vision.encoder.layers=torch.nn.ModuleList([self.original_vision[i] for i in v])
        self.language.layers=torch.nn.ModuleList([self.original_language[i] for i in l])
        cfg=copy.deepcopy(self.text_config);cfg.num_hidden_layers=len(l);cfg.layer_types=[self.text_config.layer_types[i] for i in l]
        self.language.config=cfg;self.model.config.text_config=cfg;self.model.model.config.text_config=cfg
        for j,i in enumerate(l):self.original_language[i].self_attn.layer_idx=j
        assert len(self.language.layers)==len(l) and len(self.vision.vision.encoder.layers)==len(v)
    def unchanged(self):
        assert all(x._version==version and tuple(x.shape)==shape and x.data_ptr()==ptr for x,version,shape,ptr in self.params.values())
    def features(self,request):
        torch=self.torch;x=self.prior.inputs(torch,self.preprocess,request)
        self.oracle.trace=[];before=dict(self.counts)
        with torch.inference_mode():f=self.vision(x['pixel_values'].numpy(),x['image_grid_thw'].numpy(),x['patch_positions'].numpy()).copy()
        assert f.shape==(98,2560) and np.isfinite(f).all()
        assert {t['layer'] for t in self.oracle.trace}==set(self.v)&set(range(13,24))
        assert len(self.oracle.trace)==26*len(set(self.v)&set(range(13,24)))
        assert all(self.counts.get('vision_'+str(i).zfill(2),0)-before.get('vision_'+str(i).zfill(2),0)==int(i in self.v) for i in range(24))
        return f
    def answer(self,request,feature,cap):
        torch=self.torch;x=self.prior.inputs(torch,self.preprocess,request)
        self.injected=dict(features=torch.from_numpy(feature.copy()),pixels=x['pixel_values'].to(self.visual.embeddings.patch_embedding.weight.dtype),grid=x['image_grid_thw'],positions=x['patch_positions'])
        self.visual_calls=0;before=dict(self.counts);cache=self.DynamicCache(config=self.model.config.text_config)
        assert cache.get_seq_length()==0 and len(cache.layers)==len(self.l)
        generated=[];all_logits=[];t=time.monotonic()
        with torch.inference_mode():
            for step in range(cap):
                if step==0:tokens=torch.tensor([self.ids]);kw=dict(x)
                else:tokens=torch.tensor([[generated[-1]]]);kw=dict(position_ids=torch.tensor([[128+step-1]]),cache_position=torch.tensor([128+step-1]))
                output=self.model(**kw,input_ids=tokens,attention_mask=torch.ones((1,128+step),dtype=torch.long),past_key_values=cache,use_cache=True,logits_to_keep=1)
                assert output.past_key_values is cache and cache.get_seq_length()==128+step
                z=output.logits[0,-1].float().numpy().copy();assert z.shape==(151936,) and np.isfinite(z).all()
                all_logits.append(z);generated.append(int(z.argmax()))
                if generated[-1]==151645:break
        assert self.visual_calls==1
        counts={}
        for i in range(36):
            key='language_'+str(i).zfill(2);counts[key]=self.counts.get(key,0)-before.get(key,0)
            assert counts[key]==(len(generated) if i in self.l else 0)
        cache_shapes=[dict(compact_index=j,original_layer=i,key_shape=list(cache.layers[j].keys.shape),value_shape=list(cache.layers[j].values.shape)) for j,i in enumerate(self.l)]
        assert all(s['key_shape'][2]==128+len(generated)-1 for s in cache_shapes)
        self.discard(torch,cache);assert cache.get_seq_length()==0
        self.unchanged();self.calls+=1
        return dict(request_id=request['id'],text=self.tokenizer.decode(generated,skip_special_tokens=True,clean_up_tokenization_spaces=False),token_ids=generated,ended_with_eos=generated[-1]==151645,reached_cap=generated[-1]!=151645,first_decision=decision(all_logits[0]),correct_first_token=correct(all_logits[0],request['knife_present']),correct_direction_pp=margin(all_logits[0],request['knife_present']),cache_initial=0,cache_cleared=0,cache_layers=cache_shapes,layer_calls=counts,software_seconds=time.monotonic()-t),np.stack(all_logits)
    def close(self):
        for h in self.hooks:h.remove()
        self.vision.close()
