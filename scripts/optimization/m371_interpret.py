"""Close one saved candidate profile; no board access or new performance run."""
from collections import defaultdict
import json
import re

import m351_workflow as w
from m371_collect import decode
from m371_profile_summary import summarize

RUN = w.BASE / 'runs/M371-candidate-profile-board-01'
OUT = w.BASE / 'runs/M371-candidate-profile-closure-01'
RAW_SHA = 'bfed85a21ad8ef66414723c7dcb692f7af2605c1fca5649f874f835a8d3bc9eb'
PRIOR_SHA = '812c8aa7587d8bc12d57a1d0df891a9bf784d583121b9a3b00305673e13525f3'
SOURCE_ROOT = w.ROOT / 'release_staging/kv260-mage-vl-4b-prebuilt-install-20260926-v7'


def union(intervals):
    result = []
    for start, end in sorted(intervals):
        if not result or start > result[-1][1]:
            result.append([start, end])
        else:
            result[-1][1] = max(result[-1][1], end)
    return result


def intersection_ns(left, right):
    # Two disjoint, sorted unions; temporal overlap is not causal attribution.
    i = j = total = 0
    while i < len(left) and j < len(right):
        total += max(0, min(left[i][1], right[j][1]) - max(left[i][0], right[j][0]))
        if left[i][1] <= right[j][1]:
            i += 1
        else:
            j += 1
    return total


