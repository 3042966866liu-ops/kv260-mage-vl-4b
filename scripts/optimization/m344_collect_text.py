"""Bounded result chunks, immutable exact-byte recovery and UTF-8 state sync."""
import base64
import hashlib
import json
import os
from pathlib import Path
import re
import sys
ROOT = Path(__file__).resolve().parents[2]


def atomic(path, data):
    part = path.with_name(path.name + '.m344-part')
    with part.open('wb') as f: f.write(data); f.flush(); os.fsync(f.fileno())
    os.replace(part, path)


def decode(log):
    expected = re.search(r'M344_RESULT_SHA256=([0-9a-f]{64})', log).group(1)
    chunks = re.findall(r'M344_RESULT_CHUNK=(\d+)/(\d+):([A-Za-z0-9+/=]+)', log)
    if not chunks or len(chunks) != int(chunks[0][1]): raise RuntimeError('Missing result chunk')
    data = bytearray()
    for index, (observed, count, encoded) in enumerate(chunks):
        if int(observed) != index or int(count) != len(chunks): raise RuntimeError('Wrong/duplicate chunk order')
        chunk = base64.b64decode(encoded, validate=True)
        if len(chunk) > 1800: raise RuntimeError('Oversized result chunk')
        data.extend(chunk)
    data = bytes(data)
    if hashlib.sha256(data).hexdigest() != expected: raise RuntimeError('Board raw result hash mismatch')
    result = json.loads(data)
    if result['gate_level'] != 'fixed-text-E2E': raise RuntimeError('Wrong gate level')
    if result['status'] == 'PASS' and ('M344_TEXT_DONE gate_rc=0' not in log or result['unsafe_buffers_retained'] or not result['safe_buffers_released'] or
        not all(result['exact_comparison'].values()) or not result['direct_bitwise_logits_equal'] or not result['direct_bitwise_72_kv_equal']):
        raise RuntimeError('Incomplete/unsafe numerical PASS')
    return expected, data, result


