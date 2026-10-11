"""Collect bounded COM3 evidence and back up state before publishing it."""
import json
import argparse
from pathlib import Path
import shutil
from measurement import sha256, write_json, exclusive_lock

ROOT = Path(__file__).resolve().parents[2]
BASE = ROOT / 'deployment/mage_vl4b/optimization_v1'
OUT = BASE / 'runs/OP01-decode-one-minimal-board-01'
LOG = ROOT / 'tmp/op01_decode_one_board01'


def envelope(filename, prefix):
    text = (LOG / filename).read_text(encoding='utf-8-sig')
    begin, end = prefix + '_JSON_BEGIN', prefix + '_JSON_END'
    if text.count(begin) != 1 or text.count(end) != 1:
        raise RuntimeError('Missing/duplicate result envelope')
    if '__OP01_' + ('TRANSFER' if filename == 'transfer.log' else 'MINIMAL') + '_RC_0__' not in text:
        raise RuntimeError('Successful controller exit not recorded')
    return json.loads(text.split(begin)[1].split(end)[0].strip())


def main():
    global OUT, LOG
    parser = argparse.ArgumentParser()
    parser.add_argument('--real-chain', action='store_true')
    args = parser.parse_args()
    if args.real_chain:
        OUT = BASE / 'runs/OP01-decode-one-real-chain-board-01'
        LOG = ROOT / 'tmp/op01_decode_one_real01'
    transfer = envelope('transfer.log', 'DECODE_ONE_TRANSFER')
    result = envelope('minimal.log', 'OP01_MINIMAL')
    if transfer['status'] != 'PASS_TRANSFER_ONLY' or transfer['errors']:
        raise RuntimeError('Transfer not accepted')
    if transfer['addresses_before'] != transfer['addresses_after'] or transfer['routes_before'] != transfer['routes_after']:
        raise RuntimeError('Network restoration not proved')
    accepted = 'PASS_EXPERIMENTAL_REAL_CHAIN_ONLY' if args.real_chain else 'PASS_EXPERIMENTAL_MINIMAL_ONLY'
    if result['status'] != accepted or result['errors']:
        raise RuntimeError('Minimum gate not accepted')
    if not all(result[k] for k in ('stable_restored', 'boot_unchanged', 'cmdline_unchanged')):
        raise RuntimeError('Stable restore missing')
    if result['recovery_required'] or result['unsafe_dma_buffers_retained'] or result['formal_promotion_allowed']:
        raise RuntimeError('Invalid safety/promotion state')
    expected = ['candidate-build-id-zero', 'candidate-T32-reference-descriptor', 'candidate-decode-one-reference-descriptor']
    if args.real_chain:
        expected = ['candidate-build-id-zero', 'candidate-real-layer0-gate-up-chain']
    if [x['identity'] for x in result['transactions']] != expected:
        raise RuntimeError('Transaction coverage mismatch')
    for tx in result['transactions'] + [result['restore_transaction']]:
        if tx['observed_sha256'] != tx['expected_sha256'] or not tx['completion']['ap_done_seen']:
            raise RuntimeError('Output/completion mismatch')
    note = '''## Decode-one 实验最小上板通过（2026-09-25）

用户补充授权COM3小脚本/清单后，11,038,720字节候选通过临时网线传输，逐文件哈希通过；临时地址已删除，原地址/路由恢复。
候选0x4F503131身份零事务、T32非零单descriptor、Decode-one非零单descriptor全部通过，完整输出匹配冻结参考，DMA正常完成。
两个非零事务均为groups1/W4/rows512，完整输出262144字节；这不是全模型Decode性能测试。
已恢复稳定0x4D395832并验证零事务，boot与cmdline未变，无DMA隔离/恢复待办。
容量专项仍STOPPED_BY_USER_NOT_PASS，未正式晋级，未取得完整logits或单步加速结论。
证据optimization_v1/runs/OP01-decode-one-minimal-board-01/result.json；原始串口日志及更新前报告/状态已备份。
下一步复用真实Decode输入做单chain→单layer验证，再从同一KV852进行可比缓存条件下稳定/候选单步A/B；不重跑完整视频Prefill。

'''
    if args.real_chain:
        note = '''## Decode-one 真实 Gate/Up 单链上板通过（2026-09-25）

候选0x4F503131使用REPLAY01保存的真实layer0 Gate/Up输入（1×2560）、四路不同权重；40 groups/W4/10 descriptors。
完整2,490,368字节输出逐字节匹配参考，包括19,456个有效输出及所有填充位置。无重试、无DMA错误。
单次事务总耗时0.342452秒（分配/复制/同步/校验在内），完成等待0.269609秒；不含fixture文件读取和overlay加载。
没有同条件稳定核配对，不报告加速比，不能外推为完整Decode耗时或吞吐。
稳定0x4D395832恢复零事务通过；boot/cmdline未变，临时网线地址/路由恢复。
容量专项仍STOPPED_BY_USER_NOT_PASS，非正式晋级。证据optimization_v1/runs/OP01-decode-one-real-chain-board-01/result.json；日志和更新前状态已备份。
下一步真实单layer验证，再同KV852、同缓存条件下比较稳定/候选完整单步logits与耗时；不重跑整段视频。

'''
    key = 'decode_one_real_chain_board' if args.real_chain else 'decode_one_minimal_board'
    with exclusive_lock(BASE / 'evidence.lock'):
        OUT.mkdir(parents=True, exist_ok=False)
        shutil.copytree(LOG, OUT / 'uart_logs')
        before = OUT / 'state_before_update'; before.mkdir()
        board_path = ROOT / 'deployment/mage_vl4b/BOARD_GATE_RESULT.json'
        for p in (ROOT/'CURRENT_STATE.md', ROOT/'docsMILESTONES.md', board_path, BASE/'STATE.json'):
            shutil.copy2(p, before/p.name)
        write_json(OUT/'transfer_result.json', transfer)
        write_json(OUT/'result.json', result)
        report = OUT/'REPORT.md'
        report.write_text('# Decode-one 实验上板结果\n\n' + note + '\n|事务|总耗时（含分配/同步/校验）|\n|---|---:|\n' + ''.join(
            f"|{t['identity']}|{t['total_seconds']*1000:.3f} ms|\n" for t in result['transactions']) +
            '\n以上为单事务，不可外推为完整Token延迟或加速比。\n', encoding='utf-8')
        for p in (ROOT/'CURRENT_STATE.md', ROOT/'docsMILESTONES.md'):
            old = p.read_bytes(); split = old.find(b'\n')+1
            tmp = p.with_suffix('.minimal.partial')
            tmp.write_bytes(old[:split]+b'\n'+note.encode('utf-8')+old[split:]); tmp.replace(p)
        board = json.loads(board_path.read_text(encoding='utf-8-sig'))
        board['latest_' + key] = dict(status=result['status'], build_id=result['candidate_build'],
            result=str((OUT/'result.json').relative_to(ROOT)), sha256=sha256(OUT/'result.json'),
            stable_restored=True, capacity_status=result['capacity_status'], formal_promotion_allowed=False,
            performance_pass=False, next_action='Real layer, then matched KV852 stable/candidate Decode-one A/B' if args.real_chain else 'Real chain, layer, then matched KV852 stable/candidate Decode-one A/B')
        write_json(board_path, board)
        state_path = BASE/'STATE.json'; state = json.loads(state_path.read_text(encoding='utf-8-sig'))
        state['results'][key] = str((OUT/'result.json').relative_to(ROOT))
        state['next_action'] = board['latest_' + key]['next_action']
        write_json(state_path, state)
        write_json(OUT/'BACKUP_MANIFEST.json', {p.relative_to(OUT).as_posix(): sha256(p) for p in OUT.rglob('*') if p.is_file()})
    print(result['status'])


if __name__ == '__main__': main()
