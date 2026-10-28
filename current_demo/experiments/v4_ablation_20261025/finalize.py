"""Close the finite offline study and verify synchronized current evidence."""
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
from common_ablation import *
def main():
    p=verify();audit=RUNS/'M537-V4-matched-ablation-audit-01';v=read(audit/'RESULT.json')
    assert v['primary_rc']==0 and v['counts']==dict(total=60,reused=20,new_full_prefills=40,new_optimizer_updates=0,board_commands=0)
    assert sha(HERE/'audit.py')==v['audit_source_sha256']
    expected={'parent4096':9,'exact_crop':9,'reexport_crop':9,'clean_recovery':9,'harder_recovery':10}
    assert all(v['summaries'][k]['all']['correct']==n for k,n in expected.items())
    diff=v['comparisons']['clean_recovery_vs_harder_recovery'];assert diff['new_failures']==[] and diff['recovered']==['cal_05_t1_clean']
    original_board=RUNS/'M536-V4-fixed-demo-board-02/Run/BOARD_RESULT.json'
    assert sha(original_board)=='c527efca30976579e4b0b8bd587077b64c3613dcb3c1df8c65bf1c7925649dad'
    fit=read(FIT/'RESULT.json');variants={r['name']:r for r in fit['variants']};local=[]
    for name in ['contribution_R0','clean_control','paired_harder_student']:
        r=variants[name]['metrics'];local.append(dict(method=name,fit_aggregate_relativeL2=r['aggregate']['relative_L2'],hard_training_mean_relativeL2=r['hard_mean_relativeL2']))
    report=audit/'REPORT.md';oldreport=sha(report)
    extra='''

结论与下一步：当前较难学生3584的两条错误均在父模型中存在，没有观察到V4缩宽新增错误。清晰恢复确实把训练聚合局部L2从27.13%降至13.00%，但本轮12条完整判断未比只裁剪多答对；较难恢复训练聚合L2为13.39%，在较难训练视图对清晰教师的重构均值由普通恢复21.20%降至20.22%，完整判断则额外修正cal_05_t1一条。局部特征改善、答案改善和独立泛化是三种不同结论。

cal_05_t1首token：父模型为“options”，原码只裁剪为“color”，未训练重导出为“data”，清晰恢复为“b”，较难恢复为“No”。虽然前四种也可能有正的No−Yes概率间隔，全词表另有更大logit；必须按实际全词表argmax将它们记为Invalid，不能按二分类间隔偷偷改成No。

4条较难开发输入五组均4/4，没有显示增强的额外判断收益。仅一个终点/种子、少量开发样本和非独立扰动，当前证据支持“观察到一条额外修正”，不支持宣称增强普遍提升泛化或已保证新视频正确。

保留现有已测较难学生3584研究组件、原4096父参考及所有未恢复/清晰恢复对照；本轮暂停扩层。下一具体质量工作应针对cal_03_t0漏判与cal_03_t1无效输出，先定位当前父主体/输出头的已有问题，再另行冻结实验；当前不自动重训或改prompt。M536板端计数断言FAIL及原退出码继续保持。M537没有新的板端速度结果。
'''
    with report.open('a',encoding='utf8') as f:f.write(extra)
    out=RUNS/'M537-V4-final-review-01';out.mkdir(exist_ok=False)
    source={rel(f):sha(f) for f in HERE.glob('*.py')}
    files={rel(audit/'RESULT.json'):sha(audit/'RESULT.json'),rel(report):sha(report),rel(audit/'ANSWERS.csv'):sha(audit/'ANSWERS.csv'),
        rel(PROTO):sha(PROTO),rel(REUSE/'RESULT.json'):sha(REUSE/'RESULT.json'),rel(OUT/'RESULT.json'):sha(OUT/'RESULT.json')}
    result=dict(status='CLOSED_M537_MATCHED_V4_CAUSALITY_AND_RECOVERY_ABLATION_NOT_BOARD',primary_rc=0,
        original_audit_report_sha256=oldreport,files=files,source_sha256=source,local_metrics_from_original_fit=local,
        counts=v['counts'],all_host_native_exit0=True,original_board_result_sha256=sha(original_board),original_gate_FAIL_preserved=True,
        next_step='Retain current research component and parent/ablation controls;pause layer expansion. Diagnose existing parent cal03 errors in a separately frozen experiment;no automatic training/prompt/board changes.',
        heldout_opened=False,new_board_commands=0,new_TTFT=False,promoted=False)
    save(out/'RESULT.json',result)
    sys.path.insert(0,str(ROOT/'scripts/optimization'));from m455456_workflow02 import synchronized
    h=sha(out/'RESULT.json');key='latest_m537_v4_final_review01'
    note='## M537 V4父子与同通道恢复消融闭合\n\nRESULT SHA '+h+'，报告 '+rel(report)+'，报告SHA '+sha(report)+'。原4096/原码3584/未训练W4重导出/清晰恢复/较难恢复共12输入正确数9/9/9/9/10；固定4均全对，reserved分别1/1/1/1/2，较难开发4均全对。仅较难恢复修正cal05t1，0新增错；cal03t0漏判及cal03t1无效均父模型已有。不能从一例称普遍泛化改善。20复用+40新软件prefill，0新训练/heldout/板命令，无新TTFT；M536原板门禁FAIL/rc1保留。下一先定位父模型cal03已有问题，暂停扩层，不自动改prompt或重训。'
    synchronized(key,dict(status=result['status'],result=rel(out/'RESULT.json'),sha256=h,report=rel(report),report_sha256=sha(report),board=False,promoted=False),note)
    # Read complete current records after the synchronized update, not chat memory.
    for name in ['CURRENT_STATE.md','docsMILESTONES.md','DEPLOYMENT_OPERATION_MISTAKES_REVIEW.md','deployment/mage_vl4b/BOARD_GATE_RESULT.json']:
        text=(ROOT/name).read_text(encoding='utf-8-sig')
        if 'MISTAKES' not in name:assert h in text and key in text,name
    for f,d in files.items():assert sha(ROOT/f)==d
    print(dict(status=result['status'],result=rel(out/'RESULT.json'),sha256=h,report=rel(report),report_sha256=sha(report),three_sync_verified=True))
if __name__=='__main__':main()
