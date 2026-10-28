from common_joint import *

def main():
    failed=RUNS/(PREFIX+'-head-isolation-aug_original_body-01/RESULT.json');v=read(failed);assert v['original_rc']==0 and v['fixed_demo_correct']<4
    for n in ('target_head.py','target_entry.py','target_host.py'):compile((HERE/n).read_text(encoding='utf-8'),n,'exec')
    p=dict(status='FROZEN_DEPLOYMENT_NUMERIC_HEAD_RECOVERY_WITH_MATCHED_AUGMENTATION',seed=5253,rank=8,learning_rate=.005,steps_per_arm=96,teacher_KL=.05,
        sources={relative(HERE/n):sha(HERE/n) for n in ('target_head.py','target_entry.py','target_host.py','common_joint.py')},
        failed_transferred_head_sha256=sha(failed),
        scope='Original10V18 deployment-numeric frozen body, learned FP32 full151936-vocabulary rank8 residual. All failed full-body/transfer results retained; this head-only recipe does not deploy learned body weights.',
        curriculum='Teacher cached clear original frames. Same initialization, label-balanced pairs and96 steps per arm. Student clean first16, weak next16, moderate remaining64; clean control original throughout. Only four safe fit windows augmented, no crop/occlusion/object or label changes.',
        split='Original4fit groups; ambiguouscal02t1 notCE-supervised but evaluated unchanged. Four reserved-cal windows evaluation only. Six heldout clips remain closed.',
        budgets=dict(new_student_prefills=24,teacher_new_forwards=0,optimizer_updates=192,board_actions=0),
        selection='Evaluate both final checkpoints at predeclared96 steps, no epoch selection. Prefer augmented only if all4 clean and4 fresh-seed hard demo answers correct; report reserved-cal and matched control. Final quality requires deployed result, not cached feature claims.',
        board_gate='No board action in this protocol. Residual1235968 MAC and FP32 payload must be included in any later TTFT; no forced binary vocabulary.')
    out=RUNS/(PREFIX+'-target-head-protocol-01/RESULT.json');save(out,p)
    sys.path.insert(0,str(ROOT/'scripts/optimization'));from m455456_workflow02 import synchronized
    h=sha(out);synchronized('latest_m525_target_head_protocol01',dict(status=p['status'],result=relative(out),sha256=h,board=False,promoted=False),'## M525代理训练无法迁移后冻结部署算术输出头恢复\n\nRESULT SHA '+h+'；增强已训练主体/原主体转移head均未恢复固定答案，失败保留。新训练仅原10V18部署算术主体产生特征+可学习rank8全词表FP32头；同初始化96步原帧/渐进较难视图对照，24真实学生捕获/0新教师/0板；不部署之前主体LoRA，不屏蔽词表，额外计算须计TTFT。6test封闭。')
    print(p['status'],h,flush=True)
if __name__=='__main__':main()
