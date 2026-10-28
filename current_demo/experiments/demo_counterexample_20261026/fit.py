"""Vectorized equal-size full-batch clean vs clean-plus-hard replay, fixed endpoints."""
import sys,traceback,math,importlib.util
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
from common_fix import *
def main():
    p=verify();c=read(CAP/'RESULT.json');assert c['primary_rc']==0
    FIT.mkdir(exist_ok=False);v=dict(status='FAIL_M542_FULL_BATCH_HEAD_TRAINING',primary_rc=1,arms={},board_commands=0,heldout_opened=False);start=time.monotonic()
    try:
        import torch
        import torch.nn.functional as F
        torch.set_num_threads(4);torch.set_num_interop_threads(1);torch.manual_seed(p['training']['seed']);torch.backends.cuda.matmul.allow_tf32=False
        assert torch.cuda.is_available();records=c['student'];lookup={r['key']:r for r in records};cpu={}
        for r in records:
            f=ROOT/r['source'];assert sha(f)==r['sha256']
            with np.load(f,allow_pickle=False) as z:cpu[r['key']]={k:z[k].copy() for k in ['x','z','old_logits']}
        teach={}
        for r in c['teacher']:
            assert r['score']['correct'] and sha(ROOT/r['source'])==r['sha256']
            with np.load(ROOT/r['source'],allow_pickle=False) as z:teach[r['id']]=z['z'].copy()
        targets=torch.tensor([r['target'] for r in records],device='cuda');positive=targets==9454
        weights=torch.where(positive,.5/positive.sum(),.5/(~positive).sum()).float()
        clean_keys=[r['id']+'_clean' if r['view'] in ['hard-train','hard-check'] else r['key'] for r in records]
        hard_keys=[r['key'] for r in records]
        def tensors(keys):
            return (torch.from_numpy(np.stack([cpu[k]['x'] for k in keys])).cuda(),torch.from_numpy(np.stack([cpu[k]['z'] for k in keys])).cuda())
        Xclean,Zclean=tensors(clean_keys);Xhard,Zhard=tensors(hard_keys)
        teacher_rows=[];kd_weights=[];origins=[]
        for r,k in zip(records,clean_keys):
            if r['id'] in teach:teacher_rows.append(teach[r['id']]);kd_weights.append(p['training']['teacher_KL']);origins.append('deeper_clean_teacher')
            elif r['role']=='legacy-fit':teacher_rows.append(cpu[k]['old_logits']);kd_weights.append(p['training']['legacy_KL']);origins.append('legacy_old_head_replay')
            else:teacher_rows.append(cpu[k]['old_logits']);kd_weights.append(0.);origins.append('label_only')
        teacher_probs=F.softmax(torch.from_numpy(np.stack(teacher_rows)).cuda()/2,-1);kd_weight=torch.tensor(kd_weights,device='cuda')
        A0=torch.from_numpy(np.load(HEAD/'A.npy',allow_pickle=False).copy()).cuda();B0=torch.from_numpy(np.load(HEAD/'B.npy',allow_pickle=False).copy()).cuda()
        spec=importlib.util.spec_from_file_location('_m542_portable_head',HEAD/'learned_head.py');mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod)
        for arm in ['clean_control','harder_student']:
            A=torch.nn.Parameter(A0.clone());B=torch.nn.Parameter(B0.clone());opt=torch.optim.AdamW([A,B],lr=p['training']['learning_rate'],weight_decay=0.);history=[]
            for step in range(p['training']['steps_per_arm']):
                assert time.monotonic()-start<p['budgets']['fit_seconds'];opt.zero_grad(set_to_none=True)
                hard=arm=='harder_student' and step>=p['training']['clean_prefix'];X,Z=(Xhard,Zhard) if hard else (Xclean,Zclean)
                logits=Z+F.linear(F.linear(X,A),B)
                ce=F.cross_entropy(logits,targets,reduction='none');kl=F.kl_div(F.log_softmax(logits/2,-1),teacher_probs,reduction='none').sum(-1)*4
                loss=(weights*(ce+kd_weight*kl)).sum();assert torch.isfinite(loss);loss.backward();norm=float(torch.nn.utils.clip_grad_norm_([A,B],1.));assert math.isfinite(norm);opt.step()
                history.append(dict(step=step,loss=float(loss.detach()),CE=float((weights*ce).sum().detach()),KL=float((weights*kd_weight*kl).sum().detach()),gradient_norm=norm,hard_views=hard,batch_rows=len(records)))
                if step%50==0:print('M542_FULLBATCH',arm,step,float(loss.detach()),flush=True)
            folder=OPT/'candidates'/('M542-demo-head-'+arm+'-01');folder.mkdir(exist_ok=False)
            for n,a in [('A',A.detach().cpu().numpy()),('B',B.detach().cpu().numpy())]:
                with (folder/(n+'.npy')).open('xb') as out:np.save(out,np.ascontiguousarray(a),allow_pickle=False)
            (folder/'learned_head.py').open('xb').write((HEAD/'learned_head.py').read_bytes())
            manifest=dict(scale=1.,rank=8,full_vocab=151936,arm=arm,inference_extra_MACs=1235968,body_unmodified=True,no_token_specific_bias=True,
                source_sha256=sha(folder/'learned_head.py'),protocol_sha256=sha(PROTO),capture_sha256=sha(CAP/'RESULT.json'),steps=p['training']['steps_per_arm'],
                training_scope='Demonstration-domain head counterexample replay. No source identity is available to inference.',
                A=dict(path='A.npy',sha256=sha(folder/'A.npy'),bytes=(folder/'A.npy').stat().st_size),B=dict(path='B.npy',sha256=sha(folder/'B.npy'),bytes=(folder/'B.npy').stat().st_size))
            save(folder/'HEAD_MANIFEST.json',manifest);files=[dict(path=f.name,bytes=f.stat().st_size,sha256=sha(f)) for f in sorted(folder.iterdir())]
            save(folder/'PACKAGE_MANIFEST.json',dict(files=files,file_count=len(files),total_bytes=sum(r['bytes'] for r in files)))
            head=mod.LearnedHead(folder,manifest);evaluations=[]
            for r in records:
                a=cpu[r['key']];z=head.add(a['x'][None],a['z'][None])[0];i=int(z.argmax());other=z.copy();other[r['target']]=-np.inf
                evaluations.append(dict(key=r['key'],id=r['id'],former_role=r['role'],current_role='demonstration_fit',view=r['view'],target=r['target'],
                    token_id=i,correct=i==r['target'],target_gap=float(z[r['target']])-float(other.max())))
            sample=cpu[records[0]['key']];single=head.add(sample['x'][None],sample['z'][None]);pad=np.repeat(sample['z'][None],32,axis=0);o=head.add(sample['x'][None],pad)
            assert np.array_equal(single,o[:1]) and np.array_equal(pad[1:],o[1:])
            v['arms'][arm]=dict(package=rel(folder),manifest_sha256=sha(folder/'PACKAGE_MANIFEST.json'),history=history,evaluations=evaluations,
                fit_correct=sum(r['correct'] for r in evaluations),fit_n=len(evaluations),fit_pass=all(r['correct'] for r in evaluations),
                minimum_fit_target_gap=min(r['target_gap'] for r in evaluations),padded_interface_verified=True)
            print('M542_FINAL',arm,v['arms'][arm]['fit_correct'],len(evaluations),v['arms'][arm]['minimum_fit_target_gap'],flush=True)
        assert v['arms']['clean_control']['history'][:64]==v['arms']['harder_student']['history'][:64]
        selected='harder_student' if v['arms']['harder_student']['fit_pass'] else 'clean_control' if v['arms']['clean_control']['fit_pass'] else None
        v.update(status='COMPLETE_M542_FULL_BATCH_FINAL_CHECKPOINTS',primary_rc=0,selected_arm=selected,total_optimizer_updates=800,
            fit_row_keys=[r['key'] for r in records],clean_substitution_keys=clean_keys,teacher_origins=origins,
            new_temporal_checks_used_for_gradient_or_selection=False,body_parameters_updated=False,inference_rank_or_MACs_changed=False,
            old_failed_M541_not_overwritten=True)
    except BaseException:v['traceback']=traceback.format_exc()
    v['elapsed_s']=time.monotonic()-start;save(FIT/'RESULT.json',v);print(v['status'],v.get('traceback',''),v.get('selected_arm'),flush=True);return v['primary_rc']
if __name__=='__main__':raise SystemExit(main())
