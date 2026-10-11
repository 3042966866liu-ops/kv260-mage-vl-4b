"""Correct only synthetic fixture staging geometry; retain original failure and packet."""
import ast
import json
import subprocess
import sys
from m351_workflow import ROOT, BASE, HERE, atomic, encoded, sha, sync

STAGE = ROOT / 'tmp/m43202/component_stage'
OLD = ROOT / 'tmp/m43201/component_stage'
PKG = BASE / 'candidates/M432-late11-integrated-video-01'


def prepare():
    if STAGE.exists():
        raise RuntimeError('Immutable corrected component stage exists')
    STAGE.mkdir(parents=True)
    for p in OLD.iterdir():
        if p.is_file() and p.name not in ('test_m432_provider.py', 'entry.py'):
            atomic(STAGE / p.name, p.read_bytes(), immutable=True)
    source = (OLD / 'test_m432_provider.py').read_text(encoding='utf-8')
    anchor = "name = f'{i}_{part}_{port}'; (folder / name).write_bytes(data)\n                    rows.append(dict(relative_file=name, file_bytes=len(data), bytes=len(data), offset=0))"
    if source.count(anchor) != 1:
        raise RuntimeError('Exact fixture correction anchor differs')
    source = source.replace(anchor, "name = f'{i}_{part}_{port}'\n                    assert len(data) <= 557056\n                    payload = data + bytes(557056 - len(data))\n                    (folder / name).write_bytes(payload)\n                    rows.append(dict(relative_file=name, file_bytes=len(payload), bytes=len(payload), offset=0))")
    ast.parse(source, feature_version=(3, 10))
    atomic(STAGE / 'test_m432_provider.py', source.encode('utf-8'), immutable=True)
    entry = (OLD / 'entry.py').read_text(encoding='utf-8').replace('tmp/m43201/component_stage', 'tmp/m43202/component_stage')
    atomic(STAGE / 'entry.py', entry.encode('utf-8'), immutable=True)
    record = dict(status='M432_FIXTURE_GEOMETRY_REPAIR_PREPARED', original_failure_sha256=sha(BASE / 'runs/M432-provider-component-failure-01/RESULT.json'),
                  unchanged_provider_sha256=sha(PKG / 'm432_request_visual.py'),
                  reason='Narrow synthetic weights staged fewer bytes than the intentionally fixed production 22*4*557056 budget. Pad only owned fixture files to exact real stage sizes; oracle uses the same original narrow prefixes.',
                  production_packet_changed=False, board_run=False, numerical_or_performance_pass=False)
    out = BASE / 'runs/M432-provider-fixture-repair-01/RESULT.json'
    atomic(out, encoded(record), immutable=True)
    sync('latest_m432_provider_fixture_repair', dict(status=record['status'], result=out.relative_to(ROOT).as_posix(), sha256=sha(out)),
         f'## M432 独立fixture暂存几何修复准备（2026-10-07）\n\nSHA {sha(out)}；原拒绝为窄权重fixture暂存量小于实际固定49020928B，未上板。只补自有fixture至每端口557056B、保留oracle原窄权重前缀，实际provider/候选包同SHA不改，原失败/日志保留。只重试组件级，不放宽生产合同或执行模型。')
    print('M432_COMPONENT02_STAGE_READY')


def component():
    folder = ROOT / 'tmp/m43202/component'
    if folder.exists():
        raise RuntimeError('Original component receipt exists')
    cp = subprocess.run(['wsl.exe', '-d', 'Ubuntu-24.04', '--', '/home/lyy/projects/qwen_baseline/.venv/bin/python', '-I', '-B',
                         '/mnt/c/Users/30429/Desktop/TeLLMe_FPGA_2026/tmp/m43202/component_stage/entry.py'], capture_output=True, timeout=210)
    atomic(folder / 'stdout.bin', cp.stdout, immutable=True); atomic(folder / 'stderr.bin', cp.stderr, immutable=True)
    if cp.returncode:
        raise RuntimeError('Corrected isolated fixture failed; original receipts retained')
    lines = [x.split('=', 1)[1] for x in cp.stdout.decode('utf-8').splitlines() if x.startswith('M432_PROVIDER_COMPONENT=')]
    if len(lines) != 1:
        raise RuntimeError('Unique provider receipt required')
    c = json.loads(lines[0])
    if not all(c[k] for k in ('complete286_input_output_packets_and24_boundaries_exact', 'one_live_layer_scope', 'static_cache_invalidated',
                             'successful_disposal', 'active_second_layer_timeout_preserves_original_owner_and_restores_bindings')) or c['stages'] != 22 or c['original_array_bytes'] != 33484832:
        raise RuntimeError('Complete corrected fixture evidence required')
    record = dict(status='PASS_M432_ACTUAL_ISOLATED_PROVIDER_FIXTURE_ONLY', component=c, return_code=cp.returncode,
                  stdout_sha256=sha(folder / 'stdout.bin'), stderr_sha256=sha(folder / 'stderr.bin'),
                  stage_sha256={p.name: sha(p) for p in STAGE.iterdir()}, manifest_sha256=sha(PKG / 'PACKAGE_MANIFEST.json'),
                  fixture_expected_staging_bytes=49020928, original_failure_retained=True, production_packet_changed=False,
                  board_run=False, numerical_pass=False, performance_pass=False, temperature_measurement_enabled=False)
    out = BASE / 'runs/M432-provider-component-02/RESULT.json'; atomic(out, encoded(record), immutable=True)
    sync('latest_m432_provider_component', dict(status=record['status'], result=out.relative_to(ROOT).as_posix(), sha256=sha(out), manifest_sha256=record['manifest_sha256']),
         f'## M432 实际完整请求视觉provider隔离组件（2026-10-07）\n\nSHA {sha(out)}；实际provider与冻结24包装/encoder/M207/binding，明确窄权重/Attention/fake DMA；原版/候选、286完整packet/wire及24边界、22×四端口557056B真实暂存几何、原七数组33484832B身份、单活动层、缓存失效/dispose与第二层活动timeout保留原owner并恢复hooks通过。原fixture暂存量拒绝与日志保留，生产候选包未改。0上板/完整runtime容量/真实模型数值或性能；下一步资源前来源负例/递归依赖与实际收集控制配套。')
    print('M432_PROVIDER_COMPONENT_SYNC', sha(out))


if __name__ == '__main__':
    {'prepare': prepare, 'component': component}[sys.argv[1]]()
