"""Freeze and check the single PS visual observation; no board commands."""
import ast
import copy
import importlib.util
import json
from pathlib import Path
import sys
import tempfile
from types import SimpleNamespace
import numpy as np
from m351_workflow import ROOT, BASE, HERE, atomic, encoded, sha, sync
from m406_vision_observer import Clock, Observer, proc_snapshot, instrument_forward

PKG = BASE / 'candidates/M406-vision-cost-observer-01'


def component_checks():
    source = (ROOT / 'tmp/m223_realtime/m223_realtime_delta/m207_ps_vision_runtime.py').read_text(encoding='utf-8')
    # Explicit fake Torch exercises the actual frozen forward AST and patch lifecycle.
    class Tensor:
        def __init__(self, array): self.array = np.asarray(array, dtype=np.float32)
        def to(self, dtype): return Tensor(self.array.copy())
    def linear(values, weight, bias):
        return Tensor(values.array @ weight.array.T + (0 if bias is None else bias.array))
    functional = SimpleNamespace(linear=linear, layer_norm=lambda x: x, gelu=lambda x: x, softmax=lambda x: x)
    fake = SimpleNamespace(Tensor=Tensor, bfloat16='fake-bf16', float32='fake-fp32',
                           from_numpy=Tensor, nn=SimpleNamespace(functional=functional),
                           matmul=lambda a, b: Tensor(a.array @ b.array))
    tree = ast.parse(source)
    cls = next(x for x in tree.body if isinstance(x, ast.ClassDef) and x.name == 'M207FP32GemmW4Linear')
    forward = next(x for x in cls.body if isinstance(x, ast.FunctionDef) and x.name == 'forward')
    namespace = {}
    exec(compile(ast.fix_missing_locations(ast.Module(body=[copy.deepcopy(forward)], type_ignores=[])), '<frozen-M207-forward>', 'exec'), namespace)
    class Linear:
        forward = namespace['forward']
        def __init__(self, dtype, bias):
            self.name, self.output_dtype, self.bias = 'fixture', dtype, bias
            self.store = SimpleNamespace(decode=lambda name: np.asarray([[1, 2], [-2, .5]], np.float32))
    class Vision:
        def __init__(self, module): self.module = module
        def named_modules(self): return [('linear', self.module)]
        def __call__(self, values): return self.module.forward(values)
    saved = sys.modules.get('torch')
    sys.modules['torch'] = fake
    original_to, original_forward = Tensor.to, Linear.forward
    checks = []
    try:
        for dtype in ('fake-fp32', 'fake-bf16'):
            for bias in (None, Tensor([.25, -.5])):
                obj = Linear(dtype, bias)
                vision = Vision(obj)
                values = Tensor([[3, -2], [0, .125]])
                ref = vision(values).array.copy()
                runtime = SimpleNamespace(torch=fake, vision=vision)
                with Observer(runtime, Linear, source) as obs:
                    with obs.clock.phase('fixture', 'vision_total'):
                        out = vision(values)
                assert np.array_equal(ref, out.array)
                assert Tensor.to is original_to and Linear.forward is original_forward
                ev = obs.clock.evidence()
                assert ev['exclusive_sum_ns'] == ev['vision_wall_ns']
                assert len(ev['gemm_windows']) == 1
                checks.append('exact-forward-AST/fake-API-' + dtype + '-bias-' + str(bias is not None))
        old = functional.linear
        def fail(*args): raise ValueError('intentional GEMM failure')
        functional.linear = fail
        try:
            try:
                with Observer(runtime, Linear, source) as obs:
                    with obs.clock.phase('fixture', 'vision_total'):
                        vision(values)
            except ValueError as error: assert 'intentional' in str(error)
            else: raise AssertionError('Exception swallowed')
            assert not obs.restore and not obs.clock.stack
            assert Tensor.to is original_to and Linear.forward is original_forward
            obs.clock.evidence()
            checks.append('exception-propagation/exact-binding-restoration')
        finally: functional.linear = old
        clock = Clock()
        try:
            with clock.phase('root', 'vision_total'):
                with clock.phase('attn', 'attention_other'):
                    with clock.phase('qkv', 'linear_gemm'): pass
                    with clock.phase('attn', 'attention_QK'): pass
                    with clock.phase('attn', 'attention_AV'): pass
        finally: ev = clock.evidence()
        assert ev['exclusive_sum_ns'] == ev['vision_wall_ns']
        checks.append('Attention-parent-excludes-QKV-and-QK-AV')
        clock.events = 10000
        try:
            with clock.phase('over', 'vision_total'): pass
        except RuntimeError: pass
        else: raise AssertionError('Event cap ignored')
        checks.append('event-budget-fail-closed')
        folder = ROOT / 'tmp/m406'; folder.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(dir=folder) as t:
            proc = Path(t)
            (proc / 'self/task/123').mkdir(parents=True)
            (proc / 'stat').write_text('cpu0 10 0 20 30 4 0 0 0 8 0\ncpu1 2 0 3 4 0 0 0 0\n', encoding='utf-8')
            fields = ['R'] + ['0'] * 20
            fields[11], fields[12] = '100', '20'
            (proc / 'self/task/123/stat').write_text('123 (explicit fake worker) ' + ' '.join(fields), encoding='utf-8')
            (proc / 'self/io').write_text('read_bytes: 1024\nwrite_bytes: 0\n', encoding='utf-8')
            (proc / 'self/status').write_text('VmRSS: 123 kB\nVmHWM: 456 kB\n', encoding='utf-8')
            snap = proc_snapshot(proc)
            assert snap['cpu']['cpu0']['total'] == 64 and snap['cpu']['cpu0']['idle'] == 34
            assert snap['tasks']['123']['ticks'] == 120 and snap['memory']['VmRSS'] == 123*1024
            checks.append('actual-proc-parser/fake-spaced-task-name/guest-not-double-counted')
        return checks
    finally:
        if saved is None: sys.modules.pop('torch', None)
        else: sys.modules['torch'] = saved


