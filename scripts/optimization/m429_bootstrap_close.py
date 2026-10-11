"""Document actual installed-path omission without changing original evidence."""
import json
from m351_workflow import ROOT,BASE,atomic,encoded,sha,sync
def main():
    b=json.loads((ROOT/'deployment/mage_vl4b/BOARD_GATE_RESULT.json').read_bytes());e=b['latest_m429_isolated_bootstrap_board'];assert sha(ROOT/e['result'])==e['sha256'] and e['CPU_bootstrap_pass']
    r=json.loads((ROOT/e['result']).read_bytes());out=BASE/'runs/M429-isolated-bootstrap-closure-01/RESULT.json'
    old=BASE/'runs/M429-late11-visual-PL-board-01/BOARD_RESULT.json';assert sha(old)=='420a100e690d2f8784df1bd07db5264ed3278db8c961db9464e046740f46a7fe'
    record=dict(status='CLOSED_M429_INSTALLED_RUNTIME_PATH_OMISSION_CPU_FIXED',raw_sha256=e['sha256'],original_numerical_failure_sha256=sha(old),original_stderr_sha256=r['original_child_files'][1]['sha256'],root_cause='Parent sys.path included frozen RELEASE/runtime_site; isolated -I child omitted it and ignored PYTHONPATH.',repair='Explicit unchanged frozen module_paths() before torch/numpy import; check actual installed module identities. Preserve -I and all original math/source/asset checks.',bootstrap=r['bootstrap'],CPU_component_pass=True,real_visual_numerics_pass=False,performance_unlocked=False,original_resources_never_constructed=True,temperature_measurement_enabled=False)
    atomic(out,encoded(record),immutable=True)
    report=f'# M429 隔离入口修复\n\n原数值入口在 `import torch` 失败，尚未构造真实模型、加载 Overlay、申请 DMA 或启动 PL。`stable_restored=false` 表示未进入恢复阶段，不表示已改变 Overlay 后恢复失败。\n\n原失败 SHA {sha(old)}。原 stderr 原字节 SHA {record["original_stderr_sha256"]}，196B，已经独立回收。\n\n原因是父进程加了冻结发布 `runtime_site`，子进程 `-I` 忽略 PYTHONPATH 且遗漏显式路径。修正保留隔离，使用同一冻结 `module_paths()`。真实板端 PyTorch {r["bootstrap"]["torch_version"]}、NumPy {r["bootstrap"]["numpy_version"]} 均从发布 runtime_site 解析。\n\nCPU fixture 286批/24边界/20拒绝与恢复通过，原字节 {e["sha256"]}。fixture采用合成窄权重、Attention和fake PL submit；不是实际模型数值或提速。\n\n下一步只在同级以独立03包继续后11层完整视觉PL数值；原02失败保持。数值通过且生命周期闭合后才视觉性能，不执行语言或测温。\n'
    atomic(out.with_name('REPORT.md'),report.encode('utf-8'),immutable=True)
    review=ROOT/'DEPLOYMENT_OPERATION_MISTAKES_REVIEW.md';text=review.read_text(encoding='utf-8-sig');heading='# TeLLMe / Mage-VL 4B 部署过程操作失误复盘\n'
    assert text.startswith(heading)
    note=f'\n## M429 隔离子进程遗漏已安装 runtime_site（2026-10-06）\n\n原失败 SHA `{sha(old)}`，gate1/export0，0真实视觉/语言/Overlay/DMA/PL。主进程通过冻结module_paths加入发布runtime_site，-I子进程仅加入候选/复用小包，import torch报ModuleNotFoundError；原stderr196B SHA `{record["original_stderr_sha256"]}` 已逐字节回收。不是内存、模型精度或核失败，未加载Overlay无需恢复。\n\n必须保留-I隔离，并在导入第三方库前显式调用已核SHA的冻结module_paths；记录实际Torch/NumPy解析路径和版本，不能借宿主PYTHONPATH、移除隔离、安装新库或用开发环境绕过。CPU-only真实板端原组件286批/24边界/20负例先过，再准入原数值级；fixture fake PL不能当硬件数值PASS。新版本/独立结果目录保留原包、原rc与原字节，实际新exporter/collector/control全尺寸PASS/FAIL检查后才重试本级。CPU证据 `{e["sha256"]}`。\n'
    if '## M429 隔离子进程遗漏已安装 runtime_site' not in text:atomic(review,(heading+note+text[len(heading):]).encode('utf-8'))
    sync('latest_m429_isolated_bootstrap_closure',dict(status=record['status'],result=out.relative_to(ROOT).as_posix(),sha256=sha(out),CPU_bootstrap_pass=True,hardware_visual_timing_unlocked=False),f'## M429 隔离入口失败原因与修复闭合（2026-10-06）\n\nSHA {sha(out)}；原stderr196B完整SHA已回收，确认-I child漏runtime_site。新CPU fixture通过，仅修入口。原失败0模型/Overlay/DMA，恢复标记false是未进入恢复阶段。当前03实际回收/控制门禁29项通过，继续同级真实视觉数值；原包/裁决保留，不测温，不晋级性能。')
    print('M429_BOOTSTRAP_CLOSURE_SYNC',sha(out))
if __name__=='__main__':main()
