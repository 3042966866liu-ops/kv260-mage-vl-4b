"""Close only the saved board CPU fixture; never import a model or board API."""
import json
from m351_workflow import ROOT, BASE, atomic, encoded, sha, sync
from m431_cpu_host02 import check


def main():
    board = json.loads((ROOT / 'deployment/mage_vl4b/BOARD_GATE_RESULT.json').read_bytes())
    evidence = board['latest_m431_borrowed_CPU_board']
    path = ROOT / evidence['result']
    if sha(path) != evidence['sha256'] or not all(evidence['sha256'] in (ROOT / name).read_text(encoding='utf-8-sig') for name in ('CURRENT_STATE.md', 'docsMILESTONES.md')):
        raise ValueError('Saved CPU evidence not synchronized')
    raw = check(json.loads(path.read_bytes()))
    passed = raw['status'] == 'PASS_M431_ISOLATED_CPU_BOOTSTRAP_ONLY'
    record = dict(status='CLOSED_M431_BOARD_CPU_COMPONENT_PASS' if passed else 'CLOSED_M431_BOARD_CPU_COMPONENT_FAILURE',
                  raw_sha256=evidence['sha256'], gate_return_code=raw['gate_return_code'], errors=raw['errors'],
                  manifest_sha256=raw['manifest_sha256'], source_identities_verified=raw.get('source_identities_verified'),
                  bootstrap=raw.get('bootstrap'), component=raw.get('component'),
                  child_stdout_sha256=raw.get('child_stdout', {}).get('sha256'), child_stderr_sha256=raw.get('child_stderr', {}).get('sha256'),
                  CPU_component_pass=passed, overlay_loads=0, real_DMA_allocations=0, real_FPGA_transactions=0,
                  real_model_forward_calls=0, complete_runtime_capacity_proven=False, hardware_numerical_pass=False,
                  full_request_performance_proven=False, production_promoted=False, temperature_measurement_enabled=False,
                  next_step='Prepare and isolate the late11 full-request numerical integration using the existing seven language DMA buffers; exact visual/embedding/logits/72KV/family/retry checks against the two accepted M428 samples. Performance remains locked.' if passed else 'Debug only this recorded CPU failure; preserve saved bytes and do not execute a model.')
    out = BASE / 'runs/M431-borrowed-CPU-closure-01/RESULT.json'
    atomic(out, encoded(record), immutable=True)
    report = '# M431 板端借用缓冲 CPU 组件闭合\n\n' + record['status'] + '。原始结果 SHA `' + evidence['sha256'] + '`，gate rc ' + str(raw['gate_return_code']) + '。\n\n'
    if passed:
        report += ('实际 KV260 的隔离 Python 入口解析到冻结发布目录的 Torch 2.12.1+cpu / NumPy 1.26.4，计算线程 1；49 份冻结源码 SHA 全部一致。\n\n'
                   '实际 NumPy 数组总大小 33,484,832 B，覆盖原七块缓冲几何。完成后11层的286批和22次四端口暂存，累计49,020,928 B；两个输出数组各使用143次。所有缓冲身份保持，静态配置缓存退出后失效，fixture文件已释放。15项拒绝与超时保留原owner检查通过。\n\n')
    report += ('DMA、MMIO、容量状态及字节内容明确由fixture模拟。0 Overlay、0真实DMA分配、0模型前向、0真实FPGA事务，不测温。本次证明实际板端组件及依赖/资源控制逻辑可运行；不证明完整runtime容量、真实硬件数值或完整请求性能。M430完整视觉7.686577%收益保持，不能据此宣布完整请求同幅提升。\n\n下一步：' + record['next_step'] + '\n')
    atomic(out.with_name('REPORT.md'), report.encode('utf-8'), immutable=True)
    sync('latest_m431_borrowed_CPU_closure', dict(status=record['status'], result=out.relative_to(ROOT).as_posix(), sha256=sha(out), raw_sha256=evidence['sha256'], CPU_component_pass=passed, full_request_numerical_preparation_unlocked=passed, full_request_performance_proven=False),
         f'## M431 板端CPU组件闭合（2026-10-07）\n\nSHA {sha(out)}，raw {evidence["sha256"]}；{record["status"]}，rc{raw["gate_return_code"]}。实际冻结-I后端、49源码、33MiB几何、286批/22暂存、143+143交替和15拒绝/超时保留通过；DMA/MMIO/数据明确fake，0Overlay/真实DMA/模型/PL/测温。完整runtime容量、硬件数值及完整请求性能未证明；下一步准备后11层完整请求数值接入，不自动执行性能。')
    print('M431_CPU_CLOSURE_SYNC', sha(out), record['status'])


if __name__ == '__main__':
    main()
