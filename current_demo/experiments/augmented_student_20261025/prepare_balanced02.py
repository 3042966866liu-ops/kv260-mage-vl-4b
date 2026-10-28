"""New matched recipe after real32-step outcomes: balanced CE and merged head LoRA."""
from common_joint import *
def main():
    prior=RUNS/(PREFIX+'-training-01/RESULT.json');v=read(prior)
    assert v['original_rc']==0 and len(v['arms'])==2
    p=read(RUNS/(PREFIX+'-protocol-01/RESULT.json'))
    p.update(status='FROZEN_BALANCED_MINIBATCH_CLEAN_VS_HARDER_FULL_STUDENT',previous_result_sha256=sha(prior),source_baseline=relative(prior),
        head_rank=8,head_learning_rate=.005,pair_batch_size=2,ambiguous_feature_replay_every=8,
        change_reason='Both original arms2/4 fixed demo; clean collapsesNo and augmented collapsesYes. Control class-bias with positive/negative paired gradients and a mergeable rank8 output-head adapter; keep augmentation matched, no claim unique cause.',
        budgets=dict(optimizer_updates=64,real_CE_gradient_probe=1,training_prefills=136,evaluation_prefills=32,reused_untrained_baseline_prefills=16,board_actions=0),
        baseline_reuse='Original full151936 logits for first clean window must be bit-identical before optimizer changes. Reuse completed untrained16 results; new headB=0 has no forced answer.',
        inference='Head adapter merges into same151936x2560 head weight, no extra inference branch or vocabulary mask; export/board gates remain pending.')
    sources={}
    source=(HERE/'joint_runtime.py').read_text(encoding='utf-8')
    old="e.model.lm_head=StreamLinear(e.model.lm_head.weight,None,e.model.lm_head.weight.dtype,'lm_head',int(entries['lm_head.weight']['bits']),False)"
    new="e.model.lm_head=StreamLinear(e.model.lm_head.weight,None,e.model.lm_head.weight.dtype,'lm_head',int(entries['lm_head.weight']['bits']),True)\n        self.linears['head:-1:lm_head']=e.model.lm_head"
    assert source.count(old)==1;source=source.replace(old,new)
    sources['joint_runtime02.py']=source
    source=(HERE/'train_joint.py').read_text(encoding='utf-8').replace('from joint_runtime import JointStudent','from joint_runtime02 import JointStudent').replace("+'-protocol-01/RESULT.json'","+'-protocol-02/RESULT.json'").replace("+'-training-01'","+'-training-02'")
    source=source.replace("        self.initial=", "        self.initial=")
    source=source.replace('            return loss,dict(loss=', '            student.last_ce=ce;student.last_z=z\n            return loss,dict(loss=')
    old="arrays,_=prepare(p['train_requests'][0]);loss,metrics=losses(p['train_requests'][0],arrays);loss.backward()"
    new="arrays,_=prepare(p['train_requests'][0]);loss,metrics=losses(p['train_requests'][0],arrays)\n        saved_baseline=RUNS/(PREFIX+'-training-01/baseline/cal_00_t0_clean.logits.npy')\n        assert np.array_equal(student.last_z.detach().cpu().numpy(),np.load(saved_baseline,allow_pickle=False)), 'Zero-head-adapter baseline changed'\n        student.last_ce.backward()"
    assert source.count(old)==1;source=source.replace(old,new)
    source=source.replace("for branch in ('vision','language')}","for branch in ('vision','language','head')}")
    source=source.replace("source_sha256=sha(HERE/'joint_runtime.py')","source_sha256=sha(HERE/'joint_runtime02.py'),CE_only_backward=True,matched_original_baseline_bit_exact=True")
    source=source.replace("result['evaluations']['untrained']=evaluate('baseline')","result['evaluations']['untrained']=read(ROOT/p['source_baseline'])['evaluations']['untrained']\n        student.last_ce=None;student.last_z=None")
    source=source.replace("optimizer=torch.optim.AdamW(student.params,lr=p['learning_rate'],weight_decay=0.);trajectory=[]", "body=[x for k,m in student.linears.items() if not k.startswith('head:') for x in (m.A,m.B)];head=[e.model.lm_head.A,e.model.lm_head.B]\n            optimizer=torch.optim.AdamW([{'params':body,'lr':p['learning_rate']},{'params':head,'lr':p['head_learning_rate']}],weight_decay=0.);trajectory=[]")
    start=source.index("            for step in range(p['steps_per_arm']):")
    end=source.index("            checkpoint=out/",start)
    source=source[:start]+'''            eligible=[r for r in p['train_requests'] if r['id'] not in p['ambiguous_positive_CE_mask_ids']]
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
''' +source[end:]
    source=source.replace("'COMPLETE_MATCHED_FULL_STUDENT_CLEAN_AND_HARDER_VIEW_TRAINING'","'COMPLETE_BALANCED_FULL_STUDENT_CLEAN_AND_HARDER_VIEW_TRAINING'")
    sources['train_joint02.py']=source
    source=(HERE/'entry.py').read_text(encoding='utf-8').replace('joint_runtime,train_joint','joint_runtime02,train_joint02').replace("HERE/'train_joint.py'","HERE/'train_joint02.py'");sources['entry02.py']=source
    source=(HERE/'host.py').read_text(encoding='utf-8').replace("+'-host-01'","+'-host-02'").replace('entry.py','entry02.py').replace('protocol-01/RESULT.json','protocol-02/RESULT.json').replace('training-01/RESULT.json','training-02/RESULT.json').replace('latest_m525_joint_host01','latest_m525_joint_host02');sources['host02.py']=source
    for name,source in sources.items():compile(source,name,'exec');assert not (HERE/name).exists()
    for name,source in sources.items():(HERE/name).open('x',encoding='utf-8').write(source)
    p['frozen']={relative(HERE/n):sha(HERE/n) for n in ['common_joint.py',*sources]}
    out=RUNS/(PREFIX+'-protocol-02/RESULT.json');save(out,p)
    sys.path.insert(0,str(ROOT/'scripts/optimization'));from m455456_workflow02 import synchronized
    hs=sha(out);synchronized('latest_m525_balanced_protocol02',dict(status=p['status'],result=relative(out),sha256=hs,board=False),'## M525首个完整增强对照2/4后冻结平衡批次修正\n\nRESULT SHA '+hs+'；原01两臂32步真实完成，clean全No/aug全Yes、演示均2/4，保留失败不称增强有效。新两臂同初始化原基线，正负各1累积为一次更新、各32更新，并给同维原全词表head加可合并rank8适配；首真实纯CE梯度核验视觉/语言/head及与保存初始logits逐位一致。旧16基线复用，136新训练prefill+32评估，教师缓存复用/6test封闭/0板动作；增强范围仍原4安全fit窗口且不改标签。')
    print(p['status'],hs,flush=True)
if __name__=='__main__':main()
