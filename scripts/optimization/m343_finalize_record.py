"""Record the completed layer gate and control repairs, without board rerun."""
import hashlib
import json
import os
from pathlib import Path
ROOT = Path(__file__).resolve().parents[2]
BASE = ROOT / 'deployment/mage_vl4b/optimization_v1'


def sha(path): return hashlib.sha256(path.read_bytes()).hexdigest()


def atomic(path, text):
    part = path.with_name(path.name + '.m343-finalize-part')
    with part.open('w', encoding='utf-8', newline='\n') as stream:
        stream.write(text); stream.flush(); os.fsync(stream.fileno())
    os.replace(part, path)


def main():
    path = BASE / 'runs/M343-single-layer-board-01/BOARD_RESULT.json'
    digest = 'a7fadf42f0afb65dddbffb862163a1c99684a04664318463894e598f314cf67e'
    result = json.loads(path.read_text(encoding='utf-8'))
    board_path = ROOT / 'deployment/mage_vl4b/BOARD_GATE_RESULT.json'
    board = json.loads(board_path.read_text(encoding='utf-8'))
    if sha(path) != digest or board['latest_m343_single_layer']['sha256'] != digest:
        raise RuntimeError('Raw/board result not synchronized')
    for name in ('CURRENT_STATE.md', 'docsMILESTONES.md'):
        if digest not in (ROOT / name).read_text(encoding='utf-8'):
            raise RuntimeError('Document not synchronized')
    run = BASE / 'runs/M343-control-repair-01'
    run.mkdir(parents=True, exist_ok=False)
    for name in ('CURRENT_STATE.md', 'docsMILESTONES.md', 'DEPLOYMENT_OPERATION_MISTAKES_REVIEW.md', 'deployment/mage_vl4b/BOARD_GATE_RESULT.json'):
        (run / (Path(name).name + '.before')).write_bytes((ROOT / name).read_bytes())
    evidence = dict(status='FIXED_COM3_SHELL_GUARD_AND_EXPLICIT_UTF8_COLLECTION', hardware_repeated=False,
        hardware_result_sha256=digest, synchronized_records=True, collector_exit_after_repair=0,
        rejected_attempts=['Initial COM3 login prompt consumed legacy sudo check as login name; no Linux command/overlay',
                           'Final collection assertion default GBK failed after atomic writes; no higher gate, exact-byte recollection only'],
        artifacts={name: sha(ROOT / name) for name in ('scripts/m75c_uart_command.ps1', 'scripts/optimization/m343_collect_layer.py',
                  'tmp/m343/sudo_precheck_01_uart.log', 'tmp/m343/sudo_precheck_02_uart.log', 'tmp/m343/single-layer_uart.log')},
        build_id='0x4D395832', performance_pass=False, next_step='One fixed-text E2E only; original M238/M241; full logits/KV exact; then full video balanced A/B')
    atomic(run / 'RESULT.json', json.dumps(evidence, ensure_ascii=False, indent=2) + '\n')
    control_sha = sha(run / 'RESULT.json')
    board['latest_m343_control_repair'] = dict(status=evidence['status'], result=(run / 'RESULT.json').relative_to(ROOT).as_posix(),
                                              sha256=control_sha, hardware_repeated=False)
    atomic(board_path, json.dumps(board, ensure_ascii=False, indent=2) + '\n')
    section = ('## M343 单层结果闭合与控制修复（2026-10-01）\n\n'
        '独立159-Token重复固定文本embedding单layer基线/候选各25逻辑/物理FPGA事务，0重试；五family全输出、hidden、K/V、缩放重试记录和48,381,952B权重暂存逐位/字节一致。'
        '实际第二bank27,852,800B（26.5625MiB），真实runtime及基线后CMA余量满足第二bank加64MiB门槛；A-B-A-B-A、安全释放、AP_CTRL=4、两DMA=4098，错误为空。'
        '原始结果SHA `' + digest + '`，路径 `deployment/mage_vl4b/optimization_v1/runs/M343-single-layer-board-01/BOARD_RESULT.json`；仅L4单层数值通过，107.224s全门禁耗时含权重校验/加载/观察，绝非性能成绩。'
        'COM3登录提示误发及收集器GBK末尾断言失败均保留，已修复shell保护与显式UTF-8；只重做回收、未重复硬件，三份权威记录一致后才汇报。'
        '控制证据 `deployment/mage_vl4b/optimization_v1/runs/M343-control-repair-01/RESULT.json` SHA `' + control_sha + '`。'
        '稳定Build `0x4D395832`、原源文件/服务/回滚/boot/DTB/CMA配置未改，无完整请求收益或晋级；下一步仅固定文本E2E完整logits/KV逐位核对，再固定159视频及交错A/B，不重跑已通过层级。\n\n')
    for name in ('CURRENT_STATE.md', 'docsMILESTONES.md'):
        target = ROOT / name
        heading, rest = target.read_text(encoding='utf-8').split('\n', 1)
        atomic(target, heading + '\n\n' + section + rest.lstrip('\n'))
    summary = dict(status=result['status'], sha256=digest, exact=result['exact_comparison'],
        passes=[{key: p[key] for key in ('label', 'logical_calls', 'host_calls', 'retry_count', 'stage_bytes')} for p in result['passes']],
        cma_after_runtime=result['cma_after_actual_runtime_allocations'], cma_before_extra=result['cma_before_extra_bank_after_baseline'],
        cma_with_extra=result['cma_with_extra_bank'], prefetch=result['prefetch'], final_snapshot=result['final_snapshot'],
        safe_buffers_released=result['safe_buffers_released'], performance_pass=False, control_sha256=control_sha)
    atomic(path.parent / 'SUMMARY.json', json.dumps(summary, indent=2) + '\n')
    report = ('# M343 单层数值门禁\n\n状态：PASS，L4，仅单层组件；性能与晋级未验收。\n\n'
              '稳定 Build `0x4D395832`。使用原固定文本 W3 embedding 行重复到159 Token；layer0五family，每family五T32批次，尾批31 Token。保留原M238协议/解析/重试及M241层内数学。\n\n'
              '| 项目 | 基线 | 双缓冲候选 |\n|---|---:|---:|\n| 逻辑/物理FPGA事务 | 25/25 | 25/25 |\n| 保护重试 | 0 | 0 |\n| 权重暂存字节 | 48,381,952 | 48,381,952 |\n\n'
              '全部family输入/输出、hidden、K/V、缩放记录严格一致；第二组四缓冲26.5625MiB，原文件窗口SHA独立一致，地址按A-B-A-B-A复用。核和两DMA安全空闲后释放。\n\n'
              '原始证据SHA `' + digest + '`。总门禁107.224s含权重验证/初始化及哈希观察，不能用作提速成绩。稳定源/服务/回滚/boot/DTB/CMA配置未改。\n\n'
              '拒绝与修复：COM3初始已回到login，旧助手误发检查为登录名；收集器末尾默认GBK读取失败。分别修复发送前shell保护和显式UTF-8，后者只复用原始字节重做收集，无硬件重跑，全部状态已同步。\n\n'
              '下一步：独立固定文本E2E，全logits/KV严格一致后，才允许完整159视频及顺序交错A/B。没有完整请求稳定净收益时关闭候选。\n')
    atomic(path.parent / 'REPORT.md', report)
    print(json.dumps(summary))


if __name__ == '__main__': main()
