"""Freeze a prospective natural-I/O comparison from closed saved evidence only."""
import copy
import json
from m351_workflow import ROOT, BASE, HERE, atomic, encoded, sha, sync


def main():
    board = json.loads((ROOT/'deployment/mage_vl4b/BOARD_GATE_RESULT.json').read_bytes())
    keys = ('latest_m432_integrated_board', 'latest_m432_integrated_closure',
            'latest_m430_complete_visual_closure', 'latest_m428_saved_language_board',
            'latest_m433_warm_closure', 'latest_m436_IO_board', 'latest_m436_IO_interpretation')
    prerequisites = {}
    for key in keys:
        entry = board[key]
        assert sha(ROOT/entry['result']) == entry['sha256']
        assert all(entry['sha256'] in (ROOT/n).read_text(encoding='utf-8-sig')
                   for n in ('CURRENT_STATE.md', 'docsMILESTONES.md'))
        prerequisites[key] = copy.deepcopy(entry)
    io = json.loads((ROOT/prerequisites['latest_m436_IO_interpretation']['result']).read_bytes())
    assert io['status'] == 'CLOSED_M436_TWO_REQUEST_IO_DIAGNOSTIC_PASS'
    assert io['verified_requests'] == 2 and io['second_request_language_head_storage_read_observed']
    assert io['source_sha256'] == prerequisites['latest_m436_IO_board']['sha256']
    assert io['lifecycle']['original_dma_allocations'] == io['lifecycle']['original_dma_releases'] == 7
    assert io['lifecycle']['safe_buffers_released'] and io['lifecycle']['stable_overlay_reloaded']
    original = board['latest_m433_complete_request_protocol']
    old_path = (ROOT/original['result']).with_name('PROTOCOL.json')
    assert sha(old_path) == original['protocol_sha256']
    plan = json.loads(old_path.read_bytes())
    plan.update(schema='m437-late11-natural-IO-complete-request-v1',
                prerequisites=prerequisites,
                scope='fixed159-two-view-original-versus-visual-MLP13-through23-with-natural-request-IO',
                supersedes_protocol_sha256=sha(old_path),
                previous_verdict_unchanged=prerequisites['latest_m433_warm_closure'],
                experiment_budget_s=3600, request_budget_s=240,
                measurement_question='Does B reduce complete request latency after fixed preconditioning when natural weight storage I/O remains included?')
    previous_conditions = plan.pop('warm_conditions')
    plan['preconditioning'] = dict(order='ABBA', requests=4, fixed_without_cache_qualification=True,
        retained_separately=True, additional_preconditioning_allowed=False,
        next_step_after_fixed_four='Proceed to exactly eight formal requests if numerical, environment and lifecycle checks hold, regardless of ordinary read_bytes.')
    plan['runtime_conditions'] = dict(
        identical_source_asset_storage_threads_CPU_policy_PL_clocks=True,
        same_original_runtime_and_seven_DMA=True, additional_DMA=0,
        no_cache_eviction_or_forced_weight_preload=True,
        no_drop_caches_fadvise_governor_clock_fan_or_kernel_changes=True,
        temperature_measurement_enabled=False, no_thermal_hwmon_IIO_cooling_reads=True,
        decoded_cache_entry_upper_bound=26, decoded_cache_byte_upper_bound=66699264,
        decoded_cache_within_budget_required=True,
        equal_cache_entries_or_misses_between_variants_required=False,
        read_bytes_max_per_request=None, paired_read_bytes_difference_max=None,
        major_faults_max=None, natural_read_bytes_and_faults_are_observations_not_exclusion_rules=True,
        observed_CPU_frequency_and_original_environment_check_required=True,
        storage_identity_and_source_SHA_required=True,
        unexpected_environment_numerical_or_lifecycle_failure_invalidates_experiment=True)
    plan['measurement'].update(
        natural_storage_IO_included_in_primary_timer=True,
        heavy_file_window_observer_enabled=False, mincore_observer_enabled=False,
        process_IO_and_faults_before_after_request_only=True,
        foreground_weight_staging_and_B_CPU_PL_scope_inside_original_timer=True,
        interval_hashing_may_affect_next_request_cache=True,
        interval_policy='Same fixed post-timer full numerical check after every A and B; report this protocol boundary and do not infer unattended service steady state.')
    plan['statistics'].update(
        conditions_failure='EXPERIMENT_CONDITIONS_NOT_ESTABLISHED',
        IO_difference_reported_without_sample_rejection=True,
        no_regression_adjustment_or_posthoc_IO_matching=True,
        estimand='Total effect of selected implementation under this fixed resident-runtime protocol, including its natural I/O and cache effects.',
        single_bounded_experiment_only=True,
        inconclusive_or_nonpositive_gain='NET_BENEFIT_NOT_RELIABLY_MEASURED_CLOSE_THIS_EXPERIMENT')
    plan['removed_previous_conditions'] = dict(
        read_bytes_max_per_warm_request=previous_conditions['read_bytes_max_per_warm_request'],
        paired_read_bytes_difference_max=previous_conditions['paired_read_bytes_difference_max'],
        reason='M436 second request still incurred storage I/O; a full-cache qualification would test an unestablished operating condition.')
    assert plan['warmup_order'] == 'ABBA' and plan['formal_order'] == 'ABBABAAB' and plan['maximum_requests'] == 12
    assert plan['additional_DMA'] == 0 and plan['temperature_measurement_enabled'] is False
    assert plan['statistics']['benefit_requires_both_blocks_positive_and_paired_lower_bound_positive']
    folder = BASE/'runs/M437-natural-IO-protocol-01'
    protocol = folder/'PROTOCOL.json'
    atomic(protocol, encoded(plan), immutable=True)
    record = dict(status='FROZEN_M437_NATURAL_IO_COMPLETE_REQUEST_PROTOCOL_ONLY',
        protocol_sha256=sha(protocol), source_sha256=sha(HERE/'m437_protocol.py'),
        prerequisites=prerequisites, board_run=False, performance_pass=False,
        old_verdict_changed=False, temperature_measurement_enabled=False,
        numerical_and_resource_logic_unchanged=True, requires_new_packet_and_actual_control_collector_support=True)
    out = folder/'RESULT.json'
    atomic(out, encoded(record), immutable=True)
    report = '''# M437 包含自然读盘的固定完整请求对照协议

问题：固定预处理之后，在正常权重读盘仍发生的条件下，视觉 MLP 第13–23层 PL 候选是否让完整请求更快？本文件仅冻结协议，尚未制作或执行性能包。

- A 为原视觉路径；B 仅替换现有后11层的两个 MLP Linear。两版使用 Build 0x4D333537，固定末帧两视图、159-token提示词、权重、单token输出和语言路径相同。现有七DMA驻留，禁止新增DMA；不改预读、解析线程、GELU、归一化等实现。
- 同一运行时固定4次 ABBA 预处理，再固定8次 ABBA＋BAAB 正式请求。所有预处理和正式样本保留，不因读盘、major faults或耗时而删样本。没有额外预热、加测、清缓存或预读全部权重。
- 不再要求每请求 read_bytes≤1MiB 或两版读盘量相同。记录实际 I/O、缓存状态、内存和环境；I/O差异计入真实总成本。缓存只核对原有容量上限，不能强求候选与原版条目数相同。
- 主指标使用原 stream 的 complete.total_ms；候选权重暂存、打包、PL、解析及关闭均在原计时内。视觉、Prefill、LM head等阶段照原边界报告；LM head包含在Prefill时不重复相加。
- 关闭 M436 逐文件窗口/mincore观察器，只保留轻量前后统计。完整视觉、logits和72KV核对仍在计时外，双方采用相同检查与请求间策略；这可能影响后续缓存，结论仅适用于明确写出的测试协议，不能直接当作长期服务证据。
- 保留每请求778逻辑/781语言物理事务、B的286视觉物理事务及22次46.75MiB暂存核对。12次请求加合法minimal共预期11089物理事务；正确性、资源、环境错误立即停止扩大测试，活动资源由原owner保留或安全退出。
- 两个正式组平均收益均>0，且四个预定A−B配对差的95%区间下界>0，才记为本协议下可靠收益；不可靠或非正收益则结束本次实验，不追加样本。报告全部耗时、配对差、组内波动和I/O，不做事后回归修正。
- 全局预算3600s、单请求预算240s用于有界退出观察；不是强杀超时许可。固定终点后安全释放七DMA、恢复稳定Overlay。不测温、不改生产入口，不更改M433旧裁决。

下一步只准备新版本性能包及实际原stream、cache边界、export/collector/控制/组装故障检查；这些通过并同步后才可上板。详细条件与SHA见PROTOCOL.json和RESULT.json。
'''
    atomic(folder/'REPORT.md', report.encode('utf-8'), immutable=True)
    note = f'## M437 自然I/O完整请求协议冻结（2026-10-07）\n\nSHA {sha(out)}，协议 {sha(protocol)}。M436两次驻留请求仍有语言/head读盘，故新协议固定4次ABBA预处理＋8次ABBABAAB正式、全样本保留并包含自然I/O，取消1MiB/配对I/O差/majorfault准入但保持数值、环境、缓存上限、七DMA/0新增和安全owner退出。原stream总时间为主，双组正收益与预定配对95%下界>0判据不变；不测温、不加测、不改M433原裁决或生产。只有协议，尚未新包/上板/性能结论；下一步实际包与控制收集故障支持。'
    sync('latest_m437_natural_IO_protocol', dict(result=out.relative_to(ROOT).as_posix(), sha256=sha(out), **record), note)
    print('M437_PROTOCOL_SYNC', sha(out), sha(protocol))


if __name__ == '__main__':
    main()
