from common_recovery import *
def main():
    for name in ('CURRENT_STATE.md','docsMILESTONES.md','DEPLOYMENT_OPERATION_MISTAKES_REVIEW.md','deployment/mage_vl4b/BOARD_GATE_RESULT.json'):(ROOT/name).read_text(encoding='utf-8-sig')
    old=RUNS/'M523-fixed-demo-pruning-128-protocol-01/RESULT.json';p=read(old)
    winner=RUNS/'M523-fixed-demo-pruning-128-search-02/WINNER_FROZEN.json';w=read(winner)
    native=RUNS/'M523-fixed-demo-pruning-128-board-02/Run/BOARD_RESULT.json';v=read(native)
    assert v['safe_cleanup_complete'] and not v['unsafe_retained'] and v['primary_rc']==1
    train=[r for r in p['requests'] if int(r['id'][4:6]) in (0,1,2,4)]
    dev=[r for r in p['requests'] if int(r['id'][4:6]) in (3,5)]
    assert len(train)==8 and len(dev)==4
    files=['common_recovery.py','prepare.py','capture_teacher.py','entry.py','host.py']
    for name in files:compile((HERE/name).read_text(encoding='utf-8'),name,'exec')
    value=dict(status='FROZEN_GPU_LAYERWISE_LORA_RECOVERY_FIRST_SHORT_EXPERIMENT',original_rc=0,
        user_authorization='2026-10-25: joint whole-layer distillation/LoRA, target-format export comparison, speed research may measure wrong-answer candidates. Supersedes previous no-training policy only for new version.',
        source_parent_sha256=sha(old),failed_board_sha256=sha(native),runtime_protocol=p['runtime_protocol'],token_ids=p['token_ids'],
        teacher=dict(vision=list(range(24)),language=list(range(36)),description='Current channel-pruned PS3072 parent A, not original full-width or higher-quality teacher'),
        student=dict(vision=w['vision'],language=w['language']),train_requests=train,development_requests=dev,
        split='4 original training video groups00,01,02,04; reserved calibration03,05. No test/heldout. Four demo windows are already training/selection data, not independent evaluation.',
        first_phase=dict(method='Teacher target cache, one retained block at a time on8GB GPU; original-index boundary mapping. Train attention+MLP LoRA, then evaluate composed student. This local phase is not full end-to-end joint QAT.',rank=4,alpha=4,steps_per_retained_block=8,learning_rate=0.0005,optimizer='AdamW',seed=524,
                         losses='Normalized hidden boundary MSE for all retained blocks; on final language block additionally first-token teacher KL and true Yes/No CE. Teacher errors remain recorded; labels are not substituted for model output.'),
        teacher_capture=dict(visual_forwards=8,language_prefills=8,first_tokens=8,need_new_outputs='Previously saved final logits/features lack layer inputs, kwargs and mapped segment targets; record new required intermediate evidence without replacing old answers.'),
        budgets=dict(teacher_capture_wall_seconds=3600,training_wall_seconds=3600,new_teacher_requests=8,new_student_evaluations_max=24,disk_bytes_max=20<<30),
        quantization='First FP32/BF16 adapter recovery baseline; merge to dense, export original per-module W2/W3/W4 G64/FP16-scale format with original orientation policy. No automatic higher bit width; quantify export loss separately before deciding QAT.',
        board_policy='No board actions in capture/training. New speed-only candidates may finish and save wrong answers; final demo promotion still requires all fixed windows correct and measured TTFT<30. Hardware fail-closed gates unchanged.',
        papers=['https://arxiv.org/abs/2510.15304','https://ojs.aaai.org/index.php/AAAI/article/view/32923/35078','https://arxiv.org/abs/2406.06385'],
        frozen={relative(HERE/n):sha(HERE/n) for n in files},heldout_opened=False,board_actions=0)
    out=RUNS/(PREFIX+'-protocol-01/RESULT.json');save(out,value)
    sys.path.insert(0,str(ROOT/'scripts/optimization'));from m455456_workflow02 import synchronized
    h=sha(out);synchronized('latest_m524_recovery_protocol01',dict(status=value['status'],result=relative(out),sha256=h,board=False),
        '## M524按新授权冻结整层蒸馏与LoRA短实验\n\nRESULT SHA '+h+'；14V27L保留为恢复起点，教师为当前PS3072父A。8GB GPU逐块Attention+MLP低秩蒸馏，原编号对应边界；首阶段局部训练不冒充完整端到端QAT。4fit来源8请求、2reserved-cal来源4请求、6test封闭；解释/EOS不另设演示门，真实首判断和标签监督分列。训练与当前格式导出独立量化恢复损失；速度研究允许错答候选记录TTFT，最终仍须板端答对且<30。0新板动作，旧FAIL/稳定保全。')
    print(value['status'],h,flush=True)
if __name__=='__main__':main()