def main():
    checks = component_checks()
    b = json.loads((ROOT / 'deployment/mage_vl4b/BOARD_GATE_RESULT.json').read_bytes())
    prior = b['latest_m405_vision_evidence_audit']
    assert sha(ROOT / prior['result']) == prior['sha256']
    assert all(prior['sha256'] in (ROOT / n).read_text(encoding='utf-8-sig')
               for n in ('CURRENT_STATE.md', 'docsMILESTONES.md'))
    if PKG.exists(): raise RuntimeError('Frozen package exists')
    original = BASE / 'candidates/M403-tail-performance-01'
    m = json.loads((original / 'PACKAGE_MANIFEST.json').read_bytes())
    assert sha(original / 'PACKAGE_MANIFEST.json') == 'a1bfd96e1324fd86f89f574504c280dd64028f4ef2b54155cbcbd0a00377f1a8'
    inputs = ('frozen_video_identity.py', 'M348_SOURCE_IDENTITIES.json')
    for name in inputs:
        r = next(x for x in m['files'] if x['path'] == name)
        assert sha(original / name) == r['sha256']
    raw = json.loads((BASE / 'runs/M403-tail-performance-board-01/BOARD_RESULT.json').read_bytes())
    assert sha(BASE / 'runs/M403-tail-performance-board-01/BOARD_RESULT.json') == 'f83ba109292b171d94908632a2f69c8d74c1d075b301f66b259629433c4cb321'
    numeric = raw['samples'][0]['numeric_sha_after_timer']
    assert all(x['numeric_sha_after_timer']['visual'] == numeric['visual'] for x in raw['samples'])
    PKG.mkdir(parents=True)
    for name in ('m406_vision_observer.py', 'm406_vision_gate.py'):
        ast.parse((HERE / name).read_text(encoding='utf-8'), feature_version=(3, 10))
        atomic(PKG / name, (HERE / name).read_bytes(), immutable=True)
    for name in inputs: atomic(PKG / name, (original / name).read_bytes(), immutable=True)
    atomic(PKG / 'EXPECTED.json', encoded(dict(visual=numeric['visual'], preprocessed=numeric['preprocessed'])), immutable=True)
    runner = '''#!/usr/bin/env bash
set -euo pipefail
[[ $EUID == 0 ]] || exit 65
cd "$(dirname "${BASH_SOURCE[0]}")"
task_manifest=${1:?manifest}
task_mode=${2:?Run or Collect}
task_python=/usr/local/share/pynq-venv/bin/python
export PYTHONDONTWRITEBYTECODE=1
if [[ $task_mode == Collect ]]; then exec "$task_python" -B ./m406_vision_gate.py Collect; fi
[[ $task_mode == Run && ${M406_ENABLE_PS_VISION:-0} == 1 ]] || exit 66
printf '%s  PACKAGE_MANIFEST.json\\n' "$task_manifest" | sha256sum -c -
sha256sum -c SHA256SUMS
[[ ! -e /home/ubuntu/m406_vision_cost_observation_01 ]] || exit 67
set +e
"$task_python" -B ./m406_vision_gate.py "$task_manifest" --enable-PS-vision-observation
task_gate_rc=$?
"$task_python" -B ./m406_vision_gate.py Collect
task_export_rc=$?
set -e
echo "M406_DONE gate_rc=$task_gate_rc export_rc=$task_export_rc"
if [[ $task_gate_rc != 0 ]]; then exit "$task_gate_rc"; fi
exit "$task_export_rc"
'''
    atomic(PKG / 'run_m406_vision.sh', runner.encode('utf-8'), immutable=True)
    files = sorted(PKG.iterdir())
    atomic(PKG / 'SHA256SUMS', ''.join(f'{sha(p)}  {p.name}\n' for p in files).encode('ascii'), immutable=True)
    files = sorted(PKG.iterdir())
    manifest = dict(schema='M406-PS-only-visual-cost-observation-v1', default_off=True,
                    file_count=len(files), total_bytes=sum(p.stat().st_size for p in files),
                    files=[dict(path=p.name, bytes=p.stat().st_size, sha256=sha(p)) for p in files])
    atomic(PKG / 'PACKAGE_MANIFEST.json', encoded(manifest), immutable=True)
    result = dict(status='PASS_OFFLINE_PS_VISUAL_COST_OBSERVER_PREPARATION', evidence_level='L0',
                  manifest_sha256=sha(PKG / 'PACKAGE_MANIFEST.json'), prior_audit_sha256=prior['sha256'],
                  checks=checks, actual_frozen_M207_AST_executed_with_fake_Torch=True,
                  fake_Torch_not_target_backend_or_bf16_proof=True, board_Torch_component_required_before_model=True,
                  source_sha256={n:sha(HERE/n) for n in ('m406_prepare.py','m406_vision_gate.py','m406_vision_observer.py')},
                  file_count=manifest['file_count'], total_bytes=manifest['total_bytes'],
                  fixed_visual_forwards=2, first_forward_cache_preparation=True,
                  extra_requests=False, visual_wall_budget_s=90, total_budget_s=600,
                  new_board_run=False, language_forwards=0, extra_DMA=0, performance_pass=False,
                  authorization_log_sha256=sha(ROOT / 'tmp/m406/sudo_precheck_01.log'),
                  authorization_was_blocked_before_package=True, user_reported_renewed=True)
    out = BASE / 'runs/M406-vision-observer-preparation-01/RESULT.json'
    atomic(out, encoded(result), immutable=True)
    digest = sha(out)
    sync('latest_m406_vision_observer_preparation',dict(status=result['status'],sha256=digest,
         result=out.relative_to(ROOT).as_posix(),manifest_sha256=result['manifest_sha256']),
         f'## M406 PS视觉窄成本观察准备（2026-10-05）\n\nSHA {digest}；7载荷默认关闭，'
         '原M207 forward插入计时后移除与原AST严格相同；8项实际AST/fake Torch与异常/绑定恢复/排他计时/proc解析检查。'
         'Windows无Torch，假API不证明目标BF16/后端；板端真实Torch八案例及异常恢复先于模型构造。'
         '固定一次原视觉缓存预热+一次视觉观察，完整原资产SHA/同输入视觉SHA，0语言/Overlay/DMA/FPGA；'
         'backend/线程保持，100ms逐核/进程与native算子报告。尚未上传/执行，无新性能。'
         'COM3原shell/sudo需要密码记录保留，用户已报告续期；下一步实际控制/回收检查后一次同终端验证。')
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == '__main__': main()
