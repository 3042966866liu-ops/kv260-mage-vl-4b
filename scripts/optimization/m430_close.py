"""Close exactly the saved complete-visual experiment; never execute a model."""
import json
import statistics
from m351_workflow import ROOT, BASE, atomic, encoded, sha, sync
from m430_workflow03 import check


def main():
    board = json.loads((ROOT / 'deployment/mage_vl4b/BOARD_GATE_RESULT.json').read_bytes())
    evidence = board['latest_m430_complete_visual_board']
    raw_path = ROOT / evidence['result']
    assert sha(raw_path) == evidence['sha256']
    assert all(evidence['sha256'] in (ROOT / n).read_text(encoding='utf-8-sig') for n in ('CURRENT_STATE.md', 'docsMILESTONES.md'))
    r = check(json.loads(raw_path.read_bytes()))
    complete = r['status'] == 'PASS_M430_COMPLETE_VISUAL_WARM_COLLECTED'
    decision = r.get('performance_adjudication') if complete else None
    passed = complete and decision['performance_pass']
    status = 'CLOSED_M430_WORTHWHILE_COMPLETE_VISUAL_GAIN' if passed else ('CLOSED_M430_NO_WORTHWHILE_RELIABLE_COMPLETE_VISUAL_GAIN' if complete else 'CLOSED_M430_VISUAL_EXPERIMENT_FAILURE')
    samples = r.get('warmup_samples', []) + r.get('formal_samples', [])
    rows = []
    for s in samples:
        rows.append(dict(index=s['index'], phase=s['phase'], phase_index=s['phase_index'], variant=s['variant'],
                         elapsed_ms=s['timing']['total_ms'], read_bytes=s['io_delta']['read_bytes'], major_fault_delta=s['major_fault_delta'],
                         physical_calls=s['physical_calls'], device_wait_ms=s['device_wait_ns']/1e6, staging_ms=s['staging_ns']/1e6,
                         before_memory=s['before_memory'], after_memory=s['after_memory'], feature_complete_exact=s['feature_complete_exact']))
    costs = {}
    for variant in ('A', 'B'):
        selected = [x for x in rows if x['phase'] == 'formal' and x['variant'] == variant]
        if selected:
            costs[variant] = {k: statistics.mean(x[k] for x in selected) for k in ('elapsed_ms', 'device_wait_ms', 'staging_ms')}
            costs[variant]['unpartitioned_ms'] = costs[variant]['elapsed_ms'] - costs[variant]['device_wait_ms'] - costs[variant]['staging_ms']
    memory = list(r.get('memory', []))
    for s in samples:
        memory.extend([s['before_memory'], s['after_memory']])
    next_step = ('Prepare a separately frozen full-request A/B correctness and warm-performance gate using this same late11 visual candidate and unchanged language path. No production promotion yet.' if passed else
                 'Close this performance variant without additional samples or automatic full-request expansion; preserve accepted numerical and fixed-task evidence.' if complete else
                 'Investigate only the recorded failure at this level; collection fixes may recover saved bytes only, never rerun to repair collection.')
    record = dict(status=status, raw_sha256=evidence['sha256'], gate_return_code=r['gate_return_code'], errors=r['errors'],
                  build_id=r.get('build_id'), selected_layers=r['selected_layers'], complete_fixed_experiment=complete,
                  performance_pass=passed, adjudication=decision, samples=rows, formal_mean_costs_ms=costs,
                  remaining_time_not_split_into_compute_and_PS=True,
                  visual_forward_calls=r.get('visual_forward_calls', 0), language_forward_calls=r['language_forward_calls'],
                  physical_transactions_started=r.get('physical_transactions_started', 0),
                  allocations=len(r.get('allocations', [])), releases=len(r.get('releases', [])),
                  safe_buffers_released=r.get('safe_buffers_released', False), stable_restored=r.get('stable_restored', False),
                  unsafe_dma_buffers_retained=r.get('unsafe_dma_buffers_retained', False),
                  checkpoint_min_CmaFree_bytes=min((x['CmaFree'] for x in memory if 'CmaFree' in x), default=None),
                  checkpoint_min_MemAvailable_bytes=min((x['MemAvailable'] for x in memory if 'MemAvailable' in x), default=None),
                  checkpoint_peak_RSS_bytes=max((x['VmRSS'] for x in memory if 'VmRSS' in x), default=None),
                  checkpoint_extrema_are_not_continuous_peaks=True,
                  numerical_source_sha256=r.get('numerical_source_sha256'), protocol_sha256=r.get('warm_protocol_sha256'),
                  full_request_gate_preparation_unlocked=passed, full_request_performance_proven=False,
                  production_promoted=False, temperature_measurement_enabled=False, additional_samples_allowed=False, next_step=next_step)
    out = BASE / 'runs/M430-complete-visual-warm-closure-01/RESULT.json'
    atomic(out, encoded(record), immutable=True)
    report = f'# M430 后11层视觉PL完整视觉暖态对照\n\n{status}。原raw SHA `{evidence["sha256"]}`，gate rc {r["gate_return_code"]}。\n\n'
    report += '固定末帧两视图、392行视觉输入。A为原CPU视觉，B仅13–23层的MLP fc1/fc2复用现有并行PL核0x4D333537。Attention/GELU/归一化和输入保持，0语言请求，不测温。预先冻结4次ABBA预热与8次ABBA+BAAB正式对照；不追加样本、不删异常样本、不改变阈值。\n\n'
    report += '计时包含完整视觉forward以及B绑定/退出、权重暂存、复制同步、PL等待和解析；完整feature比较和SHA在计时后。M429完整286批/24边界数值证据复用，不把逐wire哈希开销放入计时。\n\n'
    if rows:
        report += '| 次序 | 阶段 | 版本 | 完整视觉秒 | 读盘字节 | major faults | PL等待秒 | 暂存秒 |\n|---|---|---|---:|---:|---:|---:|---:|\n'
        report += ''.join(f'| {x["index"]} | {x["phase"]} | {x["variant"]} | {x["elapsed_ms"]/1000:.6f} | {x["read_bytes"]} | {x["major_fault_delta"]} | {x["device_wait_ms"]/1000:.6f} | {x["staging_ms"]/1000:.6f} |\n' for x in rows)
        report += '\n'
    if decision:
        report += f'正式A均值 {decision["A_mean_ms"]/1000:.6f}s，B均值 {decision["B_mean_ms"]/1000:.6f}s，完整视觉下降 {decision["gain_percent"]:.6f}%。\n\n'
        report += '| 组 | A均值秒 | B均值秒 | 下降百分比 | A组内范围秒 | B组内范围秒 |\n|---|---:|---:|---:|---:|---:|\n'
        report += ''.join(f'| {b["order"]} | {b["A_mean_ms"]/1000:.6f} | {b["B_mean_ms"]/1000:.6f} | {b["gain_percent"]:.6f} | {b["A_range_ms"]/1000:.6f} | {b["B_range_ms"]/1000:.6f} |\n' for b in decision['blocks'])
        report += f'\n四配对收益95%置信区间（秒）：{[x/1000 for x in decision["paired_95percent_CI_ms"]]}。双组正收益及CI下界>0：{decision["reliable_positive_gain"]}；预先冻结完整视觉至少5%收益要求：{decision["gain_percent"]>=5}；总性能裁决：{passed}。\n\n'
    report += '记录的平均成本（毫秒）：\n\n```json\n' + json.dumps(costs, ensure_ascii=False, indent=2) + '\n```\n\n'
    report += 'unpartitioned是完整计时减已记录PL等待及暂存的余项，含其余CPU算子、打包/解析、绑定退出等，不能称为纯计算或PS处理；未分项记录的成本注明未记录，不估算成可省时间。\n\n'
    report += f'原owner分配/释放 {record["allocations"]}/{record["releases"]}，安全释放 {record["safe_buffers_released"]}，稳定Overlay恢复 {record["stable_restored"]}。内存极值仅检查点，见RESULT，不是连续峰值。固定64MiB CMA floor未启用；实际分配计划/新增DMA封锁及普通PS内存预算保持。\n\n'
    if r['errors']:
        report += '原失败：\n\n```json\n' + json.dumps(r['errors'], ensure_ascii=False, indent=2) + '\n```\n\n'
    report += '本次仅完整视觉阶段，不代表完整请求收益或生产接入。原语言并行40.81%结论和已关闭两层性能分支保留；固定刀具判断一致性不是数据集准确率。\n\n下一步：' + next_step + '\n'
    atomic(out.with_name('REPORT.md'), report.encode('utf-8'), immutable=True)
    gain = decision['gain_percent'] if decision else None
    sync('latest_m430_complete_visual_closure', dict(status=status, result=out.relative_to(ROOT).as_posix(), sha256=sha(out), raw_sha256=evidence['sha256'], performance_pass=passed, full_request_gate_preparation_unlocked=passed, full_request_performance_proven=False),
         f'## M430 完整视觉暖态性能闭合（2026-10-06）\n\nSHA {sha(out)}，raw {evidence["sha256"]}；{status}，完整视觉下降百分比 {gain}。固定4预热+8正式，原裁决保留；分配/释放{record["allocations"]}/{record["releases"]}、稳定恢复{record["stable_restored"]}。0语言/温度/生产接入；不是完整请求收益。下一步：{next_step}')
    print('M430_VISUAL_CLOSURE_SYNC', sha(out), status)


if __name__ == '__main__':
    main()
