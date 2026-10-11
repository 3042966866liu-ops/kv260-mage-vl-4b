"""Interpret the immutable, completed two-half screen. No board operations."""
import json
import math
from m351_workflow import ROOT, BASE, atomic, encoded, sha, sync
from m427_workflow02 import check


def main():
    recovery = {n: dict(sha256=sha(ROOT / n), full_read=True,
                       characters=len((ROOT / n).read_text(encoding='utf-8-sig')))
                for n in ('CURRENT_STATE.md', 'DEPLOYMENT_OPERATION_MISTAKES_REVIEW.md',
                          'docsMILESTONES.md', 'deployment/mage_vl4b/BOARD_GATE_RESULT.json')}
    board = json.loads((ROOT / 'deployment/mage_vl4b/BOARD_GATE_RESULT.json').read_bytes())
    e = board['latest_m427_half_software_board']
    path = ROOT / e['result']
    assert sha(path) == e['sha256']
    assert all(e['sha256'] in (ROOT / n).read_text(encoding='utf-8-sig')
               for n in ('CURRENT_STATE.md', 'docsMILESTONES.md'))
    r = check(json.loads(path.read_bytes()))
    done = r.get('software_screen_completed') is True
    rows = []
    for row in r['ranges']:
        q = row['full_visual_quality']
        failed = []
        for metric, threshold, maximum in (
            ('relative_l2', 'maximum_relative_l2', True),
            ('cosine', 'minimum_cosine', False),
            ('min_token_cosine', 'minimum_token_cosine', False),
        ):
            value = q['metrics'][metric]
            limit = q['thresholds'][threshold]
            assert math.isfinite(value)
            if value > limit if maximum else value < limit:
                failed.append(dict(metric=metric, value=value,
                                   operator='<=' if maximum else '>=', threshold=limit))
        assert row['feature_screen_pass'] == (not failed)
        rows.append(dict(name=row['name'], selected_layers=row['selected_layers'],
                         quality=q, failed_criteria=failed,
                         logical_reference_calls=row['logical_reference_calls'],
                         physical_reference_attempts=row['physical_reference_attempts'],
                         saved_feature=row['saved_feature'],
                         candidate_visual=row['candidate_visual'],
                         boundary_metrics=row['boundary_comparison']))
    passes = r['feature_pass_ranges']
    if not done:
        status = 'FAILED_SOFTWARE_DIAGNOSTIC_SAME_LEVEL_ONLY'
        next_step = '只排查本次软件入口失败，保留原结果；不扩大范围或进入硬件。'
    elif passes:
        status = 'HALF_FEATURE_PASS_SAVED_FEATURE_TASK_REQUIRED'
        next_step = '仅对已通过范围复用保存的原版/候选视觉特征，接相同原语言路径核对完整输出及固定任务判断；不重复视觉。任务通过后才准备该范围完整视觉PL数值与净耗时。'
    else:
        status = 'BOTH_HALF_FEATURE_REJECT_LOCALIZATION_PROTOCOL_REQUIRED'
        next_step = '两个预定半区实验结束；先根据各自累计边界冻结一次更小范围定位协议，保持原版参考及阈值。不自动追加候选，不进入任务或硬件性能。'
    checkpoints = [x for x in [r.get('memory_before_constructor'), r.get('memory_after_constructor')]
                   + r.get('memory', []) + [r.get('memory_after_cleanup')] if isinstance(x, dict)]
    observed = (dict(minimum_MemAvailable_bytes=min(x['MemAvailable'] for x in checkpoints),
                     peak_checkpoint_RSS_bytes=max(x['VmRSS'] for x in checkpoints),
                     minimum_CmaFree_bytes=min(x['CmaFree'] for x in checkpoints))
                if checkpoints else None)
    record = dict(status=status, recovery=recovery,
                  raw_sha256=e['sha256'], manifest_sha256=r['manifest_sha256'],
                  software_screen_completed=done, feature_pass_ranges=passes,
                  ranges=rows, original_visual_forward_calls=r.get('original_visual_forward_calls'),
                  visual_forward_calls=r.get('visual_forward_calls'),
                  original_reference_pass=r.get('original_reference_pass'),
                  observed_checkpoint_memory=observed,
                  PS_owner_closed=r['visual_owner_closed'], bindings_restored=r['bindings_restored'],
                  task_screen_recorded=False, task_screen_pass=False,
                  hardware_visual_timing_unlocked=False, performance_pass=False,
                  production_promoted=False, temperature_measurement_enabled=False,
                  quality_scope='One fixed last-frame two-view feature screen; no task or labeled accuracy evidence.',
                  next_step=next_step)
    out = BASE / 'runs/M427-half-software-closure-01/RESULT.json'
    atomic(out, encoded(record), immutable=True)
    report = '# M427 两个11层范围的软件质量闭合\n\n'
    report += f'裁决：**{status}**。原始结果 SHA `{e["sha256"]}`。\n\n'
    report += '两个范围均与同一份保存原版比较，原版视觉未重算。仅MLP两个Linear使用精确A8/FP16/FTZ软件参考；Attention、GELU、归一化、原BF16前缀、语言、输入及线程策略保持。0Overlay/DMA/PL/语言前向，不测温。\n\n'
    report += '| 范围（零基层号） | 相对L2（≤0.02） | 余弦（≥0.999） | 最差token余弦（≥0.995） | 判据 | 逻辑/物理参考尝试 |\n|---|---:|---:|---:|---|---:|\n'
    for row in rows:
        m = row['quality']['metrics']
        report += f'| {row["name"]} | {m["relative_l2"]:.9f} | {m["cosine"]:.9f} | {m["min_token_cosine"]:.9f} | {"通过" if not row["failed_criteria"] else "拒绝"} | {row["logical_reference_calls"]}/{row["physical_reference_attempts"]} |\n'
    report += '\n具体未通过项：\n\n```json\n' + json.dumps(
        [dict(name=x['name'], failed_criteria=x['failed_criteria']) for x in rows],
        ensure_ascii=False, indent=2) + '\n```\n\n'
    report += '每层数据是累计候选输出与固定原版同层输出的比较，不能直接把相邻变化当作该层局部敏感性。软件参考耗时含精确模拟及检查，不能用作PL性能或净提速。\n\n'
    report += f'PS owner关闭：{r["visual_owner_closed"]}；钩子恢复：{r["bindings_restored"]}。观察到的检查点内存并非连续真实峰值：\n\n```json\n' + json.dumps(observed, indent=2) + '\n```\n\n'
    report += 'M426全22层拒绝与M425两层性能关闭裁决保留；此前语言并行核40.81%完整请求性能结论独立保持。\n\n下一步：' + next_step + '\n'
    atomic(out.with_name('REPORT.md'), report.encode('utf-8'), immutable=True)
    digest = sha(out)
    sync('latest_m427_half_closure', dict(status=status, result=out.relative_to(ROOT).as_posix(),
         sha256=digest, raw_sha256=e['sha256'], feature_pass_ranges=passes,
         task_screen_pass=False, hardware_visual_timing_unlocked=False, performance_pass=False),
         f'## M427 两个11层范围软件质量闭合（2026-10-06）\n\nSHA {digest}；原SHA {e["sha256"]}，{status}，feature通过范围{passes}。同原版保存特征、未重复原版视觉，原阈值不改；PS owner关闭{r["visual_owner_closed"]}，钩子恢复{r["bindings_restored"]}。任务/PL/性能未通过，原两层性能关闭与全22层拒绝保留。下一步：{next_step}')
    print('M427_CLOSURE_SYNC', digest, status)


if __name__ == '__main__':
    main()
