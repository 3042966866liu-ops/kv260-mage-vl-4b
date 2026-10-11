"""Read completed immutable software screen; no UART, model or hardware calls."""
import json,math
from m351_workflow import ROOT,BASE,atomic,encoded,sha,sync

def main():
    board=json.loads((ROOT/'deployment/mage_vl4b/BOARD_GATE_RESULT.json').read_bytes())
    e=board['latest_m426_range_software_board'];path=ROOT/e['result']
    assert path.parent.name=='M426-range-software-board-02' and sha(path)==e['sha256']
    assert all(e['sha256'] in (ROOT/n).read_text(encoding='utf-8-sig') for n in ('CURRENT_STATE.md','docsMILESTONES.md'))
    r=json.loads(path.read_bytes())
    assert not r['overlay_loaded'] and r['dma_allocations']==0 and r['fpga_transactions']==0 and r['language_forward_calls']==0 and not r['temperature_measurement_enabled']
    quality=r.get('full_visual_quality');failures=[]
    if quality:
        m=quality['metrics'];t=quality['thresholds']
        for metric,threshold,operator in [('relative_l2','maximum_relative_l2','<='),('cosine','minimum_cosine','>='),('min_token_cosine','minimum_token_cosine','>=')]:
            assert math.isfinite(m[metric])
            if (m[metric]>t[threshold] if operator=='<=' else m[metric]<t[threshold]):failures.append(dict(metric=metric,value=m[metric],operator=operator,threshold=t[threshold]))
        assert bool(not failures)==r['feature_screen_pass']
    done=r.get('software_screen_completed') is True
    if done:
        assert r['gate_return_code']==0 and r['visual_forward_calls']==2 and r['original_reference_pass'] and r['bindings_restored'] and r['visual_owner_closed'] and len(r['boundary_comparison'])==24
        status='FEATURE_SCREEN_PASS_TASK_PENDING' if r['feature_screen_pass'] else 'ALL22_FEATURE_REJECT_SOFTWARE_LOCALIZATION_REQUIRED'
        next_step=('复用保存的原版/候选特征，经相同原语言路径检查完整logits、K/V与固定任务判断；不重复视觉。任务质量通过后才准备完整视觉PL数值及净耗时验证。' if r['feature_screen_pass'] else '按24层累计边界记录冻结较小范围定位协议，仍以同一原版为参考，不调整阈值，不进入硬件性能。')
    else:
        assert r['gate_return_code']==1 and r['errors'];status='FAILED_DIAGNOSTIC_SAME_LEVEL_DEBUG_ONLY';next_step='排查本次软件入口失败；不能据此裁决量化质量或推进硬件。'
    checkpoints=[x for x in [r.get('memory_before_constructor'),r.get('memory_after_constructor')]+r.get('memory',[])+[r.get('memory_after_cleanup')] if isinstance(x,dict)]
    record=dict(status=status,raw_sha256=e['sha256'],manifest_sha256=r['manifest_sha256'],selected_layers=r['selected_layers'],
        software_screen_completed=done,feature_screen_pass=r['feature_screen_pass'],feature_criteria_failed=failures,
        feature_quality=quality,boundary_metrics=r['boundary_comparison'],logical_reference_calls=r.get('logical_reference_calls'),physical_reference_attempts=r.get('physical_reference_attempts'),
        original_visual=r.get('original_visual'),candidate_visual=r.get('candidate_visual'),retained_features=r.get('retained_features'),
        task_screen_pass=False,task_screen_recorded=False,hardware_visual_timing_unlocked=False,performance_pass=False,production_promoted=False,
        observed_memory=dict(minimum_MemAvailable_bytes=min(x['MemAvailable'] for x in checkpoints),peak_RSS_bytes=max(x['VmRSS'] for x in checkpoints),minimum_CmaFree_bytes=min(x['CmaFree'] for x in checkpoints)),
        PS_owner_closed=r['visual_owner_closed'],bindings_restored=r['bindings_restored'],temperature_measurement_enabled=False,
        original_topology_failure_preserved='2fc721ba6c70ed9d9f30618c0afeb21dd2410c873012a32dd42f373ae6588af8',
        quality_scope='One frozen last-frame two-view input; feature threshold screen only, no task or labeled accuracy evidence yet.',next_step=next_step)
    out=BASE/'runs/M426-range-software-closure-01/RESULT.json';atomic(out,encoded(record),immutable=True)
    report='# M426 22层视觉MLP精确软件筛查闭合\n\n'+f'裁决：**{status}**。原字节 SHA `{e["sha256"]}`。\n\n'
    report+='选定第2–23层共22层，仅MLP两个Linear使用已有精确A8/FP16/FTZ软件参考；原输入、前两层BF16、Attention、GELU、归一化、语言与线程/缓存策略保持。无Overlay、DMA、PL、语言前向或测温。\n\n'
    report+=f'完成软件筛查：{done}；原版视觉前向次数与候选总计 {r["visual_forward_calls"]}；逻辑参考批次 {r.get("logical_reference_calls","未记录")}；实际参考尝试 {r.get("physical_reference_attempts","未记录")}。\n\n'
    if quality:report+='完整特征判据及结果：\n\n```json\n'+json.dumps(quality,ensure_ascii=False,indent=2)+'\n```\n\n未通过项：\n\n```json\n'+json.dumps(failures,ensure_ascii=False,indent=2)+'\n```\n\n'
    report+='| 层 | 累计相对L2 | 余弦 | 最差token余弦 |\n|---|---:|---:|---:|\n'
    for row in r['boundary_comparison']:
        m=row['metrics'];report+=f'| {row["layer"]} | {m["relative_l2"]:.8f} | {m["cosine"]:.8f} | {m["min_token_cosine"]:.8f} |\n'
    report+='\n每层指标比较累计候选输出与固定原版同层输出，不能把相邻指标变化直接归因为该层本地敏感性。\n\n'
    report+='内存为观察值，不是性能：\n\n```json\n'+json.dumps(record['observed_memory'],indent=2)+'\n```\n\n'
    report+=f'PS owner关闭：{r["visual_owner_closed"]}；绑定/钩子恢复：{r["bindings_restored"]}。关闭对象不要求RSS立即回到初始值，RSS保留不能单独证明泄漏。\n\n'
    report+='首轮拓扑检查失败原证据保留，未执行模型前向；修正版只纠正BF16前缀直连检查，原算术/阈值不变。两层M425性能分支仍已关闭，其原裁决不改；已有语言并行核的40.81%完整请求性能结论独立保持。\n\n'
    report+='下一步：'+next_step+'\n\n本次未提供任务准确率、硬件数值或性能通过；不能据此晋级生产。\n'
    atomic(out.with_name('REPORT.md'),report.encode('utf-8'),immutable=True)
    sync('latest_m426_range_closure',dict(status=status,result=out.relative_to(ROOT).as_posix(),sha256=sha(out),raw_sha256=e['sha256'],feature_screen_pass=r['feature_screen_pass'],task_screen_pass=False,hardware_visual_timing_unlocked=False,performance_pass=False),
        f'## M426 较大视觉MLP软件范围闭合（2026-10-06）\n\nSHA {sha(out)}；原SHA {e["sha256"]}，{status}。22层完整累积feature判据不改；任务/硬件/性能尚未通过。PS owner关闭{r["visual_owner_closed"]}，钩子恢复{r["bindings_restored"]}，0Overlay/DMA/语言/PL/测温。首轮拓扑拒绝原证据保留，两层性能分支关闭裁决不改。下一步：{next_step}')
    print('M426_CLOSURE_SYNC',sha(out),status,json.dumps(quality))

if __name__=='__main__':main()
