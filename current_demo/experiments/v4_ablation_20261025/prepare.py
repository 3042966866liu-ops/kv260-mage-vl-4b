"""Freeze bounded reuse and matched V4 ablation before any new full forward."""
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
from common_ablation import *
def main():
    assert not PROTO.exists()
    for f in HERE.glob('*.py'):compile(f.read_text(encoding='utf8'),str(f),'exec')
    old=read(RUNS/'M525-joint-augmented-student-128-target-head-capture-01/RESULT.json')
    fitproto=read(RUNS/'M536-V4-3584-recovery-protocol-01/RESULT.json')
    plan=read(PARENT/'DEMO_BOARD_PLAN.json');fixed={r['id']:r for r in plan['demo_requests']}
    cases=[];paths=set()
    for r in old['records']:
        role='fixed-demo' if r['id'] in fixed else 'reserved-cal'
        if not (r['view']=='clean' and (r['id'] in fixed or r['split']=='reserved-cal') or r['view']=='moderate_check'):continue
        view='clean' if r['view']=='clean' else 'hard-dev'
        frame=PARENT/fixed[r['id']]['frame_path'] if role=='fixed-demo' and view=='clean' else ROOT/r['frame']
        assert sha(ROOT/r['frame'])==r['frame_sha256']
        assert np.array_equal(np.load(frame,allow_pickle=False),np.load(ROOT/r['frame'],allow_pickle=False))
        cases.append(dict(key=r['id']+'_'+view,id=r['id'],view=view,role=role if view=='clean' else 'hard-dev',
            expected='Yes' if r['target']==9454 else 'No',frame=rel(frame),frame_sha256=sha(frame),source_group=r['id'][0:6],original_augmentation=r['augmentation']))
        paths.update([frame,ROOT/r['frame'],ROOT/r['payload']])
        paths.add(RUNS/'M525-joint-augmented-student-128-target-head-reload-01'/(r['id']+'_'+r['view']+'.logits.npy'))
    assert len(cases)==12 and len({r['key'] for r in cases})==12
    assert sum(r['role']=='hard-dev' for r in cases)==4
    # Source frame inheritance and a disjoint perturbation check, without opening test clips.
    for r in fitproto['reserved_requests']:
        f=ROOT/r['frames'];assert sha(f)==r['frames_sha256'];paths.add(f)
        c=next(t for t in cases if t['id']==r['id'] and t['view']=='clean')
        assert np.array_equal(np.load(ROOT/c['frame'],allow_pickle=False),np.load(f,allow_pickle=False)[r['timestamp_index']])
    # Preserve all already frozen fit inputs and their original training augmentation metadata.
    paths.update(ROOT/n for n in fitproto['frozen'])
    for c in [r for r in cases if r['view']=='hard-dev']:
        training=fitproto['hard_training'][c['id']];f=ROOT/training['student_file']
        assert sha(f)==training['student_sha256'];paths.add(f)
        assert not np.array_equal(np.load(f,allow_pickle=False),np.load(ROOT/c['frame'],allow_pickle=False))
    paths.update(HERE.glob('*.py'));paths.update(BASE/n for n in ['quality02.py','v4_recovery_native.py','fit.py','common_v4.py'])
    for n in ['M525-joint-augmented-student-128-protocol-02','M525-joint-augmented-student-128-target-head-capture-01',
              'M525-joint-augmented-student-128-target-head-reload-01','M525-joint-augmented-student-128-target-head-reload-protocol-01',
              'M536-V4-3584-recovery-protocol-01','M536-V4-3584-recovery-fit-01','M536-V4-3584-recovery-quality-01']:
        paths.add(RUNS/n/'RESULT.json')
    fit=read(FIT/'RESULT.json')
    for r in fit['variants']:
        if r.get('payload'):paths.add(ROOT/r['payload'])
    oldquality=read(RUNS/'M536-V4-3584-recovery-quality-01/RESULT.json')
    paths.update(ROOT/r['payload'] for r in oldquality['samples'])
    paths.update(HEAD/n for n in ['A.npy','B.npy','HEAD_MANIFEST.json','learned_head.py'])
    paths.update((OPT/'candidates/M525-10V18L-learned-head-augmented-01')/n for n in ['A.npy','B.npy','HEAD_MANIFEST.json'])
    paths.add(PARENT/'DEMO_BOARD_PLAN.json')
    paths.update((ROOT/'experiments/augmented_student_20261025')/n for n in ['target_reload.py','common_joint.py'])
    tokenizer=ROOT/'release_staging/kv260-mage-vl-4b-prebuilt-install-20260926-v7/deployment/mage_vl4b/m181_m120_video_board_candidate/text_auxiliary/tokenizer/tokenizer.json'
    paths.add(tokenizer)
    newarms=['exact_crop','reexport_crop','clean_recovery','harder_recovery']
    todo=[dict(arm=arm,case=c['key']) for arm in newarms for c in cases if not (arm=='harder_recovery' and c['view']=='clean')]
    assert len(todo)==40
    frozen={rel(f):sha(f) for f in sorted(paths)}
    v=dict(status='FROZEN_M537_MATCHED_PARENT_CHILD_AND_SAME_CHANNEL_RECOVERY_ABLATION',cases=cases,new_arms=newarms,todo=todo,
        tokenizer=rel(tokenizer),frozen=frozen,budgets=dict(reuse_seconds=300,evaluate_seconds=1800),
        counts=dict(parent_reused=12,harder_reused=8,new_full_prefills=len(todo),total_arm_cases=60),
        training=dict(new_updates=0,old_updates_each_learned_arm=128,same_fc1_and56groups=True,same_final_W4_quantizer=True,
            untrained_controls=['exact_crop','reexport_crop'],head_frozen=True,no_validation_based_epoch_or_group_selection=True),
        input_contract=dict(views=2,visual_slots=98,tokens=128,T32_batches=4,decode_calls=0),
        scope='8 clean development inputs (fixed4 + reserved4), plus4 old moderate_check perturbations. Not six-video clean12 or independent test.',
        hard_dev_caveat='These perturbations were previously used in frozen-head validation;unused for V4 fitting,not heldout or independent generalization.',
        original_M536_formal_board_FAIL_preserved=True,new_board_commands=0,heldout_opened=False,automatic_layer_expansion=False)
    save(PROTO,v)
    sys.path.insert(0,str(ROOT/'scripts/optimization'));from m455456_workflow02 import synchronized
    h=sha(PROTO);synchronized('latest_m537_v4_ablation_protocol01',dict(status=v['status'],result=rel(PROTO),sha256=h,board=False,promoted=False),
        '## M537 V4同通道恢复消融冻结\n\n协议SHA '+h+'。先复用12父/8子完整首步结果并逐SHA/输入/输出头核验，再仅补40缺失软件prefill；同56组、冻结head、清晰/困难两组均复用原128步终点，0新训练/板/heldout。加未训练W4重导出对照以分开量化影响；12输入是8清晰+4旧扰动，非独立泛化测试。M536原正式门禁FAIL不覆盖。')
    print(dict(protocol=rel(PROTO),sha256=h,frozen_files=len(frozen),new_prefills=len(todo)))
if __name__=='__main__':main()
