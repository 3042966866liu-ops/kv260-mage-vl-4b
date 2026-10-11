"""Adjudicate every new parser-width sample, with the original conservative rule."""
import json
import statistics
import m351_workflow as w


def describe(values):
    return dict(n=len(values), mean_ms=statistics.mean(values),
                median_ms=statistics.median(values), minimum_ms=min(values),
                maximum_ms=max(values), range_ms=max(values)-min(values))


def compare(samples):
    answer = {}
    for metric in ('total_ms', 'first_token_ms'):
        a = describe([s['timing'][metric] for s in samples if s['variant']=='A'])
        b = describe([s['timing'][metric] for s in samples if s['variant']=='B'])
        saved = a['mean_ms']-b['mean_ms']
        answer[metric] = dict(A=a, B=b, saved_ms=saved,
                             reduction_percent=100*saved/a['mean_ms'],
                             speedup=a['mean_ms']/b['mean_ms'])
    return answer


def main():
    raw = w.BASE/'runs/M381-gate-up-performance-board-01/BOARD_RESULT.json'
    result = json.loads(raw.read_text(encoding='utf-8'))
    digest = w.sha(raw)
    board = json.loads((w.ROOT/'deployment/mage_vl4b/BOARD_GATE_RESULT.json').read_text(encoding='utf-8'))
    assert board['latest_m381_gate_up_performance_board']['sha256']==digest
    assert all(digest in (w.ROOT/n).read_text(encoding='utf-8-sig') for n in ('CURRENT_STATE.md','docsMILESTONES.md'))
    assert result['status']=='PASS_M381_LIGHT_VIDEO_MEASUREMENTS'
    assert result['numerical_pass'] and not result['errors'] and not result['performance_pass']
    assert result['order']=='ABBABAAB' and len(result['samples'])==8
    overall = compare(result['samples'])
    orders = dict(ABBA=compare(result['samples'][:4]), BAAB=compare(result['samples'][4:]))
    total = overall['total_ms']
    within = max(total['A']['range_ms'], total['B']['range_ms'])
    order_gain = min(x['total_ms']['saved_ms'] for x in orders.values())
    separation = total['A']['minimum_ms']-total['B']['maximum_ms']
    benefit = order_gain>within and separation>0
    status = 'PASS_FIXED_VIDEO_TWO_PARSER_NET_BENEFIT' if benefit else 'CLOSED_TWO_PARSER_VARIANT_NET_BENEFIT_UNPROVEN'
    # Reuse the completed M372 audit; no repeated component tests or changed guard.
    review_path = w.BASE/'runs/M372-prefetch-and-future-review-01/RESULT.json'
    review = json.loads(review_path.read_text(encoding='utf-8'))
    assert w.sha(w.HERE/'ps_read_ahead.py')==review['component_sha256']
    admissions = []
    for sample in result['samples']:
        memory = sample['before_memory']['system_bytes']
        cma = memory['CmaFree']; available = memory['MemAvailable']
        admissions.append(dict(index=sample['index'], variant=sample['variant'],
                               before_request_cma_bytes=cma,
                               before_request_available_bytes=available,
                               unchanged_PS_component_would_admit=(cma>=64<<20 and available>=(64<<20)+27852800)))
    ps_review = dict(reused_m372_review_sha256=w.sha(review_path),
                     component_sha256=review['component_sha256'],
                     slot_bytes=27852800, extra_cma_allocations=0, additional_worker=1,
                     foreground_copy_and_sync_remain=True,
                     original64MiB_guard_unchanged=True,
                     current_request_entry_observations=admissions,
                     slot_allocated_in_this_test=False, ps_worker_started_in_this_test=False,
                     actual_slot_capacity_proven=False,
                     next_step='Justify separate sealed-DMA load-plus-PS-slot diagnostic admission, then measure touched slot and lifecycle before any model binding; do not lower production guard')
    value = dict(status=status, raw_sha256=digest, numerical_pass=True,
                 performance_pass=benefit, formal_promotion_allowed=False,
                 stable_service_changed=False, production64MiB_unchanged=True,
                 both_build_id='0x4D333537', ps_prefetch_enabled=False,
                 historical_hardware_40_81_percent_result_unchanged=True,
                 measurement_scope=result['measurement_scope'], order=result['order'],
                 overall=overall, orders=orders,
                 conservative_check=dict(min_order_mean_saved_ms=order_gain,
                                         max_within_variant_range_ms=within,
                                         minimum_A_minus_maximum_B_ms=separation),
                 native_instantaneous_peak_certified=False,
                 existing_ps_read_ahead_assessment=ps_review,
                 all_samples=result['samples'],
                 next_step=('Keep this isolated candidate; daily-service admission needs separate evidence'
                            if benefit else 'Close two-parser variant; evaluate existing M350/M351 PS pre-read without scanning thread counts'))
    out = w.BASE/'runs/M381-gate-up-performance-closure-01'
    w.atomic(out/'RESULT.json', w.encoded(value), immutable=True)
    closure_sha = w.sha(out/'RESULT.json')
    rows = []
    memory_rows = []
    for sample in result['samples']:
        timing = sample['timing']; stages = timing['stages_ms']
        rows.append('| {} | {} | {:.3f} | {:.3f} | {:.3f} | {:.3f} | {:.3f} | {:.3f} |'.format(
            sample['index'], sample['variant'], timing['total_ms']/1000,
            timing['first_token_ms']/1000, stages['preprocess']/1000,
            stages['vision']/1000, stages['prefill']/1000, stages['head']/1000))
        extrema = sample['sampled_memory']['extrema']
        memory_rows.append('| {} | {} | {:.3f} | {:.3f} | {:.3f} | {:.3f} |'.format(
            sample['index'], sample['variant'], sample['io_delta']['read_bytes']/(1<<20),
            extrema['max_rss']/(1<<20), extrema['min_cma']/(1<<20), extrema['min_available']/(1<<20)))
    order_rows = []
    for name, group in orders.items():
        x = group['total_ms']
        order_rows.append(f'| {name} | {x["A"]["mean_ms"]/1000:.3f} | {x["B"]["mean_ms"]/1000:.3f} | {x["saved_ms"]/1000:.3f} | {x["reduction_percent"]:.2f}% |')
    report = f'''# gate_up 双解析 worker 完整视频请求对照

裁决：**{status}**。

两组均使用当前并行硬件 Build **0x4D333537**。A 是原来的单解析 worker；B 仅 gate_up 使用两个解析 worker。原解析数学、两个 DMA 输出缓冲、缩放重试、输入和计时方法一致；PS 权重预读关闭。

完整请求平均耗时 A **{total['A']['mean_ms']/1000:.3f}s**，B **{total['B']['mean_ms']/1000:.3f}s**。平均差值 **{total['saved_ms']/1000:.3f}s（{total['reduction_percent']:.2f}%）**。这是新的 PS 调度对照，此前硬件改动得到的约 **40.81%** 完整请求降幅保持为独立结论。

采用全部八次 ABBABAAB 样本。沿用原保守裁决：两种顺序最小均值差 {order_gain/1000:.3f}s，必须超过组内最大范围 {within/1000:.3f}s，且所有 A 的最小耗时必须高于所有 B 的最大耗时；本次后者差值 {separation/1000:.3f}s。没有选最快样本，也没有给出总体统计置信度。

| 次序 | 变体 | 完整请求s | 首tokens | 预处理s | 视觉s | Prefill含heads | heads |
| --- | --- | --- | --- | --- | --- | --- | --- |
{chr(10).join(rows)}

| 顺序 | A均值s | B均值s | 差值s | 降幅 |
| --- | --- | --- | --- | --- |
{chr(10).join(order_rows)}

每次请求在计时结束后核对完整视觉特征、159-token 语言输入、151936 logits、72 份 K/V、最终判断、778 次逻辑/781 次物理调用及三次原语言重试。每次同 Overlay 最小事务另记，总事务 {result['fpga_transactions_total']}。七块原 DMA 缓冲安全逆序释放；每请求四个运行时覆盖绑定恢复并清除 owner 注册表；B 每次只覆盖 36 次 gate_up。没有增加 CMA 缓冲。

| 次序 | 变体 | 实际磁盘读取MiB | 100ms最大RSS MiB | 最小CmaFree MiB | 最小MemAvailable MiB |
| --- | --- | --- | --- | --- | --- |
{chr(10).join(memory_rows)}

原视觉懒缓存一次预热，26 项、66,699,264 字节，两组共用相同 PS 对象。每次保存请求前后缓存、I/O 和内存记录，不清文件缓存。源校验、运行时构造、Overlay 加载、数值 SHA 和候选 AST 准备都在原请求计时之外。Prefill 已包含 head，不能将两列相加。100ms 采样不证明 native 瞬时峰值或长期服务内存稳定。

本次仍是原四个源帧中最后一帧的两视图、98 视觉 token、159 语言 token、decode=0；不代表四帧时序理解或任意输入。独立诊断规则及原生产 64MiB 门槛保持，稳定服务、回滚、boot/DTB/CMA 未替换，结束恢复稳定 Overlay，没有正式晋级。

后续：{value['next_step']}。

已有 M350/M351 PS 预读方案的后续评估复用 M372 完成的审计，组件 SHA 保持 `{review['component_sha256']}`，未重复 CPU 门禁。它需要 27,852,800 字节普通 PS slot 和一个后台读取 worker，显式额外 DMA 分配为 0；前景复制及同步仍存在。其原 `_memory()` 在创建 slot、复制前都要求 CmaFree ≥64MiB，此规则未改。已把本次八次请求入口的实际 CmaFree/MemAvailable 以及这一原规则是否准入，逐项保存在解读 JSON。通过无额外 slot 的视频不证明加入 slot 后的容量，因此没有直接启用预读。

若本变体关闭，下一具体问题是独立论证并测量“已封锁新增 DMA 的完整 runtime＋触页 PS slot”的容量和生命周期，再逐级数值验证。需要保留普通 PS 增长之外的余量，并验证文件页缓存、临时视图、worker 异常保留及 owner 清理；不能仅根据总 MemAvailable 充足推定可运行，也不能悄悄下调生产 64MiB 门槛。

原始结果 SHA：`{digest}`。
解读 SHA：`{closure_sha}`。
'''
    w.atomic(out/'REPORT.md', report.encode('utf-8'), immutable=True)
    w.sync('latest_m381_gate_up_performance_closure',
           dict(status=status, result=(out/'RESULT.json').relative_to(w.ROOT).as_posix(),
                sha256=closure_sha, raw_sha256=digest, numerical_pass=True,
                performance_pass=benefit, formal_promotion_allowed=False),
           f'## M381 单/双解析 worker 完整固定视频性能裁决（2026-10-03）\n\n'
           f'原 SHA {digest}；解读 SHA {closure_sha}。两组同 Build0x4D333537，A 原1/B gate_up2，'
           f'八次全部数值/事务/重试/七缓冲和 owner 清理正确。完整请求均值 A {total["A"]["mean_ms"]/1000:.3f}s、'
           f'B {total["B"]["mean_ms"]/1000:.3f}s；差 {total["reduction_percent"]:.2f}%。'
           f'最小顺序差 {order_gain/1000:.3f}s、组内范围 {within/1000:.3f}s、分离 {separation/1000:.3f}s；'
           f'裁决 {status}。旧硬件40.81%结论不变；无 PS 预读、0额外CMA；'
           f'原生产64MiB/服务/回滚保持且恢复稳定 Overlay，未晋级。下一步 {value["next_step"]}。')
    print(json.dumps(dict(status=status, overall=overall, orders=orders,
                          sha256=closure_sha, report=str(out/'REPORT.md')),ensure_ascii=False))


if __name__=='__main__':
    main()
