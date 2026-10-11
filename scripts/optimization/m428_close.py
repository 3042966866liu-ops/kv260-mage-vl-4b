"""Interpret collected saved-feature language quality; no board operations."""
import json
from m351_workflow import ROOT, BASE, atomic, encoded, sha, sync
from m428_workflow import check, PKG


def main():
    board = json.loads((ROOT / 'deployment/mage_vl4b/BOARD_GATE_RESULT.json').read_bytes())
    e = board['latest_m428_saved_language_board']; path = ROOT / e['result']
    assert sha(path) == e['sha256'] and all(e['sha256'] in (ROOT / n).read_text(encoding='utf-8-sig') for n in ('CURRENT_STATE.md', 'docsMILESTONES.md'))
    r = check(json.loads(path.read_bytes())); plan = json.loads((PKG / 'PLAN.json').read_bytes())
    passed = r['status'] == 'PASS_M428_SAVED_FEATURE_DECISION_CONSISTENCY'
    status = 'CLOSED_M428_LATE11_ONE_INPUT_DECISION_CONSISTENCY_PASS' if passed else 'CLOSED_M428_SAVED_FEATURE_LANGUAGE_FAILURE'
    next_step = ('Prepare only the accepted late11 complete visual PL numerical gate against its saved exact software reference. '
                 'After complete feature/wire equality and safe lifecycle, compare full visual net elapsed time with fixed balanced warm samples. '
                 'Full-request performance remains locked until worthwhile visual gain.' if passed else
                 'Debug only the saved-feature task failure; no visual/PL/performance expansion or model replay to recover evidence.')
    rows = [dict(variant=s['variant'], logical_calls=s['counts']['logical_calls'],
                 physical_calls=s['counts']['host_calls'], language_retries=s['counts']['language_retries'],
                 head_retries=s['counts']['head_retries'], decision=s['decision'], logits=s['logits'])
            for s in r.get('samples', [])]
    record = dict(status=status, raw_sha256=e['sha256'], gate_return_code=r['gate_return_code'], errors=r['errors'],
                  build_id=r['build_id'], selected_layers=plan['selected_layers'], saved_feature_source_sha256=plan['M427_raw_sha256'],
                  original_reference_pass=r.get('original_reference_pass', False), fixed_input_decision_consistency_pass=passed,
                  visual_forward_calls=r.get('vision_forward_calls', 0), language_forward_calls=r['model_forward_calls'],
                  prompt_tokens=len(r.get('prompt_token_ids', [])), output_budget=r.get('output_budget'), decode_calls=r.get('decode_calls', 0),
                  logit_comparison=r.get('logit_comparison'), per_variant=rows, retained_board_logits=r.get('logit_files', []),
                  physical_transactions=r['fpga_transactions'], original_DMA_bytes=sum(x['bytes'] for x in r['allocated_buffers']),
                  allocations=len(r['allocated_buffers']), releases=len(r['released_buffers']),
                  safe_buffers_released=r.get('safe_buffers_released', False), unsafe_buffers_retained=r['unsafe_buffers_retained'],
                  stable_overlay_reloaded=r.get('stable_overlay_reloaded', False),
                  hardware_visual_numeric_gate_unlocked=passed, hardware_visual_timing_unlocked=False,
                  dataset_accuracy_proven=False, category_location_or_motion_quality_proven=False,
                  performance_pass=False, production_promoted=False, temperature_measurement_enabled=False,
                  inherited_phase_label='saved-feature-language-original-then-layers12-13',
                  phase_label_not_selection_authority=True,
                  next_step=next_step)
    out = BASE / 'runs/M428-saved-language-closure-01/RESULT.json'
    atomic(out, encoded(record), immutable=True)
    report = f'# M428 后11层保存视觉特征的语言任务闭合\n\n{status}。原raw SHA `{e["sha256"]}`，rc {r["gate_return_code"]}。\n\n'
    report += '只复用M426保存原版和M427软件候选的两份98×2560特征；末帧两视图、159-token提示、权重、原语言与LM head、单token输出保持，视觉前向0次。不测温。\n\n'
    report += '一处phase描述沿用旧layers12-13文字；实际选层以冻结PLAN、已验SHA的M427来源和saved_feature_identities为准，均为13–23。该日志描述不参与数学或选层，原日志保留，不为改标签重跑。\n\n'
    q = record['logit_comparison']
    if q:
        report += '| 项目 | 原版 | 后11层候选 |\n|---|---:|---:|\n'
        for label, key in [('判定', 'verdict'), ('token', 'token_id'), ('刀具分数（未校准）', 'knife_score'), ('yes−no logit', 'logit_margin_yes_minus_no')]:
            report += f'| {label} | {q["original"][key]} | {q["candidate"][key]} |\n'
        report += '\n完整151936项logits的距离：\n\n```json\n'+json.dumps(
            {k: q[k] for k in ('full_logits_bit_equal', 'changed_FP32_words', 'relative_l2', 'cosine', 'RMSE', 'max_abs', 'knife_score_delta')},
            ensure_ascii=False, indent=2)+'\n```\n\n'
    report += '| 变体 | 逻辑调用 | 物理调用 | 语言重试 | head重试 |\n|---|---:|---:|---:|---:|\n'
    for row in rows:
        report += f'| {row["variant"]} | {row["logical_calls"]} | {row["physical_calls"]} | {row["language_retries"]} | {row["head_retries"]} |\n'
    report += f'\n原版完整logits、72份K/V、154family及事务/重试与冻结参考逐位相同：{record["original_reference_pass"]}。候选要求全输出有限且固定输入受限判断一致，记录logit距离而不拟合阈值。\n\n'
    report += f'七块原DMA {record["original_DMA_bytes"]}B，分配/释放 {record["allocations"]}/{record["releases"]}，安全释放 {record["safe_buffers_released"]}，稳定Overlay恢复 {record["stable_overlay_reloaded"]}，总物理事务 {record["physical_transactions"]}。无新增DMA或PS预读slot，独立诊断不使用固定64MiB CMA floor，普通PS预算/64MiB MemAvailable余量保留。初始或恢复DMASR0不是已完成DMA事务证据。\n\n'
    report += '结论仅覆盖单份固定刀具输入，不是独立标注准确率或类别、位置、运动质量证明。本轮PL只执行原语言路径，没有执行后11层视觉PL候选，诊断时间不能视为视觉/完整请求提速。M425两层性能关闭、M426全22层拒绝和此前语言并行40.81%结论各自保留。\n\n'
    if r['errors']:
        report += '原失败：\n\n```json\n'+json.dumps(r['errors'], ensure_ascii=False, indent=2)+'\n```\n\n'
    report += '下一步：'+next_step+'\n'
    atomic(out.with_name('REPORT.md'), report.encode('utf-8'), immutable=True)
    sync('latest_m428_saved_language_closure', dict(status=status, result=out.relative_to(ROOT).as_posix(), sha256=sha(out), raw_sha256=e['sha256'],
         decision_consistency_pass=passed, hardware_visual_numeric_gate_unlocked=passed, hardware_visual_timing_unlocked=False,
         performance_pass=False, production_promoted=False),
         f'## M428 后11层保存特征任务质量闭合（2026-10-06）\n\nSHA {sha(out)}；raw {e["sha256"]}保留，{status}。0视觉重算，原完整参考{record["original_reference_pass"]}，固定输入判断一致{passed}，七DMA分配/释放{record["allocations"]}/{record["releases"]}，稳定恢复{record["stable_overlay_reloaded"]}。不测温；非独立准确率或性能。通过仅解锁后11层完整视觉PL数值，数值和净视觉耗时通过后才完整请求。下一步：{next_step}')
    print('M428_CLOSURE_SYNC', sha(out), status)


if __name__ == '__main__':
    main()
