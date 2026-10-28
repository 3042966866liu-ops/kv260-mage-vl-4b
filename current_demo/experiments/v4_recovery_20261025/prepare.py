"""Freeze contribution-aware G64 selection, R1, conditional fc2 recovery."""
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
from common_v4 import *
def main():
    joint=read(RUNS/'M525-joint-augmented-student-128-protocol-02/RESULT.json')
    requests=joint['train_requests'];assert len(requests)==8 and len({r['source_group'] for r in requests})==4
    preview=read(ROOT/joint['augmentation_preview']);hard={}
    for r in preview['records']:
        if r['student_view']=='moderate' and r['source_request'] in joint['safe_augmentation_ids']:
            hard[r['source_request']]={k:r[k] for k in ('student_file','student_sha256','source_request','student_view')}
    assert len(hard)==4 and set(hard)<=set(r['id'] for r in requests)
    frozen={}
    def add(f,h=None):
        actual=sha(f)
        if h is not None:assert actual==h,str(f)
        frozen[rel(f)]=actual
    for f in sorted(HERE.glob('*.py')):compile(f.read_bytes(),str(f),'exec');add(f)
    for f in [RUNS/'M535-V4-local-screen-audit-01/RESULT.json',RUNS/'M535-V4-local-screen-board-01/V4_input.npz',
              RUNS/'M525-joint-augmented-student-128-protocol-02/RESULT.json',ROOT/joint['augmentation_preview'],
              RUNS/'M522-training-capture-protocol-03/RESULT.json',COMPONENT/'SOURCE_CLOSURE.json',COMPONENT/'PS_NATIVE_PLAN.json',
              COMPONENT/'PS_crop_native.py',PARENT/'PACKAGE_MANIFEST.json',PARENT/'board_subset.py',PARENT/'visual_cache_profiler.py',PARENT/'DEMO_BOARD_PLAN.json',
              OPT/'contracts/config.json',ROOT/'experiments/speed_target_30s_20261020/generate_flap522.py',ROOT/'deployment/mage_vl4b/scripts/mixed_bit_checkpoint.py']:
        add(f)
    for r in requests+joint['development_requests']:add(ROOT/r['frames'],r['frames_sha256'])
    for r in hard.values():add(ROOT/r['student_file'],r['student_sha256'])
    for r in read(COMPONENT/'SOURCE_CLOSURE.json')['files']:add(REL/r['path'],r['sha256'])
    for r in read(COMPONENT/'PS_NATIVE_PLAN.json')['selected']:
        add(COMPONENT/r['codes']['path'],r['codes']['sha256']);add(COMPONENT/r['R1']['path'],r['R1']['sha256'])
    # Reuse the exact already-audited full quality runtime closure, never the
    # rejected single-view geometry or its model run.
    previous=read(RUNS/'M531-single-global-view-quality-protocol-01/RESULT.json')
    for n,h in previous['frozen'].items():add(ROOT/n,h)
    plan=dict(status='FROZEN_M536_V4_3584_CONTRIBUTION_R1_CONDITIONAL_FC2',width=3584,training_requests=requests,reserved_requests=joint['development_requests'],hard_training=hard,
        original_split='4 original fit source groups /8 windows only;4 reserved-cal report only;6 test clips closed',
        frozen=frozen,retained_vision=read(PARENT/'DEMO_BOARD_PLAN.json')['retained_vision'],
        selection='Only 8 clean fit windows:64 G64 post-GELU output contribution Gram; greedily remove8 groups minimizing total reconstruction SSE including cross terms; no iterative answer-based group search',
        R1='FP64 mean teacher original V4 output minus same-input cropped V4 output over8 clean fit windows; cast FP32 once and fuse into original fc2 FP32 bias; evaluate actual fused-bias forward',
        local_gate=dict(maximum_relativeL2=.20,minimum_cosine=.98,every_clean_fit_window=True,all_fit_aggregate=True,saved_A53_one_input=True),
        conditional_fc2=dict(only_if_R1_fails=True,fc1_frozen=True,seed=536,steps_per_arm=128,lr=.0002,weight_anchor=.0001,
            arms=['clean_control','paired_harder_student'],schedule='first64 FP32, last64 W4 STE-QAT;final128 only,no best-epoch search',
            teacher='Same current original4096 V4 clean input output; frozen prefix; no answer-head or language training',
            student='Own unchanged prefix;harder arm on already-reviewed4 fit moderate views in second half,clean teacher target,same geometry; other4 requests stayclean',
            export='Existing mixed_bit_checkpoint.quantize_rows_for_storage W4 G64,FP16 scale then quantize;fc2 codes/scales may change only in this branch',
            choice='Prefer augmented if it passes clean gate and improves hard local reconstruction without >.02 aggregate clean L2 loss versus passing clean control;otherwise passing clean control. No dev selection'),
        budgets=dict(prefix_captures=12,max_local_optimizer_updates=256,fit_seconds=1800,new_full_software_prefills=12,quality_seconds=1500),
        fixed_input_tokens=128,dual_views=True,visual_slots=98,original_10V18L=True,other_weights_R1_head_unchanged=True,
        complete_quality='If local candidate passes: original dual1284 controls+4 fixed candidate+4reserved-cal(candidate report only),first full-vocab argmax;fixed4/4 and no invalid outputs;no forced labels or vocabulary',
        board='Only after export/full-quality passing:separate package/component/board E2E+same-session TTFT protocol;no board command from this offline protocol',
        heldout_opened=False,board_commands=0,no_deeper_width=True)
    save(PROTOCOL,plan)
    sys.path.insert(0,str(ROOT/'scripts/optimization'));from m455456_workflow02 import synchronized
    h=sha(PROTOCOL);synchronized('latest_m536_v4_recovery_protocol01',dict(status=plan['status'],result=rel(PROTOCOL),sha256=h,board=False),
        '## M536固定V4 3584恢复协议\n\nRESULT SHA '+h+'；8训练窗口/4来源真实当前学生PS前缀，post-GELU输出贡献及交互greedy删8G64，再FP64均值R1合入fc2偏置。原门限L2≤.20/cos≥.98保持；仅R1不过时128步clean/较难学生成对fc2训练，fc1冻结、末64步原W4 STE并实际导出复算。固定128/双视图/98槽/10V18L/原头，0测试/板命令；局部过后12软件首判断，再另立板端同场TTFT。原失败及演示基线保持。')
    print(plan['status'],h,flush=True)
if __name__=='__main__':main()
