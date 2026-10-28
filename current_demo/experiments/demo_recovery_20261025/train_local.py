"""Short all-retained-block LoRA KD. Frozen teacher cache; one GPU block.

This is local/teacher-forced hierarchical recovery, not end-to-end joint QAT.
FP32 surrogate evaluation and actual mixed-bit serialization are separate.
"""
from common_recovery import *
import gc,os,traceback,types

def main():
    import torch,numpy as np
    from torch import nn
    import torch.nn.functional as F
    torch.manual_seed(524);torch.backends.cuda.matmul.allow_tf32=False;torch.backends.cudnn.allow_tf32=False
    p=read(RUNS/(PREFIX+'-protocol-01/RESULT.json'))
    freeze=read(RUNS/(PREFIX+'-training-protocol-01/RESULT.json'))
    assert sha(__file__)==freeze['training_source_sha256']
    capture=RUNS/(PREFIX+'-teacher-capture-01/RESULT.json');cache=read(capture)
    assert cache['original_rc']==0 and sha(capture)==freeze['teacher_capture_sha256']
    out=RUNS/(PREFIX+'-local-LoRA-01');assert not out.exists();out.mkdir()
    result=dict(status='FAIL_LOCAL_ALL_BLOCK_LORA_RECOVERY',original_rc=1,blocks=[],board_actions=0,heldout_opened=False,full_end_to_end_training=False)
    began=time.monotonic();engine=None
    try:
        assert torch.cuda.is_available() and torch.cuda.mem_get_info()[0]>3<<30
        device=torch.device('cuda');engine=engine_class()(p['runtime_protocol'])
        checkpoint=Path(read(OPT/'contracts/config.json')['checkpoint'])
        entries={r['module']:r for r in read(checkpoint/'CHECKPOINT_MANIFEST.json')['entries'] if 'module' in r}
        # Entry names and module keys are independently asserted below.
        byname={r['name']:r for r in read(checkpoint/'CHECKPOINT_MANIFEST.json')['entries']}
        sys.path.insert(0,str(ROOT/'deployment/mage_vl4b/scripts'))
        from mixed_bit_checkpoint import recover_full_range_rows_for_storage,pack_unsigned_codes,unpack_unsigned_codes,pack_orientation_bits,unpack_orientation_bits
        loaded=[]
        for row in cache['teacher_requests']:
            file=ROOT/row['file'];assert sha(file)==row['sha256']
            loaded.append(torch.load(file,map_location='cpu',weights_only=True))
        assert len(loaded)==8
        plan=read(OPT/'candidates/M523-M455-twentytwo-layer-R1-research-240/TWENTYTWO_LAYER_PLAN.json')
        parent_package=OPT/'candidates/M523-M455-twentytwo-layer-R1-research-240'
        planrows={r['key']:r for r in plan['layers']}
        class LoRA(nn.Module):
            def __init__(self,weight,bias,bits,name):
                super().__init__();self.register_buffer('base',weight.detach().float().to(device));self.register_buffer('bias',None if bias is None else bias.detach().float().to(device))
                self.bits=bits;self.global_name=name;rank=p['first_phase']['rank']
                self.A=nn.Parameter(torch.randn(rank,weight.shape[1],device=device)*.01)
                self.B=nn.Parameter(torch.zeros(weight.shape[0],rank,device=device));self.scale=p['first_phase']['alpha']/rank
                self.quantized=None
            def forward(self,x):
                if self.quantized is not None:return F.linear(x.float(),self.quantized,self.bias)
                return F.linear(x.float(),self.base,self.bias)+F.linear(F.linear(x.float(),self.A),self.B)*self.scale
            def merged(self):return self.base+self.B@self.A*self.scale
        def transfer(x):
            if isinstance(x,torch.Tensor):return x.to(device=device,dtype=torch.float32 if x.is_floating_point() else x.dtype)
            if isinstance(x,tuple):return tuple(transfer(y) for y in x)
            if isinstance(x,list):return [transfer(y) for y in x]
            if isinstance(x,dict):return {k:transfer(v) for k,v in x.items()}
            return x
        head=norm=None
        for branch in ('vision','language'):
            retained=p['student'][branch]
            for index,i in enumerate(retained):
                assert time.monotonic()-began<p['budgets']['training_wall_seconds']
                key=branch+'_'+str(i).zfill(2);previous=retained[index-1] if index else -1
                print('RECOVERY_BLOCK_BEGIN',key,'teacher_segment',previous+1,i,flush=True)
                original=engine.prior.inner(engine.vision,i) if branch=='vision' else engine.original_language[i]
                memo={id(m.store):m.store for m in original.modules() if hasattr(m,'store')}
                block=copy.deepcopy(original,memo).eval();block.requires_grad_(False)
                for m in block.modules():
                    m._forward_hooks.clear();m._forward_pre_hooks.clear();m._backward_hooks.clear()
                linears={}
                for name,module in list(block.named_modules()):
                    if not isinstance(module,nn.Linear) and not hasattr(module,'store'):continue
                    global_name=('model.visual.encoder.layers.' if branch=='vision' else 'model.language_model.layers.')+str(i)+'.'+name
                    bias=getattr(module,'bias',None)
                    if branch=='vision':
                        weight=torch.from_numpy(module.store.decode(module.name).copy())
                        if i in engine.oracle.crops and name.startswith('mlp.fc'):
                            row=planrows[key]
                            with np.load(parent_package/row['codes']['path'],allow_pickle=False) as z:
                                stem=name.split('.')[-1];c=z[stem+'_codes'];s=z[stem+'_scales'];weight=torch.from_numpy((c.astype(np.float32)*s.astype(np.float32)[...,None]).reshape(len(c),-1))
                            if name=='mlp.fc1':bias=bias[torch.from_numpy(engine.oracle.crops[i])]
                        bits=4
                    else:
                        weight=module.weight.detach().float();entry=byname[global_name+'.weight'];assert entry['kind']=='packed';bits=int(entry['bits'])
                    assert weight.ndim==2 and weight.shape[1]%64==0 and bits in (2,3,4)
                    if name in ('mlp.fc2','mlp.down_proj'):
                        correction=None
                        if branch=='vision' and i in (2,3,6):correction=np.frombuffer((RUNS/'M523-PS-V2-V3-V6-3072-fit-02/R1'/('vision_'+str(i).zfill(2)+'_FP32.bin')).read_bytes(),np.float32).copy()
                        elif key in planrows:
                            row=planrows[key];correction=np.frombuffer((parent_package/row['R1']['path']).read_bytes(),np.float32).copy()
                        if correction is not None:bias=(torch.zeros(weight.shape[0]) if bias is None else bias.detach().float())+torch.from_numpy(correction)
                    adapter=LoRA(weight,bias,bits,global_name);owner=block.get_submodule(name.rsplit('.',1)[0]);setattr(owner,name.split('.')[-1],adapter);linears[name]=adapter
                assert linears and any('self_attn' in n for n in linears) and any('mlp' in n for n in linears)
                block.to(device=device,dtype=torch.float32)
                trainable=[x for m in linears.values() for x in (m.A,m.B)]
                assert all(x.requires_grad for x in trainable) and sum(x.numel() for x in block.parameters() if x.requires_grad)==sum(x.numel() for x in trainable)
                if branch=='language' and i==35:
                    norm=copy.deepcopy(engine.language.norm).to(device=device,dtype=torch.float32);norm.requires_grad_(False)
                    head=engine.model.lm_head.weight.detach().to(device=device,dtype=torch.float32)
                def run(sample):
                    teacher=sample['blocks'];inp=teacher[branch+'_'+str(previous+1).zfill(2)]['args'][0]
                    meta=teacher[key];args=(transfer(inp),*transfer(meta['args'][1:]));kwargs=transfer(meta['kwargs'])
                    y=block(*args,**kwargs);y=y[0] if isinstance(y,tuple) else y
                    target=transfer(meta['y']);hidden=F.mse_loss(y.float(),target.float())/target.float().square().mean().clamp_min(1e-8)
                    extra={};loss=hidden
                    if branch=='language' and i==35:
                        z=F.linear(norm(y)[:,-1,:],head).float();t=transfer(sample['logits']).reshape(1,-1)
                        kd=F.kl_div(F.log_softmax(z/2,dim=-1),F.softmax(t/2,dim=-1),reduction='batchmean')*4
                        label=torch.tensor([9454 if sample['request']['knife_present'] else 2753],device=device)
                        ce=F.cross_entropy(z,label);loss=hidden+.25*kd+ce
                        extra=dict(KL=float(kd.detach()),CE=float(ce.detach()),predicted_token=int(z.detach().argmax()),target_token=int(label.item()))
                    return loss,dict(loss=float(loss.detach()),hidden_MSE_normalized=float(hidden.detach()),**extra)
                def evaluate():
                    with torch.no_grad():return [run(sample)[1] for sample in loaded]
                baseline=evaluate();optimizer=torch.optim.AdamW(trainable,lr=p['first_phase']['learning_rate'],weight_decay=0.)
                trajectory=[]
                for step in range(p['first_phase']['steps_per_retained_block']):
                    optimizer.zero_grad(set_to_none=True);loss,metrics=run(loaded[step%len(loaded)])
                    assert torch.isfinite(loss);loss.backward()
                    assert all(x.grad is not None and torch.isfinite(x.grad).all() for x in trainable)
                    total=float(torch.nn.utils.clip_grad_norm_(trainable,1.));assert total>0;optimizer.step()
                    trajectory.append(dict(step=step,gradient_norm=total,**metrics))
                restored=evaluate();folder=out/key;folder.mkdir();state={}
                exported=[]
                for name,m in linears.items():
                    state[name]=dict(A=m.A.detach().cpu(),B=m.B.detach().cpu(),scale=m.scale,bits=m.bits,global_name=m.global_name)
                    merged=m.merged().detach();q=torch.empty_like(merged);pieces=[];scales=[];orientations=[]
                    for start in range(0,len(merged),64):
                        unsigned,scale,orientation,recon=recover_full_range_rows_for_storage(torch,merged[start:start+64],m.bits,scale_format='fp16')
                        u=unsigned.cpu().numpy();s=scale.cpu().numpy();o=orientation.cpu().numpy()
                        packed=pack_unsigned_codes(u,m.bits);assert np.array_equal(unpack_unsigned_codes(packed,m.bits,u.size).reshape(u.shape),u)
                        orient=pack_orientation_bits(o);assert np.array_equal(unpack_orientation_bits(orient,o.size).reshape(o.shape),o)
                        pieces.append(packed);scales.append(s);orientations.append(o);q[start:start+64]=recon
                    paths={}
                    for suffix,raw in [('codes.bin',b''.join(pieces)),('scales_fp16.bin',np.concatenate(scales).astype('<f2').tobytes()),('orientation.bin',pack_orientation_bits(np.concatenate(orientations)))]:
                        file=folder/(name.replace('.','_')+'.'+suffix);file.open('xb').write(raw);paths[suffix]=dict(path=relative(file),sha256=sha(file),bytes=file.stat().st_size)
                    m.quantized=q;exported.append(dict(name=name,bits=m.bits,shape=list(merged.shape),files=paths,merge_to_export_relative_L2=float(torch.linalg.vector_norm(q-merged)/torch.linalg.vector_norm(merged))))
                quantized=evaluate()
                with (folder/'ADAPTERS.pt').open('xb') as stream:torch.save(state,stream)
                record=dict(key=key,teacher_segment_original_indices=list(range(previous+1,i+1)),baseline=baseline,restored_high_precision=restored,target_format_quantized=quantized,trajectory=trajectory,modules=exported,adapter_sha256=sha(folder/'ADAPTERS.pt'),trainable_parameters=sum(x.numel() for x in trainable),local_teacher_forced=True)
                save(folder/'RESULT.json',record);result['blocks'].append(dict(key=key,result=relative(folder/'RESULT.json'),sha256=sha(folder/'RESULT.json'),baseline_mean=sum(x['loss'] for x in baseline)/8,restored_mean=sum(x['loss'] for x in restored)/8,quantized_mean=sum(x['loss'] for x in quantized)/8))
                print('RECOVERY_BLOCK_SAVED',result['blocks'][-1],flush=True)
                del optimizer,block,linears,trainable,state,merged,q,loss;head=norm=None;gc.collect();torch.cuda.empty_cache()
        engine.unchanged();result.update(status='COMPLETE_LOCAL_41_BLOCK_LORA_AND_TARGET_FORMAT_EXPORT',original_rc=0,steps_per_block=8,composed_student_quality_proven=False,board_speed_proven=False,base_teacher_parameters_unchanged=True)
    except BaseException:result['traceback']=traceback.format_exc()
    finally:
        if engine:engine.close()
        result['elapsed_s']=time.monotonic()-began;save(out/'RESULT.json',result);print(result['status'],result.get('traceback',''),flush=True)
    return result['original_rc']
if __name__=='__main__':raise SystemExit(main())
