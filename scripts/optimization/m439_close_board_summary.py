"""Close saved M439 board evidence only; never execute or rerun hardware."""
import json
from m351_workflow import ROOT, BASE, atomic, encoded, sha, sync
from m439_comparison import derive_comparison


def main():
    evidence = []
    records = {}
    for mode in ('buildid', 'descriptor', 'chain', 'compare'):
        path = BASE / f'runs/M439-{mode}-board-01/BOARD_RESULT.json'
        row = json.loads(path.read_bytes())
        digest = sha(path)
        collection = json.loads((path.parent / 'COLLECTION.json').read_bytes())
        assert collection['raw_sha256'] == digest and not collection['reexecuted']
        for name in ('CURRENT_STATE.md', 'docsMILESTONES.md', 'deployment/mage_vl4b/BOARD_GATE_RESULT.json'):
            assert digest in (ROOT / name).read_text(encoding='utf-8-sig')
        evidence.append(dict(path=path.relative_to(ROOT).as_posix(), sha256=digest, status=row['status']))
        records[mode] = row
    compare = records['compare']
    spec = json.loads((ROOT / 'tmp/m439_board_support_01/BOARD_CASES.json').read_bytes())
    computed = derive_comparison(compare['transactions'], compare['overlay_loads'], spec['comparison_cases'])
    assert computed == compare['comparison']
    measured = [row for row in compare['transactions'] if row.get('measured')]
    assert len(measured) == 192
    assert len(compare['transactions']) == 217
    assert all(row['full_output_exact'] for row in compare['transactions'])
    expected_releases = []
    for start in range(0, len(compare['allocations']), 6):
        expected_releases.extend(reversed(compare['allocations'][start:start + 6]))
    safe = (compare['stable_restored'] and compare['safe_buffers_released']
            and not compare['unsafe_dma_buffers_retained']
            and compare['releases'] == expected_releases)
    assert safe and len(compare['allocations']) == 150
    passed = compare['status'] == 'PASS_M439_COMPARE' and compare['gate_return_code'] == 0 and computed['all_cases_pass']
    if not passed:
        assert compare['gate_return_code'] == 1 and compare['errors']
    memory = compare['memory']
    diagnostics = dict(min_CmaFree_bytes=min(row['CmaFree'] for row in memory),
                       min_MemAvailable_bytes=min(row['MemAvailable'] for row in memory),
                       max_poll_gap_ns=max(row['observation']['max_poll_gap_ns'] for row in measured))
    result = dict(status='PASS_M439_BOARD_CHAIN_BENEFIT_ONLY' if passed else 'CLOSED_M439_FIRST_VERSION_BOARD_BENEFIT_NOT_PROVEN',
                  candidate_build_id='0x4D343339', baseline_build_id='0x4D333537',
                  restored_build_id='0x4D395832', evidence=evidence, comparison=computed,
                  errors=compare['errors'], original_gate_rc=compare['gate_return_code'],
                  physical_transactions=217, formal_samples=192, primers=24,
                  owned_allocations=150, releases=150, stable_restored=True,
                  all_wire_outputs_exact=True, memory_and_poll_observations=diagnostics,
                  extra_PS_slot=0, extra_CMA_bank=0, next_record_prefetch=False,
                  full_model=False, video=False, whole_request_benefit_proven=False, promoted=False,
                  next_step=('Prepare independently gated single-layer validation with the same M437 visual/language path; only then text/video and complete-request comparison.' if passed else
                             'Close this first record-load variant at the predetermined board comparison. Preserve original M357/M437. No extra samples, next-record pipeline, or full-model tests.'))
    path = BASE / 'runs/M439-board-summary-01/RESULT.json'
    atomic(path, encoded(result), immutable=True)
    report = '# M439：当前记录连续读取的实板裁决\n\n'
    report += ('原定实板单链收益门禁通过；尚无完整模型或视频请求增量性能结论。\n\n' if passed else
               '原定实板收益判据未全部通过；本版在这里结束，不补测直到通过。数值正确性与已通过的离线结果保留。\n\n')
    report += 'A 为原 M357 `0x4D333537`，B 为 M439 `0x4D343339`；稳定 M9 仅用于恢复。只改每个 shard 当前记录连续读取及片内小缓冲，未加入下一条预取、PS slot 或 CMA bank。\n\n'
    report += 'Build-ID、单 descriptor、完整 W2 Q 链及 W4 代表链均通过完整输出比较。固定八个 block 为 ABBA＋BAAB，每种形状每 block 一次 primer 和八次正式事务；192 次正式测量全部保留。\n\n'
    report += '| 形状 | A 中位数 ms | B 中位数 ms | 降幅 | ABBA 降幅 | BAAB 降幅 | 判据通过 |\n|---|---:|---:|---:|---:|---:|---|\n'
    for name, row in computed['cases'].items():
        report += f"| {name} | {row['original_median_ns']/1e6:.6f} | {row['candidate_median_ns']/1e6:.6f} | {row['gain_fraction']*100:.4f}% | {row['balanced_blocks'][0]['gain_fraction']*100:.4f}% | {row['balanced_blocks'][1]['gain_fraction']*100:.4f}% | {row['pass_']} |\n"
    report += '\n判据预先冻结：两个平衡四 block 组都缩短，且所有 B block 中位数都小于所有 A block 中位数；三种形状全部满足且观测时钟一致才通过。原裁决不修改。\n\n'
    for name, row in computed['cases'].items():
        report += f'## {name} 的八个 block\n\n| block | 核 | 中位数 ms | 八次样本 ms | 极差 ms |\n|---|---|---:|---|---:|\n'
        for block in row['block_medians']:
            samples = ', '.join(f'{x/1e6:.6f}' for x in block['samples_ns'])
            report += f"| {block['block']} | {block['variant']} | {block['median_ns']/1e6:.6f} | {samples} | {block['spread_ns']/1e6:.6f} |\n"
        report += '\n'
    report += '计时从提交 S2MM 前到捕获 ap_done 且两 DMA idle，包含提交、搬运、设备执行与主机轮询；权重暂存、输出同步与哈希在计时外。不是纯 PL 计算周期，也不是完整请求时间。没有清缓存或驱逐；同组缓冲复用。\n\n'
    report += f"正式事务最大轮询间隙 {diagnostics['max_poll_gap_ns']/1e6:.6f} ms；全程最小 CmaFree {diagnostics['min_CmaFree_bytes']/2**20:.6f} MiB，最小 MemAvailable {diagnostics['min_MemAvailable_bytes']/2**20:.6f} MiB。实际内存快照不等于完整 runtime 容量证明；未恢复固定 64 MiB 拒绝。\n\n"
    report += '217 次完整输出一致；150 块缓冲经原所有者按组逆序释放，稳定 Overlay 已通过合法事务确认恢复。\n\n'
    if compare['errors']:
        report += '原错误：\n\n' + ''.join('- ' + error + '\n' for error in compare['errors']) + '\n'
    report += '下一步：' + result['next_step'] + '\n\n证据：\n\n'
    for row in evidence:
        report += '- [' + row['path'].split('/')[-2] + '](' + str(ROOT / row['path']).replace('\\', '/') + ')：`' + row['sha256'] + '`\n'
    atomic(path.parent / 'REPORT.md', report.encode('utf-8'), immutable=True)
    sync('latest_m439_board_summary', dict(status=result['status'], result=path.relative_to(ROOT).as_posix(), sha256=sha(path), report=(path.parent/'REPORT.md').relative_to(ROOT).as_posix(), build_id='0x4D343339', board=True, full_model=False, promoted=False),
         '## M439 单条记录第一版实板总裁决（2026-10-07）\n\nSHA ' + sha(path) + '；' + result['status'] + '。Build/descriptor/W2和W4链数值通过，原定ABBA＋BAAB三种形状192正式样本全部保留，217事务/150所有者释放及稳定恢复闭合。计时为主机观察完整小事务，不是纯PL或完整请求。下一步 ' + result['next_step'])
    print(json.dumps(result, ensure_ascii=True))


if __name__ == '__main__':
    main()
