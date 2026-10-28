"""Freeze a full-batch curriculum with known errors explicitly reclassified as fit."""
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
from common_fix import *
def main():
    action=sys.argv[1];assert action in ['frames','training']
    if action=='frames':
        old=RUNS/'M541-demo-adaptation-fit-01/RESULT.json';v=read(old);assert v['primary_rc']==0 and v['selected_arm'] is None
        source=read(RUNS/'M541-demo-adaptation-sources-01/RESULT.json');videos={r['id']:r for r in source['sources']}
        cases=[dict(id='campus03_f'+str(i).zfill(5),video='campus_03',index=i,expected=t) for i,t in [(12,'No'),(56,'Yes'),(72,'Yes'),(88,'Yes'),(200,'No')]]
        cases.append(dict(id='campus12_f00432',video='campus_12',index=432,expected='No'))
        oldcases=read(RUNS/'M541-demo-adaptation-protocol-03/RESULT.json')['student_cases']
        assert not {r['id'] for r in cases}&{r['id'] for r in oldcases}
        paths=[HERE/'common_fix.py',HERE/'frames.py',HERE/'host.py',HERE/'prepare.py',old]
        p=dict(status='FROZEN_M542_NEW_TEMPORAL_CHECKS_AFTER_UNACCEPTED_M541',videos=videos,new_temporal_cases=cases,budgets=dict(frames_seconds=180),
            previous_clean_correct=18,previous_harder_correct=19,previous_acceptance_n=21,previous_failed_candidate_preserved=True,
            frozen={rel(f):sha(f) for f in paths},new_training=False,board_commands=0)
        p['frozen'].update({r['path']:r['sha256'] for r in videos.values()});dest=FRAMEPROTO
    else:
        verify(FRAMEPROTO);f=read(FRAMES/'RESULT.json');assert f['primary_rc']==0 and len(f['records'])==12
        c=read(CAP/'RESULT.json');assert c['primary_rc']==0 and len(c['student'])==37
        save(FRAMES/'VISUAL_REVIEW.json',dict(status='ASSISTANT_REVIEWED_ALL12_NEW_TEMPORAL_VIEWS',
            note='Frame12 emptybuildingNo;56/72/88 clearknifeYes;200 no visibleknifeNo;phone432No. Both clean/hard views preserve visible content.',human_annotation=False,independent_sources=False))
        old=read(RUNS/'M541-demo-adaptation-protocol-03/RESULT.json');frozen=dict(old['frozen'])
        paths=list(HERE.glob('*.py'))+[CAP/'RESULT.json',FRAMES/'RESULT.json',FRAMES/'VISUAL_REVIEW.json',RUNS/'M541-demo-adaptation-fit-01/RESULT.json']
        for r in c['student']:paths.append(ROOT/r['source'])
        for r in c['teacher']:paths.append(ROOT/r['source'])
        for r in f['records']:paths.append(ROOT/r['frame'])
        for path in paths:
            if path.suffix=='.py':compile(path.read_text(encoding='utf8'),str(path),'exec')
        frozen.update({rel(path):sha(path) for path in paths})
        known=[r for r in old['student_cases'] if r['role'] in ['known-demo-regression','legacy-fit']]
        assert len(known)==13
        p=dict(status='FROZEN_M542_FULL_BATCH_CLEAN_HARDER_DEMO_COUNTEREXAMPLE_REPLAY',frozen=frozen,vision=old['vision'],language=old['language'],token_ids=old['token_ids'],
            training=dict(seed=542,steps_per_arm=400,learning_rate=.0005,rank=8,clean_prefix=64,teacher_KL=.02,legacy_KL=.05,
                batch='All37 captured current student rows each step,class-balanced. Clean arm substitutes clean counterpart for each augmented row;harder arm usesboth clean andhard after64. Same row count/update budget.',
                selection='Only final400 checkpoints;preferharder ifall37fitcorrect,elsecleanifall37fitcorrect,else no candidate. New12checks never select arm/epoch.',
                source_policy='All prior37including knownfailures/freshdev explicitly become demonstrationfit. Original reserved/test unused. Not independent accuracy.',
                KD_policy='Existing deeper clean teacher8 reused only for its matching16clean/hard rows;legacy4 oldhead distribution replay;other17 labelCE only,not falsely called teacher-distilled.'),
            new_checks=f['records'],regression_cases=known,budgets=dict(fit_seconds=1200,reload_seconds=1500,reload_prefills=25),
            prior_failed_final_checkpoints_preserved=True,original_body_frozen=True,no_new_inference_rank_or_module=True,board_commands=0,heldout_opened=False)
        dest=PROTO
    save(dest,p);sys.path.insert(0,str(ROOT/'scripts/optimization'));from m455456_workflow02 import synchronized
    h=sha(dest);synchronized('latest_m542_'+action+'_protocol01',dict(status=p['status'],result=rel(dest),sha256=h,board=False,promoted=False),
        '## M542展示反例回放新协议 '+action+'\n\nRESULT SHA '+h+'；M541清晰18/21、困难19/21均不接受，原三阳性已修但空楼宇误报和新姿态漏判保持。新协议明确把原37全部作为展示fit，完整平衡批次每步同时回放清晰/较难，不再只替换清晰；clean/harder各400固定终点、前64相同、rank8/原身体不改。先预定6新时点清晰+困难12检查（未进梯度），最终按fit选头后再与13回归共25完整重载，0新教师/板/原reserved/test；不是在旧协议内搜索epoch或改写失败。演示适配非独立泛化。')
    print(dict(status=p['status'],sha256=h))
if __name__=='__main__':main()
