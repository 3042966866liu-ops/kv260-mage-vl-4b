"""Adjudicate exactly the saved original sequence; deliver two independent conclusions."""
import json
import statistics
from pathlib import Path
import m351_workflow as w
from m441_host_io08 import atomic
from m443_performance_collect01 import PKG,check
from m437_sequence import adjudicate


def main():
    assert w.sha(w.HERE/'m437_sequence.py')==w.sha(PKG/'m437_sequence.py'),'Frozen adjudicator differs'
    board=json.loads((w.ROOT/'deployment/mage_vl4b/BOARD_GATE_RESULT.json').read_bytes())
    evidence=board['latest_m443_complete_request_board01'];p=w.ROOT/evidence['result']
    assert w.sha(p)==evidence['sha256']
    assert all(evidence['sha256'] in (w.ROOT/n).read_text(encoding='utf-8-sig') for n in ('CURRENT_STATE.md','docsMILESTONES.md'))
    r=check(json.loads(p.read_bytes()));samples=r.get('samples',[])
    if r['status']=='PASS_M443P_NATURAL_IO_MEASUREMENTS_COLLECTED':verdict=adjudicate(r['formal_samples'])
    else:verdict=dict(status='CLOSED_M443_EXPERIMENT_CONDITIONS_NOT_ESTABLISHED' if r.get('experiment_stop') else 'CLOSED_M443_ORIGINAL_GATE_FAILURE',performance_pass=False,experiment_stop=r.get('experiment_stop'),errors=r['errors'],additional_samples_allowed=False)
    parser=w.BASE/'runs/M442-complete-request-parser-closure-01/RESULT.json'
    assert w.sha(parser)=='4aaf39b4059d41b83f1164822a30f3d1b2916e737ddd124a55694b6838d9c035'
    parser_raw=w.BASE/'runs/M442-complete-request-parser-board-01/BOARD_RESULT.json'
    assert w.sha(parser_raw)=='6a17bf72dd5b15e632e6139668e8c2d67be282b544ce895fa8655153e7c71f63'
    m442=json.loads(parser.read_bytes());assert m442['status']=='PASS_NATURAL_IO_FULL_REQUEST_BENEFIT' and m442['performance_pass']
    stages={}
    for variant in ('A','B'):
        rows=[s for s in r.get('formal_samples',[]) if s['variant']==variant]
        if rows:stages[variant]={k:dict(mean_ms=statistics.mean(s['timing']['stages_ms'][k] for s in rows),range_ms=max(s['timing']['stages_ms'][k] for s in rows)-min(s['timing']['stages_ms'][k] for s in rows)) for k in ('preprocess','vision','prefill','head')}
    result=dict(raw_result=evidence['result'],raw_sha256=evidence['sha256'],build_id='0x4D343433',baseline_build_id='0x4D343431',temperature_measurement_enabled=False,completed_requests=len(samples),formal_requests=len(r.get('formal_samples',[])),stage_summary=stages,numerical_pass=r.get('numerical_pass',False),safe_buffers_released=r.get('safe_buffers_released',False),stable_overlay_reloaded=r.get('stable_overlay_reloaded',False),performance_scope='Fixed159 last-frame two-view original single-parser resident requests, including natural I/O; A M441 hardware versus B M443 hardware, same M437 late11 PL visual and original full math.',semantic_accuracy_proven=False,expanded_layers=False,production_promoted=False,m442_independent_result=parser.relative_to(w.ROOT).as_posix(),m442_independent_sha256=w.sha(parser),m442_raw_sha256=w.sha(parser_raw),independent_benefits_must_not_be_added=True,source_sha256=w.sha(Path(__file__)))
    result.update(verdict)
    out=w.BASE/'runs/M443-complete-request-closure-01';atomic(out/'RESULT.json',w.encoded(result),immutable=True)
    report='# M442 与 M443 两项独立完整请求裁决\n\n'
    report+='M442解析器：原独立完整请求实验已闭合，'+m442['status']+'。A平均94.760294961s，B平均93.591876212s，减少1.168418749s（1.233025656%），四配对95%区间[0.874005803,1.462831695]s，两顺序组均为正收益。保持同M441硬件、同M437 late11视觉、原完整数学、单parser无预读、七驻留DMA、12805物理提交及零请求间编程；原A53组件较慢的独立结论保留。raw SHA '+w.sha(parser_raw)+'；closure SHA '+w.sha(parser)+'。未重跑M442。\n\n'
    report+='M443硬件：'+result['status']+'。原始SHA '+evidence['sha256']+'。A为M441，B为独立M443新核（0x4D343433）；两版使用同一原解析器、同M437后11层视觉和完整数学。同输入、提示、原语言路径、七驻留DMA及普通PS预算。八次核切换及合法最小证明在请求计时外，每次实际同PID/PFN1904配置页释放及零未知申请/零事件丢失后才允许记账，原累计baseline保持。未加入M442解析收益。\n\n'
    report+='| 次序 | 阶段 | 版 | 完整请求s | 视觉s | prefill s | head s（含在prefill） | 读盘MiB | major faults |\n|---:|---|---|---:|---:|---:|---:|---:|---:|\n'
    for s in samples:
        t=s['timing'];stage=t['stages_ms'];report+=f'| {s["index"]} | {s.get("phase","completed")} | {s["variant"]} | {t["total_ms"]/1000:.6f} | {stage["vision"]/1000:.6f} | {stage["prefill"]/1000:.6f} | {stage["head"]/1000:.6f} | {s["io_delta"]["read_bytes"]/(1<<20):.6f} | {s["major_fault_delta"]} |\n'
    if 'blocks' in verdict:
        ci=verdict['paired_95percent_CI_ms'];report+=f'\nM443八次总体均值：A {verdict["A_mean_ms"]/1000:.9f}s，B {verdict["B_mean_ms"]/1000:.9f}s，减少 {verdict["paired_mean_gain_ms"]/1000:.9f}s（{verdict["gain_percent"]:.9f}%）。四配对95% t区间（df=3）：[{ci[0]/1000:.9f}, {ci[1]/1000:.9f}]s。\n\n'
        report+='| 顺序组 | A平均s | B平均s | 减少s | 减少比例 |\n|---|---:|---:|---:|---:|\n'
        for b in verdict['blocks']:report+=f'| {b["order"]} | {b["A_mean_ms"]/1000:.9f} | {b["B_mean_ms"]/1000:.9f} | {b["gain_ms"]/1000:.9f} | {b["gain_percent"]:.9f}% |\n'
        report+='\n预定条件为两组正收益且95%区间下界>0；'+('通过。' if verdict['performance_pass'] else '本次未可靠测出正收益，关闭本次硬件变体性能实验。')+'固定4预热ABBA及8正式ABBABAAB，所有自然I/O样本保留，不删样本、不追加、不拟合新门限。\n'
    else:report+='\n原失败或停止：\n```json\n'+json.dumps(verdict,ensure_ascii=False,indent=2)+'\n```\n不能据未完整建立的对照评价提速，不补跑请求。\n'
    report+='\nM443安全释放/稳定硬件恢复：'+str(r.get('safe_buffers_released'))+'/'+str(r.get('stable_overlay_reloaded'))+'。两项收益独立，不相加；没有共同变体实测。原失败尝试及原M441性能17/W2W4闭合23均保留。固定输入数值一致和完整请求收益不证明任意输入正确、语义标注准确率、24层适用性、生产服务或自动晋级。稳定源/服务/boot/DTB/CMA/slotbank未更改。\n'
    atomic(out/'REPORT.md',report.encode('utf-8'),immutable=True);w.atomic=atomic;s=w.sha(out/'RESULT.json')
    w.sync('latest_m443_complete_request_closure01',dict(status=result['status'],result=(out/'RESULT.json').relative_to(w.ROOT).as_posix(),sha256=s,raw_sha256=evidence['sha256'],build_id='0x4D343433',performance_pass=result['performance_pass'],production_promoted=False,m442_independent_sha256=w.sha(parser)), '## M443同视觉原完整请求独立裁决01（2026-10-11）\n\nSHA '+s+'，原raw '+evidence['sha256']+'；'+result['status']+'，完成'+str(len(samples))+'次/正式'+str(result['formal_requests'])+'次。原完整参考及配置ledger/七owner释放/稳定恢复严格重核。独立报告同时引用M442既有1.233025656%收益且不相加，不追加/生产晋级；REPORT.md为两项交付。')
    print('M443_CLOSURE_SYNC',s,result['status']);print(json.dumps(verdict,ensure_ascii=False))


if __name__=='__main__':main()
