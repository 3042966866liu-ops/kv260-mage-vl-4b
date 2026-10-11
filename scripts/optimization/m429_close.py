"""Close collected complete visual PL numerics; never rerun board/model."""
import json
from m351_workflow import ROOT,BASE,atomic,encoded,sha,sync
from m429_workflow03 import check

def main():
    board=json.loads((ROOT/'deployment/mage_vl4b/BOARD_GATE_RESULT.json').read_bytes());ev=board['latest_m429_late11_visual_PL_board'];path=ROOT/ev['result']
    assert sha(path)==ev['sha256'] and all(ev['sha256'] in (ROOT/n).read_text(encoding='utf-8-sig') for n in ('CURRENT_STATE.md','docsMILESTONES.md'))
    r=check(json.loads(path.read_bytes()));passed=r['status']=='PASS_M429_LATE11_COMPLETE_VISUAL_PL_NUMERICAL'
    status='CLOSED_M429_LATE11_VISUAL_PL_NUMERICS_PASS' if passed else 'CLOSED_M429_VISUAL_NUMERICAL_FAILURE'
    memory=r['memory'];rss=[x['VmRSS'] for x in memory if 'VmRSS' in x]
    next_step=('Freeze one bounded complete-visual warm comparison: unchanged CPU A versus late11 PL B, identical fixed input, four predeclared warmups and eight balanced formal samples. Light statistics only; no per-stage full hashes/array export in measured interval. Stop on quality/lifecycle/resource or cache-condition failure. Full-request comparison remains locked until worthwhile net visual benefit.' if passed else 'Debug only this actual failure level; preserve original bytes and stable restoration evidence. Do not run visual performance or language/full-request expansion.')
    record=dict(status=status,raw_sha256=ev['sha256'],gate_return_code=r['gate_return_code'],errors=r['errors'],build_id=r['build_id'],selected_layers=r['selected_layers'],
        visual_forward_calls=r['visual_forward_calls'],language_forward_calls=r['language_forward_calls'],
        matched_complete_input_output_batches=r.get('matched_wire_batches',0),all24_boundaries_exact=passed,complete_visual_feature_exact=passed,
        feature_quality=r.get('full_visual_quality'),saved_software_feature_source_sha256=r.get('software_reference_source_sha256'),saved_task_source_sha256=r.get('task_source_sha256'),
        allocations=len(r['allocations']),releases=len(r['releases']),planned_main_DMA_bytes=557056*4+163856+524288*2,
        physical_transactions_started=r['physical_transactions_started'],safe_buffers_released=r['safe_buffers_released'],unsafe_dma_buffers_retained=r['unsafe_dma_buffers_retained'],
        visual_owner_closed=r['visual_owner_closed'],bindings_restored=r['bindings_restored'],stable_restored=r['stable_restored'],
        memory_checkpoint_min_CmaFree_bytes=min((x['CmaFree'] for x in memory),default=None),
        memory_checkpoint_min_MemAvailable_bytes=min((x['MemAvailable'] for x in memory),default=None),
        memory_checkpoint_peak_RSS_bytes=max(rss,default=None),checkpoint_peaks_are_not_continuous=True,
        hardware_visual_timing_unlocked=passed,full_request_timing_unlocked=False,performance_pass=False,production_promoted=False,
        fixed_input_task_consistency_reused_not_dataset_accuracy=passed,temperature_measurement_enabled=False,next_step=next_step)
    out=BASE/'runs/M429-late11-visual-numerical-closure-01/RESULT.json';atomic(out,encoded(record),immutable=True)
    report=f'# M429 后11层完整视觉PL数值闭合\n\n{status}。原raw SHA `{ev["sha256"]}`，rc {r["gate_return_code"]}。\n\n'
    report+='固定末帧两视图，完整392行视觉前向只运行一次。仅13–23的MLP fc1/fc2使用现有并行核0x4D333537，Attention/GELU/归一化、原BF16前缀及其它层保持。不重跑原版或软件视觉，不执行语言，不测温。\n\n'
    report+=f'完整输入/输出wire校验 {record["matched_complete_input_output_batches"]}/286，24层边界及98×2560最终feature与M427保存软件参考逐位一致：{passed}。任务一致性复用M428相同候选feature的原语言输出，不是独立标注准确率。\n\n'
    if record['feature_quality']:report+='原版feature对照：\n\n```json\n'+json.dumps(record['feature_quality'],ensure_ascii=False,indent=2)+'\n```\n\n'
    report+=f'累计原owner分配/释放 {record["allocations"]}/{record["releases"]}；包含两组最小事务缓冲及七块main {record["planned_main_DMA_bytes"]}B。物理事务 {record["physical_transactions_started"]}，安全释放 {record["safe_buffers_released"]}，PS owner关闭 {record["visual_owner_closed"]}，绑定恢复 {record["bindings_restored"]}，稳定恢复 {record["stable_restored"]}。\n\n'
    report+='内存仅检查点：\n\n```json\n'+json.dumps({k:record[k] for k in ('memory_checkpoint_min_CmaFree_bytes','memory_checkpoint_min_MemAvailable_bytes','memory_checkpoint_peak_RSS_bytes')},ensure_ascii=False,indent=2)+'\n```\n\n'
    report+='这些不是连续峰值，CMA统计不是分配可行性的替代证明；本轮按原计划分配、封锁新增DMA、检查实际普通PS预算和64MiB MemAvailable余量，没有固定64MiB CMA floor。诊断含哈希/比较开销，其耗时不能报告为净提速。旧两层性能关闭、22层软件拒绝和此前语言并行40.81%收益各自保留。\n\n'
    if r['errors']:report+='原失败：\n\n```json\n'+json.dumps(r['errors'],ensure_ascii=False,indent=2)+'\n```\n\n'
    report+='下一步：'+next_step+'\n';atomic(out.with_name('REPORT.md'),report.encode('utf-8'),immutable=True)
    sync('latest_m429_late11_visual_numerical_closure',dict(status=status,result=out.relative_to(ROOT).as_posix(),sha256=sha(out),raw_sha256=ev['sha256'],hardware_visual_numerics_pass=passed,hardware_visual_timing_unlocked=passed,full_request_timing_unlocked=False,performance_pass=False),
        f'## M429 后11层完整视觉PL数值闭合（2026-10-06）\n\nSHA {sha(out)}；raw {ev["sha256"]}，{status}。286完整wire/24边界/finalfeature逐位一致{passed}；分配/释放{record["allocations"]}/{record["releases"]}、稳定恢复{record["stable_restored"]}。仅视觉数值，无语言重跑/温度/性能/生产晋级。下一步：{next_step}')
    print('M429_NUMERICAL_CLOSURE_SYNC',sha(out),status)

if __name__=='__main__':main()
