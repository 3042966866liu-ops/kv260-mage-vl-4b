"""Freeze complete-visual comparison only after late11 numerical closure."""
import json
from m351_workflow import ROOT,BASE,HERE,atomic,encoded,sha,sync
def main():
    board=json.loads((ROOT/'deployment/mage_vl4b/BOARD_GATE_RESULT.json').read_bytes())
    prerequisites={}
    for key in ('latest_m429_late11_visual_PL_board','latest_m429_late11_visual_numerical_closure','latest_m428_saved_language_closure','latest_m425_warm_closure'):
        e=board[key];assert sha(ROOT/e['result'])==e['sha256'];assert all(e['sha256'] in (ROOT/n).read_text(encoding='utf-8-sig') for n in ('CURRENT_STATE.md','docsMILESTONES.md'));prerequisites[key]=dict(e)
    if not board['latest_m429_late11_visual_numerical_closure']['hardware_visual_numerics_pass']:raise RuntimeError('Complete numerical/lifecycle closure required before timing')
    numeric=json.loads((ROOT/board['latest_m429_late11_visual_PL_board']['result']).read_bytes())
    from m429_workflow04 import check
    check(numeric)
    plan=dict(schema='m430-late11-complete-visual-warm-protocol-v1',build_id='0x4D333537',stable_rollback_build_id='0x4D395832',
        user_goal='Only accepted late11 visual MLP range: precision and worthwhile net complete visual benefit before complete-request expansion.',
        prerequisites=prerequisites,default_off=True,temperature_measurement_enabled=False,no_thermal_hwmon_IIO_cooling_reads=True,
        input=dict(last_frame_only=True,views=2,resolution=224,visual_rows=392,feature_shape=[98,2560],source_raw_sha256=numeric['baseline_source_sha256']),
        A='Original complete CPU visual path; all original24 layers, original exact bounded cache and thread policy.',
        B='Same visual path; only13..23 MLP fc1/fc2 use unchanged PLMLPBinding and existing parallel kernel. No prefetch/dualparser/SiLU/tail/Attention/GELU/norm/input changes.',
        language_forward_calls=0,real_model_visual_forward_calls=12,
        warmup_order='ABBA',formal_order='ABBABAAB',combined_order='ABBAABBABAAB',automatic_extra_samples_allowed=False,outlier_deletion_allowed=False,
        stop_on_first_failure=True,sequence_budget_seconds=1800,individual_visual_budget_seconds=180,
        primary_timing='time.perf_counter_ns immediately before entering candidate instance/hook scope, through original full visual forward and scope cleanup. A measures its unchanged forward. B includes staging, copy/sync, input packing, PL waiting, output parsing, bias, remaining CPU operators and scope overhead.',
        excluded_from_primary_timing=['Common asset/source SHA preflight','One common PS visual constructor','Candidate legal minimal transaction and planned DMA allocation','post-request complete visual feature serialization/full SHA/metrics','ordinary memory/io/environment before/after samples','collection and stable restore'],
        no_per_batch_full_wire_hash_or_boundary_array_materialization_in_timer=True,no_tensor_or_wire_payload_history=True,
        correct_each_sample_after_timer=dict(A_complete_feature_sha256=numeric['original_visual']['sha256'],B_complete_feature_sha256=numeric['candidate_visual']['sha256'],same_saved_wire_and_all24_boundary_evidence_reused=board['latest_m429_late11_visual_PL_board']['sha256'],no_language_recompute=True),
        resource_policy=dict(main_DMA_sizes=[557056]*4+[163856,524288,524288],main_DMA_bytes=3440656,main_DMA_sealed=True,zero_extra_DMA_during_sequence=True,original_owner_release_only=True,fixed_CMA_floor=None,ordinary_RSS_growth_limit_bytes=768<<20,ordinary_MemAvailable_reserve_bytes=64<<20,unsafe_DMA_retains_owner_process_buffers=True),
        physical_calls=dict(per_A=0,per_B=286,expected_B_visual_calls=6,expected_MLP_calls=1716,legal_minimal_and_stable_restore=2,expected_total=1718),
        warm_conditions=dict(first_A_populates_common_cache=True,cache_entries=26,cache_bytes=66699264,cache_misses=26,cache_within_budget=True,after_all_samples_cache_complete=True,first_two_warmup_before_cache_may_be_empty=True,warmup3_4_and_all_formal_read_bytes_max=1<<20,warmup3_4_and_all_formal_major_faults=0,paired_read_bytes_difference_max=1<<20,CPU_PL_clock_backend_config_matches=True,read_only_observation_no_eviction=True),
        adjudication=dict(reused_statistic_source_sha256=sha(HERE/'m425_warm.py'),formal_pairs=[[1,2],[4,3],[6,5],[7,8]],both_ABBA_BAAB_gains_positive=True,paired_95percent_CI_lower_ms_above=0,paired_df=3,paired_t_critical=3.182446305,worthwhile_complete_visual_gain_percent_minimum=5.,worthwhile_threshold_basis='Same existing isolated visual MLP decision minimum_gain=.05 in m411_mlp_binding.py; now assessed on complete visual forward, frozen before any sample.',threshold_source_sha256=sha(HERE/'m411_mlp_binding.py'),no_fitting_after_measurement=True),
        successful_claim_scope='Fixed-input controlled warm complete visual comparison only; fixed task consistency from M428, not labeled accuracy; no production promotion.',
        failure_branch='Preserve all warm/formal samples and failure rc; close variant if no worthwhile reliable net gain. No extra sampling or thread/layer sweep.',
        next_after_worthwhile_pass='Only then prepare unchanged-input complete-request correctness/latency comparison; no immediate service promotion.')
    folder=BASE/'runs/M430-complete-visual-warm-protocol-01';p=folder/'PROTOCOL.json';atomic(p,encoded(plan),immutable=True)
    r=dict(status='FROZEN_M430_ACCEPTED_LATE11_COMPLETE_VISUAL_WARM_PROTOCOL',protocol_sha256=sha(p),numerical_source_sha256=board['latest_m429_late11_visual_PL_board']['sha256'],source_sha256=sha(HERE/'m430_protocol.py'),board_run=False,performance_pass=False,temperature_measurement_enabled=False)
    out=folder/'RESULT.json';atomic(out,encoded(r),immutable=True)
    report='# M430 后11层完整视觉净耗时协议\n\n仅在M429完整PL数值及生命周期闭合后冻结。原CPU A与后11层PL B，原末帧两视图392行输入，同一运行时/缓存/线程/Overlay和七DMA。4次预热ABBA，8次正式ABBA+BAAB，合计固定12次视觉、0语言，不测温。\n\n主计时包含候选绑定、完整前向、权重暂存/复制同步/pack/设备等待/parse/bias和解绑；原特征与候选特征完整SHA在各请求计时后核对，不在计时内保存边界数组或逐batch wire哈希。原M429全部286wire/24边界证据复用。\n\n先确认原26项66699264B cache、读盘≤1MiB、major faults=0及相同时钟配置。两组都正收益、配对95%区间下界>0，而且完整视觉平均收益≥5%才值得保留；5%沿用原MLP候选阈值，预先冻结。条件/正确性/资源失败立即停止，不删除样本、不加测。\n\n只通过视觉净收益才准备完整请求对照，未接生产服务。协议SHA '+sha(p)+'。\n'
    atomic(folder/'REPORT.md',report.encode('utf-8'),immutable=True)
    sync('latest_m430_complete_visual_protocol',dict(result=out.relative_to(ROOT).as_posix(),sha256=sha(out),**r),f'## M430 后11层完整视觉暖态协议（2026-10-06）\n\nSHA {sha(out)}，协议 {sha(p)}；M429原数值/安全闭合后冻结。原CPU A/后11层PL B，4预热＋8正式固定ABBA/BAAB、0语言/测温，完整forward含全部候选开销，完整feature SHA计时后检查。缓存/读盘/时钟同条件，双组正收益、配对95%下界>0且完整视觉≥5%才保留；不加测/拟合阈值。尚未上板，不晋级服务。')
    print('M430_PROTOCOL_SYNC',sha(out),sha(p))
if __name__=='__main__':main()
