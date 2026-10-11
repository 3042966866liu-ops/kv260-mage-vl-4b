"""Freeze CPU-only algorithm preparation, explicitly excluding board proof."""
import ast
import json
import subprocess
import sys
import shutil
from m351_workflow import ROOT, HERE, BASE, sha, atomic, encoded, sync


def main():
    out = BASE / 'runs/M389-silu-workspace-preparation-01'
    pkg = BASE / 'candidates/M389-silu-workspace-component-01'
    if out.exists() or pkg.exists():
        raise RuntimeError('Immutable preparation already exists')
    recovery = {}
    for name in ('CURRENT_STATE.md', 'DEPLOYMENT_OPERATION_MISTAKES_REVIEW.md',
                 'docsMILESTONES.md', 'deployment/mage_vl4b/BOARD_GATE_RESULT.json'):
        text = (ROOT / name).read_text(encoding='utf-8-sig')
        recovery[name] = dict(sha256=sha(ROOT / name), lines=len(text.splitlines()))
    board = json.loads((ROOT / 'deployment/mage_vl4b/BOARD_GATE_RESULT.json').read_text(encoding='utf-8'))
    prior = board['latest_m388_ps_performance_closure']
    assert sha(ROOT / prior['result']) == prior['sha256']
    assert prior['status'] == 'CLOSED_PS_PREFETCH_VARIANT_NET_BENEFIT_UNPROVEN'
    closure_path = BASE / 'candidates/M388-ps-performance-01/SOURCE_CLOSURE.json'
    closure = json.loads(closure_path.read_text(encoding='utf-8'))
    release = ROOT / 'release_staging/kv260-mage-vl-4b-prebuilt-install-20260926-v7'
    rows = {r['path']: r for r in closure['files']}
    sources = {}
    for module in ('m241_video_language_runtime', 'video_language_runtime'):
        relative = closure['modules'][module]
        source = release / relative
        assert sha(source) == rows[relative]['sha256']
        sources[module] = dict(path=source.relative_to(ROOT).as_posix(), sha256=sha(source))
    old = ROOT / 'tmp/web3_runtime_audit/qwen_fpga_runtime.py'
    old_text = old.read_text(encoding='utf-8')
    assert 'def prefill_tokens' in old_text and 'np.clip(gate, -30.0, 30.0)' in old_text
    old_precedent = dict(path=old.relative_to(ROOT).as_posix(), sha256=sha(old),
                         decode_and_prefill_scratch_fallback=True, clips_gate=True,
                         evidence_of_Mage4B159_performance=False)
    fixture = ROOT / 'deployment/mage_vl4b/artifacts/m143_m120_layer0_boundaries.npz'
    # M143's gate_up array is that family's INPUT, not gate/up projection outputs.
    fixture_audit = dict(path=fixture.relative_to(ROOT).as_posix(), sha256=sha(fixture),
                         gate_up_shape=[30, 2560], mlp_down_shape=[30, 9728],
                         suitable_as_real159_gate_up_pair=False)
    test = subprocess.run([sys.executable, '-X', 'utf8', '-B',
                           str(HERE / 'test_m389_silu_workspace.py')],
                          capture_output=True, text=True, encoding='utf-8')
    assert test.returncode == 0 and 'Ran 8 tests' in test.stderr and test.stderr.rstrip().endswith('OK')
    names = ('m389_silu_workspace.py', 'test_m389_silu_workspace.py')
    for name in names:
        tree = ast.parse((HERE / name).read_text(encoding='utf-8'), feature_version=(3, 10))
        imports = [a.name.split('.')[0] for n in ast.walk(tree)
                   if isinstance(n, ast.Import) for a in n.names]
        assert not {'pynq', 'torch', 'video_server', 'board_runtime'}.intersection(imports)
    pkg.mkdir(parents=True)
    for name in names:
        shutil.copyfile(HERE / name, pkg / name)
    plan = '''# M389 SiLU×up 工作缓冲组件准备

当前仅离线 L0：159×9728 FP32 工作缓冲6,186,? bytes的准确值以RESULT.json为准；默认关闭，未修改生产或冻结源，未上传、未上板，不证明性能。

实际来源：M388冻结模块映射解析到M242中的M241 prefill和M181中的silu。原顺序为negative、exp、1+、divide、FP32 astype、multiply。新组件保留顺序、不clip、不融合、不使用reciprocal；去除已经FP32的冗余astype，五次ufunc out写入同一工作缓冲。gate/up只读。

旧Qwen3B在Decode与Prefill的fallback已有单scratch原位算法，但先clip到±30；不能照搬数学或外推性能，也不能称单scratch思想首次实现。本组件针对Mage4B固定159-token的持久工作缓冲。

8项Windows合成算法/生命周期检查通过，含真实尺寸、signed zero/subnormal/overflow/NaN、非连续只读输入、逐位结果、alias/shape/dtype拒绝、重复缓冲、忙碌及消费者异常拒绝复用/释放。浮点overflow告警保留，exp溢出处理与原公式一致；不以告警替代完整结果比较。没有实际DMA/异步解析生命周期证明。

## 真实输入尚缺失

已有M388 JSON仅保存gate/up相关计算的哈希及最终数值摘要，没有gate/up原数组。M143 layer00_gate_up为30×2560的归一化激活输入，不是两个投影输出，不能伪作159×9728输入或将重复/随机数组称为真实视频输入。

下一具体步骤只准备独立的layer0真实输入捕获入口：复用冻结M276/M273视频及M238/M241、原七DMA封锁新分配和已验证视频停止预算，使用原固定视频，核对预处理、视觉特征和159-token语言输入SHA；执行到layer0 gate_up完整返回，保存两个159×9728 FP32投影输出及身份后主动结束，不进入mlp_down或后续层。不重跑M388八次/全模型来生成组件输入。包必须区分预期边界结束与故障，未知输入/未完成解析或活动DMA不得释放。

真实数组捕获和SHA闭合并同步后，才制作无Overlay CPU组件门禁。先确认实际板端Python/NumPy身份、输入SHA和形状，保持两数组不变；按原表达式与工作缓冲作ABBA和BAAB成组重复，数值核对置于计时外。记录预分配、工作缓冲建立/关闭（另行计时）、每调用及批次时间、缓存/驻留和RSS范围。第一次ufunc预热两组相同；文件载入不混进算子计时。所有异常留存，禁止静默容差或以Windows速度作板端证据。组件无稳定收益就在组件级关闭，不扫描线程数、不扩大模型。

模型接入是后续独立候选：工作缓冲必须等本层mlp_down所有T32、预打包/解析future、缩放重试结束及两DMA/AP idle后才可复用。纯Pythonlease正常退出不能替代真实硬件屏障。消费者故障/超时持有owner与工作缓冲并阻止DMA清理；不得kill/free。优先验证实际同步_family返回关系及源码闭包，不提前patch生产prefill。

组件收益成立后只改变这一处，按必要数值级别核对单层/固定文本/固定视频完整KV/logits/重试与释放，再轻量完整请求交错性能。保留当前并行Build0x4D333537和单parser，PS预读、双parser关闭，原生产准入/服务/稳定rollback/boot/DTB/CMA保持。普通工作缓冲必须纳入完整runtime内存预算；本次尚无新增容量证明。
'''.replace('6,186,? bytes的准确值以RESULT.json为准', '6,187,008B（5.900390625MiB）')
    atomic(pkg / 'PLAN.md', plan.encode('utf-8'))
    atomic(pkg / 'SOURCE_IDENTITY.json', encoded(dict(sources=sources, old_precedent=old_precedent,
                                                      fixture_audit=fixture_audit)))
    rows = [dict(path=p.name, bytes=p.stat().st_size, sha256=sha(p)) for p in sorted(pkg.iterdir())]
    atomic(pkg / 'SHA256SUMS', ''.join(r['sha256']+'  '+r['path']+'\n' for r in rows).encode('ascii'))
    rows.append(dict(path='SHA256SUMS', bytes=(pkg/'SHA256SUMS').stat().st_size, sha256=sha(pkg/'SHA256SUMS')))
    atomic(pkg/'PACKAGE_MANIFEST.json', encoded(dict(schema='M389-offline-component-only-v1',
           files=rows, file_count=len(rows), total_bytes=sum(r['bytes'] for r in rows))))
    value = dict(status='PASS_OFFLINE_SILU_WORKSPACE_ALGORITHM_ONLY', recovery=recovery,
                 prior_closure=prior, sources=sources, old_precedent=old_precedent,
                 fixture_audit=fixture_audit, tests_run=8, test_output=test.stderr,
                 shape=[159, 9728], workspace_bytes=159*9728*4,
                 windows_numpy_version=__import__('numpy').__version__, synthetic_inputs=True,
                 real_video_inputs_available=False, board_run=False, model_integrated=False,
                 runtime_capacity_proven=False, performance_pass=False, default_enabled=False,
                 production_changed=False, manifest_sha256=sha(pkg/'PACKAGE_MANIFEST.json'),
                 package_files=len(rows), next_step='Prepare bounded layer0 actual fixed-video gate/up capture only; do not rerun full model or M388')
    assert value['workspace_bytes'] == 6187008
    atomic(out/'RESULT.json', encoded(value), immutable=True)
    digest = sha(out/'RESULT.json')
    sync('latest_m389_silu_workspace_preparation', dict(status=value['status'],
         result=(out/'RESULT.json').relative_to(ROOT).as_posix(), sha256=digest,
         board_run=False, performance_pass=False),
         f'## M389 Mage4B SiLU×up工作缓冲离线组件（2026-10-03）\n\n'
         f'冻结M388加载映射核对，默认关闭单FP32工作缓冲6187008B，8项Windows合成逐位/生命周期检查；SHA {digest}。'
         '旧Qwen3B Decode/Prefill已有带clip的scratch fallback，不能直接搬数学或称新思想。'
         'M388只有哈希、M143是30-token family输入，缺少真实159 gate/up原数组；无板端/容量/性能证据。'
         'M388关闭裁决和旧硬件40.81%保持，PS预读/双parser继续关闭。下一步仅准备layer0实际固定视频捕获入口，输出SHA同步后CPU组件；不得重跑全模型生成输入，组件无收益不扩大。')
    print(json.dumps(dict(status=value['status'], sha256=digest,
                          manifest_sha256=value['manifest_sha256'], workspace_bytes=value['workspace_bytes'])))


if __name__ == '__main__':
    main()
