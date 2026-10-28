"""Bounded global-only versus original two-view fixed-demo quality comparison.

No training, token mask, new compensation, prompt search, or hardware APIs.
"""
import sys,json,hashlib,time,traceback,ast,inspect,textwrap,copy,types
from pathlib import Path
import numpy as np
ROOT=Path(__file__).resolve().parents[2];OPT=ROOT/'deployment/mage_vl4b/optimization_v1';RUNS=OPT/'runs'
TASK=Path(__file__).resolve().parent;OUT=RUNS/'M531-single-global-view-quality-01'
def read(p):return json.loads(Path(p).read_bytes())
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def rel(p):return Path(p).relative_to(ROOT).as_posix()
def save(p,v):p.open('x',encoding='utf8').write(json.dumps(v,ensure_ascii=False,indent=2,allow_nan=False)+'\n')
def digest(a):return hashlib.sha256(np.ascontiguousarray(a).tobytes()).hexdigest()
def render(views):return '<|im_start|>system\nYou are a helpful assistant.<|im_end|>\n<|im_start|>user\n'+('<|vision_start|>'+'<|image_pad|>'*49+'<|vision_end|>')*views+'Is a knife visible in these views'+'<|im_end|>\n<|im_start|>assistant\n'
def imports():
    sys.path.insert(0,str(ROOT/'experiments/augmented_student_20261025'))
    from common_joint import engine_class
    return engine_class()
