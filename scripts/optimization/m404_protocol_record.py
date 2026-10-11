"""Freeze a protocol only; no serial, model, hardware or measurement execution."""
import json
from m351_workflow import ROOT, BASE, HERE, sha, atomic, encoded, sync


def main():
    names = ('CURRENT_STATE.md', 'DEPLOYMENT_OPERATION_MISTAKES_REVIEW.md',
             'docsMILESTONES.md', 'deployment/mage_vl4b/BOARD_GATE_RESULT.json')
    recovery = {}
    for name in names:
        path = ROOT / name
        content = path.read_text(encoding='utf-8-sig')
        recovery[name] = dict(sha256=sha(path), bytes=path.stat().st_size,
                              lines=len(content.splitlines()))
    board = json.loads((ROOT / names[-1]).read_text(encoding='utf-8-sig'))
    expected = {
        'latest_m403_tail_performance_board': 'f83ba109292b171d94908632a2f69c8d74c1d075b301f66b259629433c4cb321',
        'latest_m403_tail_performance_closure': '079a8eaa43bd17c1fff2c1602e83baa2393bf2469255a21b256e514966bfe685',
        'latest_m402_tail_video_closure': '8fbfa263498dde618ee6c93f94f6ce726cb37d6da6eb5309bb6d3b848231d732',
    }
    for key, digest in expected.items():
        entry = board[key]
        assert entry['sha256'] == digest == sha(ROOT / entry['result'])
        assert all(digest in (ROOT / n).read_text(encoding='utf-8-sig')
                   for n in names[:1] + names[2:3])
    source = BASE / 'candidates/M403-tail-performance-01'
    manifest = json.loads((source / 'PACKAGE_MANIFEST.json').read_bytes())
    assert sha(source / 'PACKAGE_MANIFEST.json') == 'a1bfd96e1324fd86f89f574504c280dd64028f4ef2b54155cbcbd0a00377f1a8'
    for row in manifest['files']:
        path = source / row['path']
        assert path.stat().st_size == row['bytes'] and sha(path) == row['sha256']
    protocol = BASE / 'M404_WARM_REQUEST_PROTOCOL_2026-10-04.md'
    text = protocol.read_text(encoding='utf-8')
    assert all(s in text for s in ('未上板', 'A、B、B、A', '1,048,576B', '9300',
                                  'WARM_CONDITIONS_NOT_ESTABLISHED',
                                  'WARM_BENEFIT_NOT_RELIABLY_RESOLVED'))
    plan = dict(
        protocol_version='M404-warm-fixed159-v1', build_id='0x4D333537',
        warmup_order='ABBA', measured_order='ABBABAAB',
        formal_pair_indices_A_B=[[1, 2], [4, 3], [6, 5], [7, 8]],
        warmup_admission_indices=[3, 4], request_count_maximum=12,
        expected_model_physical_total=9288, expected_all_physical_total=9300,
        expected_logical_total=9264, expected_language_forwards=12,
        expected_vision_forwards=13, original_parser_workers=1,
        extra_DMA_allocations=0, PS_prefetch=False, SiLU_workspace=False,
        io_read_limit_bytes=1048576, paired_read_difference_limit_bytes=1048576,
        major_fault_increment_limit=0, vision_cache_entries=26,
        vision_cache_bytes=66699264, vision_cache_misses=26,
        adjacent_entry_temperature_difference_limit_C=5,
        request_budget_s=180, sequence_budget_s=1800,
        kill_on_timeout=False, extra_warmups=False, replacement_samples=False,
        posthoc_exclusions=False, thresholds_adapted_after_data=False,
        per_pair_total_saved_min_ms=500, per_pair_prefill_saved_min_ms=500,
        per_pair_absolute_vision_difference_max_ms=500,
        per_pair_total_minus_vision_saved_min_ms=500,
        general_population_confidence_claim=False,
        production64MiB_guard_changed=False, service_changed=False,
        formal_promotion_allowed=False,
    )
    order = plan['measured_order']
    assert sorted(i for pair in plan['formal_pair_indices_A_B'] for i in pair) == list(range(1, 9))
    assert all(order[a-1] == 'A' and order[b-1] == 'B'
               for a, b in plan['formal_pair_indices_A_B'])
    assert plan['expected_model_physical_total'] == 6 * (781 + 767)
    assert plan['expected_all_physical_total'] == plan['expected_model_physical_total'] + 12
    value = dict(status='PREPARED_CONTROLLED_WARM_PROTOCOL_ONLY',
                 protocol_path=protocol.relative_to(ROOT).as_posix(),
                 protocol_sha256=sha(protocol), recorder_sha256=sha(HERE / 'm404_protocol_record.py'),
                 recovery=recovery, prior_evidence=expected,
                 frozen_source_sha256={n: sha(source / n) for n in (
                     'm403_trials.py', 'm403_timed_count_scope.py',
                     'm401_prefill_tail_scope.py', 'm402_video_contract.py')},
                 plan=plan, board_run=False, new_package_created=False,
                 performance_pass=False, old_M403_verdict_unchanged=True)
    out = BASE / 'runs/M404-warm-protocol-preparation-01/RESULT.json'
    atomic(out, encoded(value), immutable=True)
    digest = sha(out)
    sync('latest_m404_warm_protocol', dict(
        status=value['status'], result=out.relative_to(ROOT).as_posix(), sha256=digest,
        protocol_sha256=value['protocol_sha256'], board_run=False, performance_pass=False),
        '## M404 受控暖请求协议准备（2026-10-04）\n\n'
        f'证据SHA {digest}；协议SHA {value["protocol_sha256"]}。Build0x4D333537，'
        '固定完整预热ABBA4次、正式ABBABAAB8次，1MiB实际读盘/零major fault及环境缓存匹配；'
        '相邻四对请求/Prefill至少500ms且视觉差不超过500ms、扣除视觉差仍至少500ms。'
        '全部阈值前瞻冻结，无新增计算或板端执行；原M403裁决/40.81%/生产政策/服务保持。'
        '下一步另建协议绑定默认关闭运行包、实际编排/停止与owner回收检查；本步仅准备协议，尚未实现或启动上板。')
    print(json.dumps(dict(status=value['status'], sha256=digest,
                          protocol_sha256=value['protocol_sha256'], board_run=False)))


if __name__ == '__main__':
    main()