def main():
    assert w.sha(RUN / 'BOARD_RESULT.json') == RAW_SHA
    for name in ('CURRENT_STATE.md', 'docsMILESTONES.md', 'deployment/mage_vl4b/BOARD_GATE_RESULT.json'):
        assert RAW_SHA in (w.ROOT / name).read_text(encoding='utf-8-sig')
    log = (w.ROOT / 'tmp/m371/run.log').read_text(encoding='utf-8-sig')
    digest, raw, r = decode(log)
    assert digest == RAW_SHA and raw == (RUN / 'BOARD_RESULT.json').read_bytes()
    chunks = re.findall(r'M371_RESULT_CHUNK=(\d+)/(\d+):', log)
    assert len(chunks) == 984 and all(int(a) == i and int(b) == 984 for i, (a, b) in enumerate(chunks))
    assert 'M371_DONE case=B1 gate_rc=0 export_rc=0' in log
    report = json.loads((RUN / 'PREFILL_TRACE.json').read_text(encoding='utf-8'))
    s = summarize(report)
    assert s == r['candidate_prefill_profile']
    assert r['numerical_pass'] and r['safe_buffers_released'] and r['stable_overlay_reloaded']
    assert not r['worker_started'] and not r['formal_promotion_allowed']
    sample = r['samples'][0]
    assert sample['build_id'] == '0x4D333537'
    assert sample['counts']['logical_calls'] == 778 and sample['counts']['host_calls'] == 781
    assert r['fpga_transactions_total'] == 782 and r['original_buffer_release_count'] == 7
    e = s['main_exclusive_s']
    bins = dict(
        device_completion_wait=e['device_completion_wait'],
        weight_read_copy_sync_and_bookkeeping=sum(e[k] for k in (
            'weight_file_read', 'weight_cma_copy', 'weight_cache_sync',
            'file_read_copy_sync', 'weight_stage', 'weight_window_lookup')),
        explicit_ps_math=sum(e[k] for k in (
            'ps_silu', 'ps_causal_attention_grouped', 'ps_rms_norm', 'ps_apply_rope')))
    bins['other_main_work_or_wait_not_fully_attributed'] = s['prefill_s'] - sum(bins.values())
    assert abs(sum(e.values()) - s['prefill_s']) < 1e-9
    rows = report['trace']['events']
    root = next(x for x in rows if x['name'] == 'prefill_call')
    children = defaultdict(list)
    for row in rows:
        children[row['parent']].append(row)
    family_self = []
    for row in rows:
        if row['name'] != 'language_family':
            continue
        cursor = row['start_ns']
        for child in sorted(children[row['id']], key=lambda x: x['start_ns']):
            family_self.append((cursor, child['start_ns']))
            cursor = child['end_ns']
        family_self.append((cursor, row['end_ns']))
    worker_parse = union((x['start_ns'], x['end_ns']) for x in rows
                         if x['name'] == '_parse_into_and_check' and x['thread'] != root['thread'])
    parse_overlap = intersection_ns(union(family_self), worker_parse) / 1e9
    closure = json.loads((w.BASE / 'runs/M369-light-video-closure-01/RESULT.json').read_text(encoding='utf-8'))
    assert w.sha(w.BASE / 'runs/M369-light-video-closure-01/RESULT.json') == PRIOR_SHA
    original = r['original_full_profile_counters']
    sources = {}
    source_closure = json.loads((w.BASE / 'candidates/M371-candidate-prefill-profile-01/SOURCE_CLOSURE.json').read_text(encoding='utf-8'))
    for module in ('m238_prefill_runtime', 'm236_prefill_runtime'):
        relative = source_closure['modules'][module]
        sources[module] = dict(path=(SOURCE_ROOT / relative).relative_to(w.ROOT).as_posix(),
                               sha256=w.sha(SOURCE_ROOT / relative))
    value = dict(
        status='PASS_CANDIDATE_PROFILE_INTERPRETATION_NO_NEW_PERFORMANCE_CLAIM',
        build_id='0x4D333537', raw_sha256=RAW_SHA,
        trace_sha256=w.sha(RUN / 'PREFILL_TRACE.json'),
        summary_sha256=w.sha(RUN / 'PROFILE_SUMMARY.json'),
        run_log_sha256=w.sha(w.ROOT / 'tmp/m371/run.log'),
        result_chunks=984, gate_rc=0, export_rc=0, numerical_pass=True,
        performance_pass=False, formal_promotion_allowed=False,
        prefill_s=s['prefill_s'], main_exclusive_bins_s=bins,
        main_exclusive_bins_percent={k:100*v/s['prefill_s'] for k,v in bins.items()},
        main_thread_closure_error_ns=0,
        weight_file_read_s=e['weight_file_read'], weight_read_boundary_process_disk_bytes=s['process_read_boundary_io_delta']['read_bytes'],
        request_process_disk_bytes=sample['io_delta']['read_bytes'],
        original_weight_stage_bytes=sample['counts']['stage_bytes'],
        background_parse_s=s['background_exclusive_s_do_not_add']['_parse_into_and_check'],
        background_pack_s=s['background_exclusive_s_do_not_add']['_prepare_block'],
        main_recorded_pack_future_wait_s=original['pack_prefetch_wait_ms']/1000,
        family_self_overlap_with_worker_parse_s=parse_overlap,
        family_self_overlap_is_not_proven_future_wait=True,
        source_evidence=sources,
        dma_allocations=7, dma_payload_bytes=sum(x['bytes'] for x in r['allocated_buffers']),
        dma_release_count=7, extra_cma_allocations=0, weight_prefetch_enabled=False,
        loaded_capacity=r['loaded_capacity'], sampled_request_memory=sample['sampled_memory'],
        prior_net_benefit_sha256=PRIOR_SHA,
        prior_request_reduction_percent=closure['overall']['total_ms']['reduction_percent'],
        limitations=[
            'One instrumented candidate request, natural file cache; not cold-start or balanced performance.',
            '91.377s profile cannot quantitatively partition the earlier 65.571s light Prefill; different I/O and observation.',
            'Device completion waiting includes DMA/DDR/compute/output/backpressure/polling and concurrent CPU scheduling.',
            'Worker duration overlaps main wall time; temporal coincidence does not prove wait causality.',
            'language_family self includes future waits, allocation/checking/scheduling and observation; not pure PS math.',
            'Current seven-buffer reuse diagnostic does not authorize extra PS prefetch slot or production reserve adjustment.'],
        next_step='Re-evaluate existing M350/M351 PS-slot prefetch with separately justified sealed-DMA capacity/lifetime rules; do not automatically enable. If continuing attribution, separately observe parser/future tail before changing PL again.')
    w.atomic(OUT / 'RESULT.json', w.encoded(value), immutable=True)
    text = f'''# M371 候选版剩余耗时：上板诊断闭合

固定159-token候选0x4D333537诊断已完成，原gate/export均0；984个≤900B分块完整回收并核对SHA。778次逻辑、781次请求物理事务（3次语言重试），另加1次合法最小事务。视觉、输入、logits、72份K/V和最终判断均与原参考相同；七块原DMA缓冲各安全释放一次，稳定Overlay已恢复。没有启用PS权重预取，也没有改变核、输入策略、生产门槛或服务。

本次带观测Prefill **{s['prefill_s']:.6f}秒**；请求135.588430秒。此前M369轻量交错测试候选Prefill均值65.570745秒、完整请求均值109.534533秒及40.81%收益仍是独立性能证据。本次不能重新计算收益，也不能把这里的占比精确套到此前65.57秒。

| 本次主线程独占分类 | 秒 | Prefill占比 |
|---|---:|---:|
'''
    labels = ['设备完成等待（非纯PL计算）','权重读/复制/同步及相关 bookkeeping','已明确观测的PS数学（Attention/SiLU/RMS/RoPE）','其余主线程工作或等待（尚未完全归因）']
    for label, (key, seconds) in zip(labels, bins.items()):
        text += f'|{label}|{seconds:.6f}|{100*seconds/s["prefill_s"]:.2f}%|\n'
    text += f'''
主线程独占总和与Prefill墙钟严格闭合，误差0 ns。单独的权重文件读取为26.877673秒、复制1.121958秒、同步0.120390秒。读取span包围的进程`read_bytes`合计{value['weight_read_boundary_process_disk_bytes']/2**20:.3f} MiB；整个请求为{value['request_process_disk_bytes']/2**20:.3f} MiB，暂存API读取仍为2,034,890,752B。进程I/O不是每个文件的物理扇区证据，也不是强制冷缓存测试；本次确实含有磁盘读取。观测会增加开销，缓存与观测分别造成多少额外耗时尚未分离。

后台输出解析33.663709秒、激活pack5.356398秒，**不能再加到主线程91.38秒上**。原计数记录pack-future主线程等待{value['main_recorded_pack_future_wait_s']:.6f}秒。language_family主线程self15.070836秒包含输出future等待、缓冲复用、目标数组/检查及调度等；其中{parse_overlap:.6f}秒在时间上与后台解析重合，这仅是重合证据，不是已经证明的解析阻塞。冻结M238每family启动pack/parse线程，复用输出buffer前及family结束调用M236 `_resolve_pending`，后者先`pending.future.result()`；解析可能暴露在关键路径，仍需单独观察future等待才可精确裁决。

**结论：当前数据准备和设备等待量级相近，不能再把剩余时间视为主要PL计算。** 既有普通PS-slot权重预读值得重新评估，但本次尚不能证明在此前充分缓存的轻量请求中也能覆盖26.88秒。后台解析也有较大成本，应先查实际暴露等待，避免将全部33.66秒当作可节省延迟。

内存仍须单独论证：构造后CMA {r['loaded_capacity']['cma_free_bytes']/2**20:.6f} MiB；100ms采样请求期间最低CMA {sample['sampled_memory']['extrema']['min_cma']/2**20:.6f} MiB、最低MemAvailable {sample['sampled_memory']['extrema']['min_available']/2**30:.6f} GiB、最高RSS {sample['sampled_memory']['extrema']['max_rss']/2**20:.6f} MiB。这不是瞬时精确峰值。此次完成依赖七块DMA已分配并封锁新增申请的独立诊断规则，**不自动解锁额外PS slot、旧双bank或生产准入**。旧64MiB政策是否调整仍需根据新增需求和连续服务生命周期另行论证；不将统计余量下降认定为4GB耗尽或泄漏。

下一具体方向：在上述证据基础上，复用已有M350/M351普通PS-slot方案，先独立论证容量、对象和worker生命周期；不要自动启用预取、改RTL或切换稳定服务。若继续分段归因，优先补parser/future关键路径观测。

原始BOARD SHA：`{RAW_SHA}`。完整trace SHA：`{value['trace_sha256']}`。已有净收益证据SHA：`{PRIOR_SHA}`。本报告基于保存结果离线解读，没有重跑模型或硬件。
'''
    w.atomic(OUT / 'REPORT.md', text.encode('utf-8'), immutable=True)
    digest = w.sha(OUT / 'RESULT.json')
    w.sync('latest_m371_candidate_profile_closure', dict(status=value['status'], sha256=digest,
        result=(OUT / 'RESULT.json').relative_to(w.ROOT).as_posix(), raw_sha256=RAW_SHA,
        numerical_pass=True, performance_pass=False, formal_promotion_allowed=False),
        f'## M371 候选耗时诊断闭合（2026-10-03）\n\nBuild0x4D333537，一次原固定159视频，原rc0/export0，984块SHA完整，778逻辑/781物理+1最小，原视觉/logits/72KV数值通过、7缓冲释放并稳定恢复。画像Prefill91.377140s：主线程设备等待30.009027s（不是纯PL），权重读26.877673s/复制1.121958s/同步0.120390s，全部权重相关29.679278s，明确PS数学8.488920s；剩余self/调度/等待未完全归因，worker解析33.663709s不可相加。读取边界进程磁盘416.843750MiB，不能把本次占比精确套到旧轻量65.570745s或重算M36940.81%收益。运行时构造CMA32.617188MiB，100ms采样最小1.992188MiB，额外CMA0，PS预取未启用；不解锁额外slot/生产准入或服务。闭合SHA `{digest}`，原SHA `{RAW_SHA}`。下一步只据候选暴露成本独立论证现有PS-slot容量/lifetime，或分辨parser/future尾部；不自动改RTL/开预取/晋级。')
    print(json.dumps(dict(status=value['status'], sha256=digest, bins_s=bins,
                         family_parse_temporal_overlap_s=parse_overlap), ensure_ascii=False))


if __name__ == '__main__':
    main()
