"""Independent saved-result integrity checks, including the failed comparison."""
import json
from m351_workflow import ROOT, BASE, sha, atomic, encoded, sync
from board_safety import safe_to_release

spec = json.loads((ROOT/'tmp/m439_board_support_01/BOARD_CASES.json').read_bytes())
fixtures = {row['path']: row for row in spec['files']}
builds = dict(A=0x4D333537, B=0x4D343339, R=0x4D395832)
paths = []
for mode, count in (('buildid', 2), ('descriptor', 2), ('chain', 3), ('compare', 217)):
    path = BASE/f'runs/M439-{mode}-board-01/BOARD_RESULT.json'
    result = json.loads(path.read_bytes())
    collection = json.loads((path.parent/'COLLECTION.json').read_bytes())
    assert sha(path) == collection['raw_sha256']
    assert sha(ROOT/collection['log_path']) == collection['log_sha256']
    assert len(result['transactions']) == result['physical_transactions_started'] == count
    for row in result['transactions']:
        case = spec['cases'][row['case']] if row.get('case') else None
        packet = fixtures[case['packet'] if case else 'build_packet.bin']
        golden = fixtures[case['golden'] if case else 'build_golden.bin']
        assert (row['packet_sha256'], row['input_bytes']) == (packet['sha256'], packet['bytes'])
        assert (row['output_sha256'], row['expected_sha256'], row['output_bytes']) == (golden['sha256'], golden['sha256'], golden['bytes'])
        assert int(row['config'], 16) == int(case['config_u32'] if case else spec['build_config'], 16)
        assert row['full_output_exact'] and safe_to_release(row['completed_snapshot'])
        assert row['completed_snapshot']['ap_return'] == builds[row['variant']]
        assert row['observation']['completion_proven'] and row['wait_ns'] == row['observation']['wait_ns']
    assert result['stable_restored'] and result['safe_buffers_released'] and not result['unsafe_dma_buffers_retained']
    assert safe_to_release(result['final_snapshot']) and result['final_snapshot']['ap_return'] == builds['R']
    if mode == 'compare':
        order = [(block, variant, name, repeat) for block, variant in enumerate('ABBABAAB') for name in spec['comparison_cases'] for repeat in range(-1, 8)]
        assert [(row['block'],row['variant'],row['case'],row['repeat']) for row in result['transactions'][:-1]] == order
        assert all(row['measured'] == (row['repeat'] >= 0) for row in result['transactions'][:-1])
        assert result['gate_return_code'] == collection['gate_rc'] == 1
        assert result['status'] == 'FAIL_M439_COMPARE'
        log = (ROOT/collection['log_path']).read_text(encoding='utf-8-sig')
        assert 'M439_DONE gate_rc=1 export_rc=0' in log
    paths.append(dict(path=path.relative_to(ROOT).as_posix(), sha256=sha(path)))
summary = BASE/'runs/M439-board-summary-01/RESULT.json'
for name in ('CURRENT_STATE.md','docsMILESTONES.md','deployment/mage_vl4b/BOARD_GATE_RESULT.json'):
    assert sha(summary) in (ROOT/name).read_text(encoding='utf-8-sig')
receipt = dict(status='PASS_SAVED_RESULT_INTEGRITY_AND_SAFE_RESTORE_ONLY', evidence=paths,
               summary_sha256=sha(summary), report_sha256=sha(summary.parent/'REPORT.md'),
               comparison_original_rc=1, collection_export_rc=0, hardware_reexecuted=False,
               limitation='Host controller reports collection failure on nonzero original gate rc; saved result, full SHA, export rc0 and all three records prove collection completed. This receipt does not change FAIL_M439_COMPARE or its predetermined policy.')
path = BASE/'runs/M439-saved-board-integrity-01/RESULT.json'
atomic(path, encoded(receipt), immutable=True)
sync('latest_m439_saved_board_integrity',dict(status=receipt['status'], result=path.relative_to(ROOT).as_posix(), sha256=sha(path)),
     '## M439 保存结果独立核对（2026-10-07）\n\nSHA '+sha(path)+'；四级原字节SHA/日志SHA/冻结输入输出字节和配置/Build/完成与恢复状态/固定192样本顺序及三记录同步核对。Compare原rc1、export rc0：主机把原门禁非零称为collection failure，但回收已完整完成，无需重取或硬件重跑；原总FAIL裁决不改。')
print(receipt['status'],sha(path))