def main():
    if len(sys.argv) > 1 and sys.argv[1] == '--self-test':
        sample = dict(status='PASS', gate_level='fixed-text-E2E', unsafe_buffers_retained=False, safe_buffers_released=True,
                      exact_comparison={'logits': True}, direct_bitwise_logits_equal=True, direct_bitwise_72_kv_equal=True,
                      chinese='逐位一致' * 700)
        raw = (json.dumps(sample, ensure_ascii=False) + '\n').encode('utf-8'); digest = hashlib.sha256(raw).hexdigest()
        chunks = [raw[i:i+1800] for i in range(0, len(raw), 1800)]
        log = 'M344_RESULT_SHA256=' + digest + '\n' + ''.join('M344_RESULT_CHUNK=' + str(i) + '/' + str(len(chunks)) + ':' + base64.b64encode(c).decode() + '\n' for i,c in enumerate(chunks)) + 'M344_TEXT_DONE gate_rc=0\n'
        assert decode(log)[1] == raw
        for bad in (log.replace('gate_rc=0', 'gate_rc=1'), log.replace(digest, '0' * 64), log.replace('M344_RESULT_CHUNK=1/', 'M344_RESULT_CHUNK=0/')):
            try: decode(bad)
            except RuntimeError: pass
            else: raise AssertionError('Invalid recovery accepted')
        print('M344_COLLECTOR_SELF_TEST_PASS UTF8/raw_chunks/hash/nonzero/duplicate_rejection')
        return
    expected, data, result = decode((ROOT / 'tmp/m344/fixed-text_uart.log').read_text(encoding='utf-8-sig'))
    run = ROOT / 'deployment/mage_vl4b/optimization_v1/runs/M344-fixed-text-board-01'; run.mkdir(parents=True, exist_ok=True)
    path = run / 'BOARD_RESULT.json'
    if path.exists() and path.read_bytes() != data: raise RuntimeError('Different immutable result exists')
    atomic(path, data)
    for name in ('CURRENT_STATE.md', 'docsMILESTONES.md', 'deployment/mage_vl4b/BOARD_GATE_RESULT.json'):
        backup = run / (Path(name).name + '.before')
        if not backup.exists(): backup.write_bytes((ROOT / name).read_bytes())
    relative = path.relative_to(ROOT).as_posix()
    board_path = ROOT / 'deployment/mage_vl4b/BOARD_GATE_RESULT.json'
    board = json.loads(board_path.read_text(encoding='utf-8'))
    board['latest_m344_fixed_text'] = dict(status=result['status'], evidence_level='L5_FIXED_TEXT_ONLY' if result['status']=='PASS' else 'FAILED_FIXED_TEXT',
        build_id=result['build_id'], result=relative, sha256=expected, performance_pass=False, formal_promotion_allowed=False,
        full_logits_and_72_kv_exact=result.get('direct_bitwise_logits_equal', False) and result.get('direct_bitwise_72_kv_equal', False),
        unsafe_buffers_retained=result['unsafe_buffers_retained'])
    atomic(board_path, (json.dumps(board, ensure_ascii=False, indent=2) + '\n').encode('utf-8'))
    summary = dict(status=result['status'], sha256=expected, errors=result['errors'], performance_pass=False,
        passes=[{k:p.get(k) for k in ('label','token','logical_calls','host_calls','retry_count','language_retries','head_retries','stage_bytes')} for p in result['passes']],
        exact=result.get('exact_comparison'), prefetch=result.get('prefetch'), final_snapshot=result.get('final_snapshot'),
        next_step=result['next_step'], elapsed_s_diagnostic_not_performance=result['elapsed_s_diagnostic_not_performance'])
    atomic(run / 'SUMMARY.json', (json.dumps(summary, indent=2) + '\n').encode('utf-8'))
    note = ('## M344 固定文本 E2E ' + result['status'] + '（2026-10-01）\n\n'
        '稳定Build `0x4D395832`，原30-Token W3 embedding、36层、原M238打包/解析/保护重试与完整M241数学及全LM head。'
        '基线/候选计数与现有参考Token17见JSON；完整151936 logits和36K/36V逐位比对、全部family输入/输出及缩放重试记录严格比较，162-chain预取顺序/交替bank/原文件窗口SHA独立核对。'
        '证据 `' + relative + '` SHA `' + expected + '`，错误 `' + json.dumps(result['errors'], ensure_ascii=False) + '`；实际结果 `' + json.dumps(summary['passes']) + '`。'
        '第二bank26.5625MiB及真实runtime后CMA+64MiB余量、寄存器和安全释放均以JSON为准。仅固定文本数值验收，带观察与额外权重哈希的总耗时非性能，非完整视频/任意Web/晋级。'
        '稳定源/服务/回滚/boot/DTB/CMA配置未改；本轮Windows导入Linux专用fcntl的离线尝试被拒绝，改为本地源码/AST核验与板端Overlay前真实导入，不模拟平台依赖；准备记录 deployment/mage_vl4b/optimization_v1/runs/M344-fixed-text-preparation-01/RESULT.json 保留此项。收集失败只修复回收，不重跑硬件。下一步 ' + result['next_step'] + '。\n\n')
    for name in ('CURRENT_STATE.md', 'docsMILESTONES.md'):
        target = ROOT / name; text = target.read_text(encoding='utf-8')
        if expected not in text:
            heading, rest = text.split('\n',1); atomic(target, (heading + '\n\n' + note + rest.lstrip('\n')).encode('utf-8'))
    assert json.loads(board_path.read_text(encoding='utf-8'))['latest_m344_fixed_text']['sha256'] == expected
    assert all(expected in (ROOT / n).read_text(encoding='utf-8') for n in ('CURRENT_STATE.md','docsMILESTONES.md'))
    atomic(run / 'REPORT.md', ('# M344 固定文本 E2E\n\n' + note + '\n所有计数、内存、安全快照及逐位比较项见 SUMMARY.json 和原始 BOARD_RESULT.json。\n').encode('utf-8'))
    print(json.dumps(summary))


if __name__ == '__main__': main()
