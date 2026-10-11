"""Freeze the next bounded warm experiment only after saved M423 closure."""
import json
from m351_workflow import ROOT, BASE, atomic, encoded, sha, sync


def main():
    b=json.loads((ROOT/'deployment/mage_vl4b/BOARD_GATE_RESULT.json').read_bytes())
    prerequisites={}
    for key in ('latest_m420_combination_board','latest_m421_saved_language_board',
                'latest_m423_integrated_board','latest_m423_integrated_closure'):
        e=b[key];p=ROOT/e['result']
        assert sha(p)==e['sha256']
        assert all(e['sha256'] in (ROOT/n).read_text(encoding='utf-8-sig')
                   for n in ('CURRENT_STATE.md','docsMILESTONES.md'))
        prerequisites[key]=dict(result=e['result'],sha256=e['sha256'],status=e['status'])
    assert b['latest_m423_integrated_board']['status']=='PASS_M423_INTEGRATED_VIDEO_NUMERICAL'
    assert b['latest_m423_integrated_closure']['numerical_pass'] is True
    old=b['latest_m404_environment_board'];p=ROOT/old['result']
    assert sha(p)==old['sha256']
    old_environment=json.loads(p.read_bytes())
    plan=dict(
        schema='m424-two-visual-MLP-warm-request-protocol-v1',
        prerequisites=prerequisites,scope='fixed159-two-view-original-versus-visual-MLP12+13',
        build_id='0x4D333537',stable_rollback_build='0x4D395832',
        changed_layers=[12,13],changed_parts=['mlp.fc1','mlp.fc2'],
        attention_GELU_norm_language_unchanged=True,parser_workers=1,
        PS_prefetch=False,last_layer_tail=False,SiLU_workspace=False,
        original_seven_DMA_payload_bytes=33484832,additional_DMA=0,
        runtime_resident_through_all_requests=True,
        same_overlay_legal_minimal_before_first_request=True,
        warmup_order='ABBA',formal_order='ABBABAAB',maximum_requests=12,
        no_additional_warmups_or_formal_samples=True,
        experiment_budget_s=1800,request_budget_s=180,
        measurement=dict(
            entry='original M276ShortPromptBinaryRuntime.stream(request)',
            primary='original complete.total_ms',secondary=['first_token_ms','preprocess_ms','vision_ms','prefill_ms','head_ms'],
            source_frames=4,selected_frame_indices=[3],views=2,prompt_tokens=159,generated_tokens=1,decode_calls=0,
            model_load_and_common_source_checks_outside_timer=True,
            B_binding_staging_pack_parse_cache_invalidation_close_inside_timer=True,
            no_full_tensor_packet_or_wire_hash_inside_timer=True,
            full_visual_logits_KV_hash_after_each_timer=True,
            per_request_language_expected_logical=778,
            per_request_language_expected_physical=781,
            candidate_visual_physical=52,candidate_visual_stage_bytes=8912896,
            language_and_visual_counters_separate=True),
        warm_conditions=dict(
            established_before_formal_by_fixed_warmups_3_and_4=True,
            warmup_1_and_2_io_recorded_without_warm_limit=True,
            read_bytes_max_per_warm_request=1048576,major_faults_max=0,
            paired_read_bytes_difference_max=1048576,
            original_visual_cache_entries=26,original_visual_cache_bytes=66699264,
            original_visual_cache_misses=26,
            identical_source_asset_storage_threads_CPU_policy_PL_clocks=True,
            observable_temperature_required=True,
            paired_entry_temperature_difference_max_mC=5000,
            observed_cooling_or_throttling_active_rejects=True,
            do_not_modify_cache_governor_clock_fan_or_kernel=True),
        missing_environment_evidence=dict(
            previous_result=old['result'],previous_sha256=old['sha256'],
            previous_status=old['status'],
            previous_issues=old_environment['environment']['observability_issues'],
            next='Reuse the prepared, never-run M404 read-only hwmon/IIO sensor catalogue. '
                 'Resolve actual sensor identity/units from authoritative driver evidence before formal measurement. '
                 'If temperature or required clock/cache evidence remains unproven, close this experiment as conditions not established.'),
        numerical=dict(A='bit exact saved original M421',B='bit exact saved layers12+13 M421',
                       visual_source='M420',logits_words=151936,KV_tensors=72,
                       per_request_count_retry_release_guard=True),
        statistics=dict(
            pairs=[[1,2],[4,3],[6,5],[7,8]],pair_definition='A total_ms minus B total_ms',
            block_gains=['ABBA meanA minus meanB','BAAB meanA minus meanB'],
            report_all_warmup_and_formal_samples=True,
            report_read_bytes_major_faults_memory_environment_for_each=True,
            report_total_vision_language_ms_and_group_spread=True,
            report_mean_median_relative_gain_and_paired_deltas=True,
            confidence_interval='two-sided 95% paired t interval on four deltas, df=3, critical=3.182446305',
            benefit_requires_both_blocks_positive_and_paired_lower_bound_positive=True,
            conditions_failure='WARM_CONDITIONS_NOT_ESTABLISHED',
            insufficient_benefit='NET_BENEFIT_NOT_RELIABLY_MEASURED_CLOSE_VARIANT',
            no_outlier_deletion_no_extra_runs_no_fitted_posthoc_threshold=True),
        production_changed=False,expanded_24_layers=False,
        performance_pass=False,board_run=False)
    folder=BASE/'runs/M424-warm-protocol-01'
    protocol=folder/'PROTOCOL.json';atomic(protocol,encoded(plan),immutable=True)
    report=('# M424 两层视觉MLP完整暖请求协议\n\n'
            'M423完整接入数值闭合后，冻结一次原版A/第12＋13层候选B的完整请求验证。'
            '原七DMA和完整runtime驻留；4次固定ABBA预热后，8次ABBABAAB正式测量，最多12次，'
            '不能删除首个样本、追加预热或增加次数直至通过。\n\n'
            '主指标为原M276 stream的complete.total_ms，另存视觉、语言及其他阶段。'
            '候选实例绑定、实际权重暂存、pack/parse、缓存失效和安全关闭都在原计时内；'
            '完整特征、logits、K/V哈希放在计时后。无PS预读、双parser、末层跳批或SiLU叠加。\n\n'
            '从第3、4次预热建立暖态：每请求读盘≤1MiB、major faults=0、原视觉缓存26项66699264B，'
            '线程/存储/CPU政策/PL时钟一致。温度必须可观测，相邻A/B入口差≤5℃，观测到降频或冷却动作则拒绝。'
            '旧M404缺thermal_zones，不能当作环境已通过；下一项复用已有未执行的小型只读传感器目录包，'
            '核实实际hwmon/IIO来源和单位，无法证明则闭合，不启动昂贵正式测试。\n\n'
            '固定四对配对差A−B，报告全部样本、ABBA和BAAB各收益、组内波动、读盘及阶段时间。'
            '净收益要求两组均为正、四对差值的双侧95%配对t区间下界为正（df=3）。'
            '未满足仅表示本协议未可靠测出收益，结束这次变体；旧性能裁决不改。\n\n'
            '这只是协议冻结，性能包尚未实现或上板；没有新加速结论、扩层或生产晋级。\n')
    atomic(folder/'REPORT.md',report.encode('utf-8'),immutable=True)
    result=dict(status='FROZEN_M424_WARM_PROTOCOL_PENDING_ENVIRONMENT_AND_IMPLEMENTATION',
                protocol_sha256=sha(protocol),prerequisites=prerequisites,
                source_sha256=sha(ROOT/'scripts/optimization/m424_protocol.py'),
                performance_pass=False,board_run=False,next_concrete_step=plan['missing_environment_evidence']['next'])
    out=folder/'RESULT.json';atomic(out,encoded(result),immutable=True)
    sync('latest_m424_warm_protocol',dict(status=result['status'],result=out.relative_to(ROOT).as_posix(),
         sha256=sha(out),protocol_sha256=sha(protocol),performance_pass=False,board_run=False),
         f'## M424 两层视觉MLP暖请求协议冻结（2026-10-06）\n\nSHA {sha(out)}，协议{sha(protocol)}；'
         'M423完整接入数值PASS后冻结4预热＋8正式ABBA/BAAB、原七DMA驻留、原complete计时及全数值计时后核对。'
         '两组正收益及四对95%区间下界为正才裁决；不删样本/不追加。旧M404温度不可观测仍未解锁环境，'
         '下一步仅复用未执行的只读sensor catalogue核实身份/单位，再实现轻量性能入口。未上板/性能/扩层/生产。')
    print('M424_PROTOCOL_SYNC',sha(out),sha(protocol))


if __name__=='__main__':main()
