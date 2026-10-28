"""Freeze matched final checkpoints after reviewing all new clean/harder frames."""
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
from common_adapt import *
def main():
    verify(SOURCE);frames=read(FRAMES/'RESULT.json');assert frames['primary_rc']==0
    for r in frames['records']:
        assert sha(ROOT/r['frame'])==r['frame_sha256'] and sha(ROOT/r['png'])==r['png_sha256']
    save(FRAMES/'VISUAL_REVIEW.json',dict(status='ASSISTANT_REVIEWED_ALL24_CLEAN_AND_HARDER_VIEWS',
        observations='CONTACT1/2 reviewed:fit52/68/84 andfresh60/76 preserve clear knife;fit6/176,fresh208 show no visibleknife;phone fit48/288/576,fresh360 show phone/no knife. Mild aug doesnotcropocclude orchange label.',
        human_annotation=False,source_group_independent_test=False,model_runs_before_review=0))
    cases=[]
    for r in frames['records']:
        cases.append(dict(r,key=r['id']+'_'+r['view'],target=9454 if r['expected']=='Yes' else 2753))
    for stage in ['M539-campus12-demo-software-quality-01','M540-campus03-demo-software-quality-01']:
        for r in read(RUNS/stage/'RESULT.json')['samples']:
            proto=read(RUNS/('M539-campus12-demo-quality-protocol-01' if 'M539' in stage else 'M540-campus03-demo-quality-protocol-01')/'RESULT.json')
            c=next(t for t in proto['cases'] if t['id']==r['id'])
            cases.append(dict(c,key=r['id']+'_known-check',role='known-demo-regression',view='clean',target=9454 if r['expected']=='Yes' else 2753,original_logits=dict(payload=r['payload'],sha256=r['sha256'])))
    old_quality=read(RUNS/'M536-V4-3584-recovery-quality-01/RESULT.json');plan=read(PARENT/'DEMO_BOARD_PLAN.json')
    for r in plan['demo_requests']:
        c=next(x for x in old_quality['samples'] if x['id']==r['id'] and x['arm']=='recovered3584')
        f=PARENT/r['frame_path'];assert sha(f)==r['frame_sha256']
        cases.append(dict(id=r['id'],key=r['id']+'_legacy-fit',role='legacy-fit',view='clean',frame=rel(f),frame_sha256=sha(f),expected=r['expected_decision'],
            target=9454 if r['expected_decision']=='Yes' else 2753,original_logits=dict(payload=c['payload'],sha256=c['sha256'])))
    assert len(cases)==37 and len({r['key'] for r in cases})==37
    teachers=[r for r in cases if r['role']=='fit' and r['view']=='clean'];accept=[r for r in cases if r['role']!='fit']
    assert len(teachers)==8 and len(accept)==21
    frozen=dict(read(RUNS/'M540-campus03-demo-quality-protocol-01/RESULT.json')['frozen'])
    sources=list(HERE.glob('*.py'))+[SOURCE,FRAMES/'RESULT.json',FRAMES/'VISUAL_REVIEW.json',PARENT/'DEMO_BOARD_PLAN.json']
    for r in cases:
        sources.append(ROOT/r['frame'])
        if r.get('original_logits'):sources.append(ROOT/r['original_logits']['payload'])
    sources.extend(HEAD/n for n in ['A.npy','B.npy','learned_head.py','HEAD_MANIFEST.json'])
    for f in sources:
        if f.suffix=='.py':compile(f.read_text(encoding='utf8'),str(f),'exec')
    frozen.update({rel(f):sha(f) for f in sources})
    p=dict(status='FROZEN_M541_MATCHED_DEMO_HEAD_REPAIR_CLEAN_VS_HARDER',frozen=frozen,student_cases=cases,teacher_cases=teachers,
        vision=plan['retained_vision'],language=plan['retained_language'],token_ids=plan['token_ids'],
        training=dict(seed=541,rank=8,learning_rate=.0001,steps_per_arm=256,clean_steps=64,teacher_KL=.02,legacy_KL=.05,
            batch='One balanced new positive/negative plus one legacy positive/negative eachstep',
            teacher='Deeper V24L36 frozen lowbit parent,originalV4,clean input,no learned head. Wrong teacher full argmax disables KD;label CE remains.',
            student='Actual frozen V10L18 with deployedV4_3584,preA8 hidden and actual base logits. Only originalrank8 A/B train;no body updates.',
            arms=['clean_control','harder_student'],selection='Fixed256stepfinal only;preferharder ifall21correct,elsecleanifall21correct,elsenoexportselection.'),
        budgets=dict(capture_seconds=1800,fit_seconds=900,reload_seconds=1200,teacher_prefills=8,student_capture_prefills=37,reload_prefills=21),
        wider_original_reserved_not_trained=True,six_original_test_closed=True,known_demo_failures_now_development_not_independent=True,
        no_binary_mask_or_source_ID_in_inference=True,new_board_commands=0,new_TTFT=False,
        distinction='Head adaptation,not new body feature distillation;V4 body recovery fromM536 remains unchanged. No new inference rank/network.')
    save(PROTO,p)
    sys.path.insert(0,str(ROOT/'scripts/optimization'));from m455456_workflow02 import synchronized
    h=sha(PROTO);synchronized('latest_m541_demo_repair_protocol01',dict(status=p['status'],result=rel(PROTO),sha256=h,board=False,promoted=False),
        '## M541演示域成对恢复训练冻结\n\n协议SHA '+h+'；24清晰/困难图已逐图检查刀具保留。新8时点fit（3阳/5阴含同背景无刀）、4旧fit回放；9已知失败/手机回归与8新同源清晰/困难开发仅验收。8深度24V36低比特清晰教师，实际10V18L/V43584学生37前向采preA8隐藏；rank8头clean/harder各256步同初值/前64清晰，错误教师不做KL、只标签CE，旧fit蒸馏回放。只按两个最终点选择（优先困难臂21验收全对），0epoch/seed搜索、0原reserved/test训练。重载21完整学生再核导出，不当实板或独立泛化；不增加推理rank/模块。M540原FAIL保留。')
    print(dict(status=p['status'],sha256=h,cases=len(cases),acceptance=len(accept)))
if __name__=='__main__':main()
