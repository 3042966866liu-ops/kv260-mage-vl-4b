"""Recover exact board bytes and synchronize all three authoritative records."""
import base64
import hashlib
import json
import os
from pathlib import Path
import re
import sys
ROOT = Path(__file__).resolve().parents[2]


def atomic(path, data):
    part = path.with_name(path.name + '.m343-part')
    with part.open('wb') as stream:
        stream.write(data); stream.flush(); os.fsync(stream.fileno())
    os.replace(part, path)


def decode(log):
    expected = re.search(r'M343_RESULT_SHA256=([0-9a-f]{64})', log).group(1)
    data = base64.b64decode(re.search(r'M343_RESULT_BASE64=([A-Za-z0-9+/=]+)', log).group(1), validate=True)
    if hashlib.sha256(data).hexdigest() != expected:
        raise RuntimeError('Board result hash mismatch')
    result = json.loads(data)
    if result['gate_level'] != 'single-layer': raise RuntimeError('Wrong gate identity')
    if result['status'] == 'PASS' and ('M343_LAYER_DONE gate_rc=0' not in log or result['unsafe_buffers_retained'] or not result['safe_buffers_released'] or not all(result['exact_comparison'].values())):
        raise RuntimeError('Incomplete or unsafe PASS envelope')
    return expected, data, result


def note(result, expected, relative):
    return ('## M343 独立单layer ' + result['status'] + '（2026-10-01）\n\n'
        '稳定Build `0x4D395832`，原M238打包/解析/重试与M241层内数学完全保留；原固定文本W3 embedding重复到159 Token，仅layer0组件输入、不是视频。'
        '先同Overlay稳定单层基线确认DMA安全完成，再执行M340权重双四缓冲；五family与五T32批次，完整family输出/hidden/K/V/重试契约逐位比较，原文件权重窗口SHA独立核对。'
        '结果 `' + relative + '` SHA `' + expected + '`，错误 `' + json.dumps(result['errors'], ensure_ascii=False) + '`。'
        '实际计数/26.5625MiB第二bank/CMA/释放/寄存器均以JSON为准；仅L4单层门禁，性能未验收、无完整模型/Web或晋级结论。'
        'COM3初始回到login，旧助手误发检查为登录名，无板端命令/Overlay；已增加发送前shell保护，用户重新登录续期后通过。同47项稳定硬件证据复用，稳定源/回滚/boot/DTB/CMA配置未改。'
        '下一步 ' + result['next_step'] + '；收集失败仅修复回收，不重跑硬件。\n\n')


def main():
    if len(sys.argv) > 1 and sys.argv[1] == '--self-test':
        sample = dict(status='PASS', gate_level='single-layer', unsafe_buffers_retained=False,
                      safe_buffers_released=True, exact_comparison={'hidden': True}, errors=[], next_step='fixed-text')
        data = (json.dumps(sample) + '\n').encode(); expected = hashlib.sha256(data).hexdigest()
        log = 'M343_RESULT_SHA256=' + expected + '\nM343_RESULT_BASE64=' + base64.b64encode(data).decode() + '\nM343_LAYER_DONE gate_rc=0\n'
        assert decode(log)[1] == data
        assert expected in note(sample, expected, 'fixture.json')
        try: decode(log.replace('M343_LAYER_DONE gate_rc=0', 'M343_LAYER_DONE gate_rc=1'))
        except RuntimeError: pass
        else: raise AssertionError('Nonzero runner accepted')
        try: decode(log.replace(expected, '0' * 64))
        except RuntimeError: pass
        else: raise AssertionError('Hash drift accepted')
        print('M343_COLLECTOR_SELF_TEST_PASS exact_bytes/format/runner_rejection/hash_rejection')
        return
    log = (ROOT / 'tmp/m343/single-layer_uart.log').read_text(encoding='utf-8-sig')
    expected, data, result = decode(log)
    run = ROOT / 'deployment/mage_vl4b/optimization_v1/runs/M343-single-layer-board-01'
    run.mkdir(parents=True, exist_ok=True)
    path = run / 'BOARD_RESULT.json'
    if path.exists() and path.read_bytes() != data: raise RuntimeError('Different immutable evidence exists')
    atomic(path, data)
    for name in ('CURRENT_STATE.md', 'docsMILESTONES.md', 'deployment/mage_vl4b/BOARD_GATE_RESULT.json'):
        backup = run / (Path(name).name + '.before')
        if not backup.exists(): backup.write_bytes((ROOT / name).read_bytes())
    relative = path.relative_to(ROOT).as_posix()
    board_path = ROOT / 'deployment/mage_vl4b/BOARD_GATE_RESULT.json'
    board = json.loads(board_path.read_text(encoding='utf-8-sig'))
    board['latest_m343_single_layer'] = dict(status=result['status'], evidence_level='L4_SINGLE_LAYER_ONLY',
        build_id=result['build_id'], result=relative, sha256=expected, performance_pass=False,
        formal_promotion_allowed=False, unsafe_buffers_retained=result['unsafe_buffers_retained'])
    atomic(board_path, (json.dumps(board, ensure_ascii=False, indent=2) + '\n').encode())
    section = note(result, expected, relative)
    for name in ('CURRENT_STATE.md', 'docsMILESTONES.md'):
        path = ROOT / name
        text = path.read_text(encoding='utf-8-sig')
        if expected not in text:
            heading, rest = text.split('\n', 1)
            atomic(path, (heading + '\n\n' + section + rest.lstrip('\n')).encode())
    assert json.loads(board_path.read_text(encoding='utf-8'))['latest_m343_single_layer']['sha256'] == expected
    assert all(expected in (ROOT / n).read_text(encoding='utf-8') for n in ('CURRENT_STATE.md', 'docsMILESTONES.md'))
    print(json.dumps(dict(status=result['status'], sha256=expected, errors=result['errors'],
                         exact=result.get('exact_comparison'), passes=result.get('passes'))))


if __name__ == '__main__': main()
