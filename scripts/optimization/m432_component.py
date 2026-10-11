"""Isolate the actual provider; preserve every component receipt, never use board control."""
import ast
import json
import subprocess
import sys
from m351_workflow import ROOT, BASE, HERE, atomic, encoded, sha, sync

PKG = BASE / 'candidates/M432-late11-integrated-video-01'
STAGE = ROOT / 'tmp/m43201/component_stage'


def prepare():
    if STAGE.exists():
        raise RuntimeError('Original isolated stage exists')
    plan = json.loads((PKG / 'PLAN.json').read_bytes())
    paths = []
    for row in plan['visual_reused_packages']:
        matches = [p.parent for p in (BASE / 'candidates').glob('*/PACKAGE_MANIFEST.json') if sha(p) == row['manifest_sha256']]
        if len(matches) != 1:
            raise RuntimeError('Unique actual reused packet required')
        folder = matches[0]
        for e in json.loads((folder / 'PACKAGE_MANIFEST.json').read_bytes())['files']:
            if sha(folder / e['path']) != e['sha256']:
                raise RuntimeError('Actual stage dependency changed')
        paths.append(folder)
    STAGE.mkdir(parents=True)
    for name, p in [('m432_request_visual.py', PKG / 'm432_request_visual.py'), ('m428_saved_features.py', PKG / 'm428_saved_features.py'),
                    ('m431_borrowed_visual.py', PKG / 'm431_borrowed_visual.py'), ('m431_window_component.py', HERE / 'm431_window_component.py'),
                    ('test_m432_provider.py', HERE / 'test_m432_provider.py'), ('test_m430_timing.py', paths[0] / 'test_m430_timing.py')]:
        ast.parse(p.read_text(encoding='utf-8-sig'), feature_version=(3, 10))
        atomic(STAGE / name, p.read_bytes(), immutable=True)
    linux = lambda p: '/mnt/c/Users/30429/Desktop/TeLLMe_FPGA_2026/' + p.relative_to(ROOT).as_posix()
    entry = ('import sys,json\nfrom pathlib import Path\nassert sys.flags.isolated\n'
             + 'sys.path[:0]=' + repr([linux(STAGE)] + [linux(p) for p in paths]) + '\n'
             + 'import torch\ntorch.set_num_threads(1)\nfrom test_m432_provider import component\n'
             + "print('M432_PROVIDER_COMPONENT='+json.dumps(component(Path('/mnt/c/Users/30429/Desktop/TeLLMe_FPGA_2026'),Path(" + repr(linux(STAGE)) + ')),sort_keys=True),flush=True)\n')
    atomic(STAGE / 'entry.py', entry.encode('utf-8'), immutable=True)
    receipt = dict(status='M432_ACTUAL_PROVIDER_COMPONENT_STAGE_PREPARED', reused_paths=[p.relative_to(ROOT).as_posix() for p in paths],
                   stage_sha256={p.name: sha(p) for p in STAGE.iterdir()}, board_run=False, fake_DMA_explicit=True)
    atomic(STAGE.parent / 'STAGE.json', encoded(receipt), immutable=True)
    print('M432_COMPONENT_STAGE_READY')


def component():
    folder = ROOT / 'tmp/m43201/component'
    if folder.exists():
        raise RuntimeError('Original component receipt exists')
    cp = subprocess.run(['wsl.exe', '-d', 'Ubuntu-24.04', '--', '/home/lyy/projects/qwen_baseline/.venv/bin/python', '-I', '-B',
                         '/mnt/c/Users/30429/Desktop/TeLLMe_FPGA_2026/tmp/m43201/component_stage/entry.py'], capture_output=True, timeout=210)
    atomic(folder / 'stdout.bin', cp.stdout, immutable=True)
    atomic(folder / 'stderr.bin', cp.stderr, immutable=True)
    metadata = dict(return_code=cp.returncode, stdout_sha256=sha(folder / 'stdout.bin'), stderr_sha256=sha(folder / 'stderr.bin'))
    if cp.returncode:
        out = BASE / 'runs/M432-provider-component-failure-01/RESULT.json'
        atomic(out, encoded(dict(status='FAIL_M432_ISOLATED_PROVIDER_COMPONENT', receipt=metadata, board_run=False)), immutable=True)
        sync('latest_m432_provider_component_failure', dict(status='FAIL_M432_ISOLATED_PROVIDER_COMPONENT', result=out.relative_to(ROOT).as_posix(), sha256=sha(out)),
             f'## M432 隔离provider组件拒绝（2026-10-07）\n\nSHA {sha(out)}；原stdout/stderr与rc保留，0板端/模型/Overlay/DMA/PL。仅本组件级调查，不上传或扩大数值/性能。')
        raise RuntimeError('Isolated provider failed; inspect saved original stderr')
    rows = [x.split('=', 1)[1] for x in cp.stdout.decode('utf-8').splitlines() if x.startswith('M432_PROVIDER_COMPONENT=')]
    if len(rows) != 1:
        raise RuntimeError('Unique actual provider receipt required')
    c = json.loads(rows[0])
    if not all(c[k] for k in ('complete286_input_output_packets_and24_boundaries_exact', 'one_live_layer_scope', 'static_cache_invalidated',
                             'successful_disposal', 'active_second_layer_timeout_preserves_original_owner_and_restores_bindings')) or c['stages'] != 22 or c['original_array_bytes'] != 33484832:
        raise RuntimeError('Complete fixture evidence required')
    record = dict(status='PASS_M432_ACTUAL_ISOLATED_PROVIDER_FIXTURE_ONLY', component=c, receipt=metadata,
                  stage_sha256={p.name: sha(p) for p in STAGE.iterdir()}, manifest_sha256=sha(PKG / 'PACKAGE_MANIFEST.json'),
                  board_run=False, numerical_pass=False, performance_pass=False, temperature_measurement_enabled=False)
    out = BASE / 'runs/M432-provider-component-01/RESULT.json'
    atomic(out, encoded(record), immutable=True)
    sync('latest_m432_provider_component', dict(status=record['status'], result=out.relative_to(ROOT).as_posix(), sha256=sha(out), manifest_sha256=record['manifest_sha256']),
         f'## M432 实际完整请求视觉provider隔离组件（2026-10-07）\n\nSHA {sha(out)}；真实冻结24包装/encoder/M207及binding，明确窄MLP权重/Attention和fake DMA。实际provider原版/候选调用、286完整packet/wire及24边界、22暂存、原七数组33484832B身份、单活动层、静态缓存失效/成功dispose及第二层活动timeout保留原owner并恢复hooks通过。0上板/完整runtime容量/真实模型质量或性能；待资源前来源负例、递归依赖、完整实际export→host/控制门禁。')
    print('M432_PROVIDER_COMPONENT_SYNC', sha(out))


if __name__ == '__main__':
    {'prepare': prepare, 'component': component}[sys.argv[1]]()
