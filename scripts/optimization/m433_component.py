"""Isolated actual timed-provider fixture; no model/board performance evidence."""
import ast
import json
import subprocess
from m351_workflow import ROOT, BASE, HERE, atomic, encoded, sha, sync

STAGE = ROOT / 'tmp/m43301/component_stage'
OLD = ROOT / 'tmp/m43202/component_stage'


def once(text, old, new):
    if text.count(old) != 1:
        raise RuntimeError('Component adaptation anchor differs: ' + old)
    return text.replace(old, new)


def prepare():
    if STAGE.exists():
        raise RuntimeError('Component stage exists')
    STAGE.mkdir(parents=True)
    for p in OLD.iterdir():
        if p.is_file() and p.name not in ('test_m432_provider.py', 'entry.py'):
            atomic(STAGE / p.name, p.read_bytes(), immutable=True)
    atomic(STAGE / 'm433_timed_visual.py', (HERE / 'm433_timed_visual.py').read_bytes(), immutable=True)
    atomic(STAGE / 'm430_timed_scope.py', (HERE / 'm430_timed_scope.py').read_bytes(), immutable=True)
    text = (OLD / 'test_m432_provider.py').read_text(encoding='utf-8')
    text = once(text, 'from m432_request_visual import VisualProvider', 'from m433_timed_visual import TimedVisualProvider as VisualProvider')
    text = once(text, "provider.current_owner = provider.current_scope = None; provider.disposed = False", "provider.current_owner = provider.current_scope = None; provider.disposed = False; provider.enabled = True")
    text = once(text, "assert len(submitted) == 286 and p.result['visual_matched_wire_batches'] == 286 and len(p.result['integrated_boundaries']) == 24", "assert len(submitted) == 286 and p.result['visual_matched_wire_batches'] == 286\n        assert 'integrated_boundaries' not in p.result and p.result['integrated_visual'] == []\n        assert p.current_scope is None and p.current_owner is None")
    text = once(text, "bad.result['integrated_visual'] = [tensor(original)]", "bad.enabled = True")
    text = text.replace('complete286_input_output_packets_and24_boundaries_exact=True', 'complete286_order_geometry_and_final_feature_exact=True, diagnostic_boundaries_and_full_wire_SHA_omitted_from_timer=True')
    text = text.replace('actual_provider_call=True', 'actual_timed_provider_call=True')
    ast.parse(text, feature_version=(3, 10))
    atomic(STAGE / 'test_m433_provider.py', text.encode('utf-8'), immutable=True)
    entry = (OLD / 'entry.py').read_text(encoding='utf-8').replace('tmp/m43202/component_stage', 'tmp/m43301/component_stage').replace('from test_m432_provider import', 'from test_m433_provider import').replace('M432_PROVIDER_COMPONENT', 'M433_PROVIDER_COMPONENT')
    atomic(STAGE / 'entry.py', entry.encode('utf-8'), immutable=True)
    print('M433_COMPONENT_STAGE_READY')


def component():
    folder = ROOT / 'tmp/m43301/component'
    if folder.exists():
        raise RuntimeError('Original component receipt exists')
    cp = subprocess.run(['wsl.exe', '-d', 'Ubuntu-24.04', '--', '/home/lyy/projects/qwen_baseline/.venv/bin/python', '-I', '-B',
                         '/mnt/c/Users/30429/Desktop/TeLLMe_FPGA_2026/tmp/m43301/component_stage/entry.py'], capture_output=True, timeout=210)
    atomic(folder / 'stdout.bin', cp.stdout, immutable=True)
    atomic(folder / 'stderr.bin', cp.stderr, immutable=True)
    lines = [x.split('=', 1)[1] for x in cp.stdout.decode('utf-8').splitlines() if x.startswith('M433_PROVIDER_COMPONENT=')]
    c = json.loads(lines[0]) if cp.returncode == 0 and len(lines) == 1 else None
    if c is not None and not all(c[k] for k in ('actual_timed_provider_call', 'complete286_order_geometry_and_final_feature_exact',
            'diagnostic_boundaries_and_full_wire_SHA_omitted_from_timer', 'static_cache_invalidated', 'successful_disposal',
            'active_second_layer_timeout_preserves_original_owner_and_restores_bindings')):
        raise RuntimeError('Component receipt incomplete')
    status = 'PASS_M433_ACTUAL_TIMED_PROVIDER_FIXTURE_ONLY' if c is not None else 'FAIL_M433_ACTUAL_TIMED_PROVIDER_FIXTURE_ONLY'
    record = dict(status=status, component=c, return_code=cp.returncode,
                  stdout_sha256=sha(folder / 'stdout.bin'), stderr_sha256=sha(folder / 'stderr.bin'),
                  stage_sha256={p.name: sha(p) for p in STAGE.iterdir() if p.is_file()},
                  source_sha256=sha(HERE / 'm433_timed_visual.py'),
                  board_run=False, model_quality_proven=False, performance_pass=False, temperature_measurement_enabled=False)
    out = BASE / 'runs/M433-timed-provider-component-01/RESULT.json'
    atomic(out, encoded(record), immutable=True)
    sync('latest_m433_timed_provider_component', dict(status=status, result=out.relative_to(ROOT).as_posix(), sha256=sha(out)),
         f'## M433 完整请求轻量视觉provider组件（2026-10-07）\n\nSHA {sha(out)}，{status}；明确合成窄权重/Attention与fake DMA/MMIO，实际冻结包装/encoder/MLP及新轻量provider。计时内不导出24边界或wire SHA，保留286顺序几何、22暂存及完整最终输出校验、缓存失效和活动超时保留；不是模型质量、板端容量或性能证据，不测温。M432仍独立执行数值级，不能在闭合前启动性能。')
    print('M433_COMPONENT_SYNC', sha(out), status)
    if c is None:
        raise RuntimeError('Actual timed provider fixture failed; original receipts retained')


if __name__ == '__main__':
    import sys
    {'prepare': prepare, 'component': component}[sys.argv[1]]()
