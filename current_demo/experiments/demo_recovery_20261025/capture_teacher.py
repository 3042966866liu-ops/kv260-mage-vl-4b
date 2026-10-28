"""Capture new teacher block boundaries needed by local GPU distillation."""
from common_recovery import *
import os,traceback,gc

def main():
    p=read(RUNS/(PREFIX+'-protocol-01/RESULT.json'))
    for name,h in p['frozen'].items():assert sha(ROOT/name)==h
    out=RUNS/(PREFIX+'-teacher-capture-01');assert not out.exists();out.mkdir()
    value=dict(status='FAIL_RECOVERY_TEACHER_CAPTURE',original_rc=1,teacher_requests=[],board_actions=0,parameter_updates=0)
    began=time.monotonic();engine=None;handles=[]
    try:
        import torch
        assert torch.cuda.is_available();free,total=torch.cuda.mem_get_info();assert free>2<<30
        value['GPU']=dict(name=torch.cuda.get_device_name(0),free_bytes=free,total_bytes=total)
        mem=Path('/proc/meminfo').read_text();value['host_memory_before']=mem
        print('RECOVERY_TEACHER_LOAD',flush=True)
        engine=engine_class()(p['runtime_protocol']);engine.set_active(list(range(24)),list(range(36)))
        current={};inventory={}
        def clone(x):
            if isinstance(x,torch.Tensor):return x.detach().cpu().clone()
            if isinstance(x,tuple):return tuple(clone(y) for y in x)
            if isinstance(x,list):return [clone(y) for y in x]
            if isinstance(x,dict):return {k:clone(v) for k,v in x.items()}
            if x is None or isinstance(x,(str,int,float,bool)):return x
            if 'Cache' in type(x).__name__:return None
            raise TypeError('Unsupported teacher argument '+str(type(x)))
        for branch,modules in [('vision',engine.original_vision),('language',engine.original_language)]:
            for i,module in enumerate(modules):
                key=branch+'_'+str(i).zfill(2)
                def before(m,args,kwargs,key=key):
                    current[key]=dict(args=clone(args),kwargs=clone({k:(None if k in ('past_key_values','past_key_value') else False if k=='use_cache' else v) for k,v in kwargs.items()}))
                def after(m,args,kwargs,result,key=key):
                    y=result[0] if isinstance(result,tuple) else result
                    assert isinstance(y,torch.Tensor) and torch.isfinite(y).all();current[key]['y']=clone(y)
                handles.extend([module.register_forward_pre_hook(before,with_kwargs=True),module.register_forward_hook(after,with_kwargs=True)])
                inventory[key]=dict(type=str(type(module)),modules=[dict(name=n,type=str(type(m)),weight=list(m.weight.shape) if hasattr(m,'weight') and isinstance(m.weight,torch.Tensor) else None,in_features=getattr(m,'in_features',None),out_features=getattr(m,'out_features',None),store=hasattr(m,'store')) for n,m in module.named_modules() if hasattr(m,'weight') or hasattr(m,'store')])
        save(out/'INVENTORY.json',inventory)
        for request in p['train_requests']:
            assert time.monotonic()-began<p['budgets']['teacher_capture_wall_seconds']
            print('RECOVERY_TEACHER_BEGIN',request['id'],flush=True);current.clear()
            feature=engine.features(request);answer,logits=engine.answer(request,feature,1)
            assert set(current)==set(inventory)
            for key,row in current.items():assert row['args'][0].shape==row['y'].shape
            folder=out/request['id'];folder.mkdir();file=folder/'boundaries.pt'
            with file.open('xb') as stream:torch.save(dict(blocks=current,features=torch.from_numpy(feature.copy()),logits=torch.from_numpy(logits[0].copy()),request=request),stream)
            save(folder/'RESULT.json',dict(request_id=request['id'],file=relative(file),sha256=sha(file),bytes=file.stat().st_size,teacher_answer=answer['text'],teacher_correct=answer['correct_first_token'],block_count=len(current),parameter_unchanged=True))
            value['teacher_requests'].append(read(folder/'RESULT.json'));current.clear();gc.collect()
            print('RECOVERY_TEACHER_SAVED',request['id'],file.stat().st_size,flush=True)
        engine.unchanged();value.update(status='PASS_TEACHER_BOUNDARY_CACHE_FOR_GPU_RECOVERY',original_rc=0,blocks_per_request=60,teacher_is_parent_A=True)
    except BaseException:value['traceback']=traceback.format_exc()
    finally:
        for h in handles:h.remove()
        if engine:engine.close()
        value['elapsed_s']=time.monotonic()-began;save(out/'RESULT.json',value)
        print(value['status'],value.get('traceback',''),flush=True)
    return value['original_rc']
if __name__=='__main__':raise SystemExit(main())