def main():
    p=read(RUNS/'M531-single-global-view-quality-protocol-01/RESULT.json')
    for n,h in p['frozen'].items():assert sha(ROOT/n)==h,n
    Engine=imports()
    if sys.argv[-1]=='smoke':
        import torch
        assert torch.cuda.is_available();print('PASS_ISOLATED_SINGLE_VIEW_IMPORT_CUDA_ZERO_MODEL',flush=True);return 0
    assert not OUT.exists();OUT.mkdir();started=time.monotonic();e=None
    result=dict(status='FAIL_SINGLE_GLOBAL_VIEW_QUALITY',primary_rc=1,samples=[],new_board_commands=0,new_training=0,heldout_opened=False)
    try:
        import torch
        from transformers.modeling_outputs import BaseModelOutputWithPooling
        base=read(RUNS/'M525-joint-augmented-student-128-protocol-02/RESULT.json')
        pkg=OPT/'candidates/M523-fixed-demo-subset-board-07';plan=read(pkg/'DEMO_BOARD_PLAN.json')
        sys.path.insert(0,str(pkg));from learned_head import LearnedHead
        head=LearnedHead(pkg,read(pkg/'HEAD_MANIFEST.json'))
        e=Engine(base['runtime_protocol']);e.set_active(plan['retained_vision'],plan['retained_language'])
        hidden={}
        def observe(module,args):hidden['x']=args[0].detach().float().cpu().numpy().reshape(-1,2560)[-1:].copy()
        e.hooks.append(e.model.lm_head.register_forward_pre_hook(observe,prepend=True))
        # Only the request row bound changes in the frozen visual oracle; every
        # packet, integer dot, scaling, FP16/FTZ, parser and retry stays original.
        original_run=e.oracle.run;tree=ast.parse(textwrap.dedent(inspect.getsource(original_run)))
        expected=copy.deepcopy(tree);hits=[]
        class ChangeRows(ast.NodeTransformer):
            def visit_Constant(self,node):
                if type(node.value) is int and node.value==392:hits.append(node);return ast.copy_location(ast.Constant(196),node)
                return node
        changed=ChangeRows().visit(copy.deepcopy(tree));assert len(hits)==2
        namespace=dict(original_run.__func__.__globals__);exec(compile(ast.fix_missing_locations(changed),'<single_view_original_oracle_rows>','exec'),namespace)
        single_run=types.MethodType(namespace['run'],e.oracle)
        # The existing injection guard is independently narrowed to one view.
        def inject(pixels,*args,**kwargs):
            assert e.injected is not None and e.visual_calls==0 and tuple(pixels.shape) in ((196,768),(392,768))
            assert torch.equal(pixels,e.injected['pixels']) and torch.equal(kwargs['grid_thw'],e.injected['grid']) and torch.equal(kwargs['patch_positions'],e.injected['positions'])
            e.visual_calls+=1;return BaseModelOutputWithPooling(last_hidden_state=e.injected['features'])
        e.visual.forward=inject
        ids2=e.tokenizer.encode(render(2),add_special_tokens=False);ids1=e.tokenizer.encode(render(1),add_special_tokens=False)
        assert ids2==plan['token_ids'] and len(ids1)==77 and ids1.count(151655)==49
        for arm,views,ids in [('two_view_control',2,ids2),('single_global',1,ids1)]:
            e.oracle.run=original_run if views==2 else single_run
            for request in plan['demo_requests']:
                file=pkg/request['frame_path'];assert sha(file)==request['frame_sha256'];frame=np.load(file,allow_pickle=False)
                arrays=e.preprocess(np.ascontiguousarray(frame[None]))
                if views==1:
                    arrays={k:(a[:196].copy() if k in ('pixel_values','patch_positions') else a[:1].copy() if k=='image_grid_thw' else np.array(49 if k=='merged_visual_tokens' else 1,dtype=a.dtype)) for k,a in arrays.items()}
                count=196*views;assert arrays['pixel_values'].shape==(count,768) and int(arrays['view_count'])==views
                x={k:torch.from_numpy(a.copy()) for k,a in arrays.items()};e.oracle.trace=[];e.visual_calls=0;before=dict(e.counts);tick=time.monotonic()
                with torch.inference_mode():
                    # Same frozen M273 body call, with explicit dynamic geometry.
                    f=e.vision.vision(x['pixel_values'].to(e.vision.compute_dtype),grid_thw=x['image_grid_thw'],patch_positions=x['patch_positions']).last_hidden_state.float().cpu().numpy().copy()
                    assert f.shape==(49*views,2560) and np.isfinite(f).all()
                    expected_linear_calls=2*((count+31)//32)*len(set(plan['retained_vision'])&set(range(13,24)))
                    assert len(e.oracle.trace)==expected_linear_calls
                    assert {r['layer'] for r in e.oracle.trace}==set(plan['retained_vision'])&set(range(13,24))
                    e.injected=dict(features=torch.from_numpy(f),pixels=x['pixel_values'].to(e.visual.embeddings.patch_embedding.weight.dtype),grid=x['image_grid_thw'],positions=x['patch_positions'])
                    cache=e.DynamicCache(config=e.model.config.text_config);assert cache.get_seq_length()==0
                    try:
                        output=e.model(**x,input_ids=torch.tensor([ids]),attention_mask=torch.ones((1,len(ids)),dtype=torch.long),past_key_values=cache,use_cache=True,logits_to_keep=1)
                        assert output.past_key_values is cache and cache.get_seq_length()==len(ids) and len(cache.layers)==18
                        z0=output.logits[0,-1].float().cpu().numpy().copy();z=head.add(hidden.pop('x'),z0[None])[0]
                        shapes=[dict(original_layer=i,key_shape=list(cache.layers[j].keys.shape),value_shape=list(cache.layers[j].values.shape)) for j,i in enumerate(plan['retained_language'])]
                        assert all(r['key_shape'][2]==len(ids) and r['value_shape'][2]==len(ids) for r in shapes)
                    finally:e.discard(torch,cache)
                assert cache.get_seq_length()==0 and e.visual_calls==1 and z.shape==(151936,) and np.isfinite(z).all()
                for branch,size,active in [('vision',24,plan['retained_vision']),('language',36,plan['retained_language'])]:
                    for i in range(size):
                        key=branch+'_'+str(i).zfill(2);assert e.counts.get(key,0)-before.get(key,0)==int(i in active)
                token=int(z.argmax());raw=e.tokenizer.decode([token],skip_special_tokens=True);decision={'yes':'Yes','true':'Yes','no':'No','false':'No'}.get(raw.strip().casefold().rstrip('.,!?;:'),'Invalid')
                key=arm+'_'+request['id'];payload=OUT/(key+'.npz')
                with payload.open('xb') as stream:np.savez(stream,features=f,base_logits=z0,logits=z)
                pp=np.exp(z.astype(np.float64)-float(z.max()));pp/=pp.sum();sign=1 if request['expected_decision']=='Yes' else -1
                row=dict(arm=arm,id=request['id'],frame_sha256=sha(file),tokens=len(ids),views=views,vision_patch_rows=count,vision_oracle_logical_calls=len(e.oracle.trace),token=token,raw_token=raw,decision=decision,expected=request['expected_decision'],correct=decision==request['expected_decision'],correct_direction_pp=float((pp[9454]-pp[2753])*sign*100),full_vocab=151936,cache_before=0,cache_after_clear=0,cache_shapes=shapes,payload=rel(payload),sha256=sha(payload),parameter_versions_unchanged=True,software_elapsed_s=time.monotonic()-tick)
                e.unchanged();result['samples'].append(row);save(OUT/(key+'.json'),row);print('SINGLE_VIEW_QUALITY',arm,request['id'],raw,row['correct'],row['correct_direction_pp'],flush=True)
        assert len(result['samples'])==8 and head.calls==8
        controls=[r for r in result['samples'] if r['arm']=='two_view_control'];single=[r for r in result['samples'] if r['arm']=='single_global']
        result.update(status='COMPLETE_SINGLE_GLOBAL_VIEW_SOFTWARE_QUALITY',primary_rc=0,control_correct=sum(r['correct'] for r in controls),single_correct=sum(r['correct'] for r in single),control_count=4,single_count=4,single_fixed_demo_pass=all(r['correct'] for r in controls+single),full_prefills=8,decode_calls=0,constant_only_oracle_transform=dict(from_rows=392,to_rows=196,changed_literals=len(hits),original_ast_sha256=hashlib.sha256(ast.dump(expected).encode()).hexdigest(),changed_ast_sha256=hashlib.sha256(ast.dump(changed).encode()).hexdigest()),head_calls=head.calls,head_A_sha256=sha(pkg/'A.npy'),head_B_sha256=sha(pkg/'B.npy'),body_and_head_unchanged=True,software_seconds_not_board_TTFT=True,board_speedup_proven=False)
    except BaseException:result['traceback']=traceback.format_exc()
    finally:
        if e:e.close()
        result['elapsed_s']=time.monotonic()-started;save(OUT/'RESULT.json',result);print(result['status'],result.get('traceback',''),flush=True)
    return result['primary_rc']
if __name__=='__main__':raise SystemExit(main())
