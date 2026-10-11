"""Read-only evidence audit and bounded layer13 plan; no UART/model/hardware."""
import json
from m351_workflow import ROOT, BASE, atomic, encoded, sha, sync


def main():
    board = json.loads((ROOT / 'deployment/mage_vl4b/BOARD_GATE_RESULT.json').read_bytes())
    evidence = {}
    for key in ('latest_m415_saved_feature_language_board',
                'latest_m415_saved_feature_language_closure',
                'latest_m414_layer12_visual_closure', 'latest_m406_vision_cost_closure'):
        row = board[key]
        assert sha(ROOT / row['result']) == row['sha256']
        assert all(row['sha256'] in (ROOT / name).read_text(encoding='utf-8-sig')
                   for name in ('CURRENT_STATE.md', 'docsMILESTONES.md'))
        evidence[key] = row
    prior = json.loads((ROOT / evidence['latest_m415_saved_feature_language_closure']['result']).read_bytes())
    assert prior['status'] == 'CLOSED_M415_ONE_INPUT_SAVED_FEATURE_DECISION_CONSISTENCY_PASS'
    assert prior['fixed_input_decision_consistency_pass'] and prior['original_reference_pass']
    assert prior['safe_buffers_released'] and prior['stable_overlay_reloaded']
    source = BASE / 'candidates/M407-vision-MLP-isolated-01/MLP_CHAINS.json'
    contract = json.loads(source.read_bytes())
    chains = [c for c in contract['chains'] if '.layers.13.mlp.' in c['module']]
    assert len(chains) == 2
    assert [c['descriptor_count'] for c in chains] == [2, 1]
    assert [c['groups'] for c in chains] == [16, 64]
    for row in contract['files']:
        assert (ROOT / row['path']).stat().st_size == row['bytes']
        assert sha(ROOT / row['path']) == row['sha256']
    costs = BASE / 'runs/M406-vision-cost-board-02/BOARD_RESULT.json'
    observed = json.loads(costs.read_bytes())
    assert sha(costs) == board['latest_m406_vision_cost_closure']['raw_sha256']
    gemm = [r for r in observed['costs']['rows']
            if r['category'] == 'linear_gemm' and '.layers.13.mlp.' in r['name']]
    assert len(gemm) == 2 and all(r['calls'] == 1 for r in gemm)
    plan = dict(
        status='PREPARED_M416_ONE_ADDITIONAL_LAYER_PLAN_ONLY', default_off=True,
        board_run=False, build_id='0x4D333537', stable_build_id='0x4D395832',
        evidence=evidence, prior_one_input_decisions=prior['logit_comparison'],
        original_chain_contract_sha256=sha(source), chains=chains,
        fixed_original_reference='Original A from unchanged frozen input, never previous candidate B',
        existing_selected_layers=[12], additional_layer=13,
        next_combination=[12, 13], verified_isolated_selected_layers=[12],
        production_visual_path_changed=False,
        reason='One adjacent FP32-state MLP with the same fc1/fc2 geometry; bounded accumulation experiment, not a claim that layer13 is fastest',
        representative_old_GEMM_seconds={r['name']: r['exclusive_ns'] / 1e9 for r in gemm},
        cost_scope='Existing M406 diagnostic only, not predicted PL or request gain',
        real_rows=392, native_batch_and_rows=[1,392], t32_rows=[32]*12+[8],
        later_isolated_DMA_payload_sizes=[max(c['stage_bytes_per_shard'] for c in chains)]*4+
            [max(c['input_bytes'] for c in chains)]+[max(c['output_bytes'] for c in chains)]*2,
        logical_calls_per_selected_MLP=26, logical_calls_combination=52,
        original_input='Same last source frame index3, two224 views; fixed weights and preprocessing',
        unchanged=['first two BF16 layers', 'Attention', 'GELU', 'normalization',
                   'Merger', 'language', 'prompt', 'output budget', 'retry math',
                   'RTL', 'production service', 'boot/DTB/CMA', 'stable rollback'],
        next_gate='Capture only layer13 original MLP tensors during one unchanged original visual forward; require existing complete original visual SHA and restoration',
        evidence_stages=[
            'Real original input capture, native [1,392,K] rank and original MLP bit-exact replay',
            'Local A8 QDQ rejection screen on original13 input; not PL arithmetic or task accuracy',
            'Complete same-input FTZ oracle, bias and GELU; full visual-chain output/FIFO/lifecycle check before combination',
            'Only12+13 complete visual features against original A; accumulated quality can differ from isolated13',
            'Reuse saved original/combination features in the same original language path and compare all logits, K/V and final decision',
            'Separate complete-request performance experiment only after numerical/decision and release evidence sync'],
        quality_scope='Current knife check is one-input consistency, no independent labeled accuracy; category/location need their own fixed prompts, original references and labels. Motion direction is not a sole criterion for a last-frame path.',
        quality_screen='Reuse fixed prior relativeL2/cosine/min-token screen without fitting; nonfinite, decision change, unsafe lifecycle or uncertain evidence stops expansion',
        capacity='Plan actual small seven-buffer sizes and seal new public DMA; no fixed64MiB CMA floor in isolated diagnosis. Preserve independently budgeted ordinary PS allocations and safe owner lifecycle.',
        additional_layers_executed=False, all24_allowed=False,
        accuracy_proven=False, performance_pass=False,
        next_concrete_step='Prepare an immutable PS-only layer13 capture component and actual producer/collector/source-closure checks; no all24 runner')
    out = BASE / 'runs/M416-bounded-layer13-plan-01/RESULT.json'
    atomic(out, encoded(plan), immutable=True)
    report = '''# M416 只增加一个 FP32 视觉层的计划

M415 原版精确参考及第12层候选固定刀具判定一致性通过后，下一候选限定为第13层两个 MLP Linear；计划组合为12+13，始终与固定原版A比较。尚未执行新增层，也没有组合准确率或性能结论。

第13层复用原W4四分片，fc1输入1024/输出4096、两descriptor，fc2输入4096/输出1024、一descriptor。392行仍12×32+8，每个MLP26逻辑事务；12+13共52次MLP逻辑事务，重试和合法最小事务另计。选择相邻层是有界累积误差实验，不声称它的收益最大。

先取得原第13层真实输入，保持原[1,392,K]接口与双重包装、FP32内部/BF16输出边界。原视觉完整SHA及局部重放必须通过，再做A8局部筛选和完整FTZ数值参考。组合中第13层输入受第12层改动影响，所以孤立第13层PASS不能替代组合特征和语言质量检查。

保留前两层BF16、Attention、GELU、归一化、Merger、语言、提示及单token输出预算。组合视觉特征只保存一次，后续语言质量复用保存特征；完整logits/KV/受限判定与固定原版比较。刀具样例只证明本输入一致性；类别/位置需要独立提示、参考和标签。末帧两视图不提供运动方向所需时序。

隔离诊断不恢复固定64MiB CMA门槛；按实际缓冲计划分配并封锁新增DMA，普通PS需求单独预算。任何数值、生命周期或证据失败停本级，不扩全部24层。完成组合质量与安全释放闭合后，才准备独立完整请求性能对照。

下一步仅准备PS捕获组件和配套检查。本文件为离线计划，无新板端事务。
'''
    atomic(out.with_name('REPORT.md'), report.encode('utf-8'), immutable=True)
    sync('latest_m416_bounded_expansion_plan',
         dict(status=plan['status'], result=out.relative_to(ROOT).as_posix(),
              sha256=sha(out), selected_layers=[12,13], board_run=False,
              accuracy_proven=False, performance_pass=False),
         f'## M416 单一新增FP32层计划（2026-10-06）\n\nSHA {sha(out)}；M415本输入原版精确参考和候选判定一致性闭合后，只计划第13层两个MLP及12+13组合，固定原版A不变。原W4/16及64 G64组/两与一descriptor/392行26逻辑合同和旧画像成本复核，未新增层执行/质量或性能。先PS真实13输入捕获与局部A8/FTZ，再组合视觉及保存特征语言质量，不扩24层、不改其余路径。')
    print('M416_PLAN_SYNC', sha(out))


if __name__ == '__main__':
    main()
