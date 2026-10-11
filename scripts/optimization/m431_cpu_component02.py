"""Use every frozen reused package path in the isolated offline fixture."""
import json
import subprocess
from m351_workflow import ROOT, BASE, atomic, encoded, sha, sync
from m431_cpu_finalize import PKG


def prepare():
    old = ROOT / 'tmp/m43101/component'
    assert b"ModuleNotFoundError: No module named 'board_safety'" in (old / 'stderr.bin').read_bytes()
    failure = dict(status='REJECTED_M431_OFFLINE_STAGE_MISSING_REUSED_PATH', stdout_sha256=sha(old / 'stdout.bin'),
                   stderr_sha256=sha(old / 'stderr.bin'), module='board_safety',
                   issue='Offline entry listed only M430 and M417, omitting other PLAN reused paths. Frozen packet PLAN includes the verified M418 dependency.',
                   board_upload=False, Overlay_loads=0, hardware_transactions=0, temperature_measurement_enabled=False)
    out = BASE / 'runs/M431-isolated-stage-rejection-01/RESULT.json'
    atomic(out, encoded(failure), immutable=True)
    sync('latest_m431_isolated_stage_rejection', dict(status=failure['status'], result=out.relative_to(ROOT).as_posix(), sha256=sha(out)),
         f'## M431 离线隔离暂存依赖路径拒绝（2026-10-06）\n\nSHA {sha(out)}。-I入口漏PLAN中的M418路径，board_safety不可解析，0板端/模型/Overlay/事务。原stderr/raw保留；包PLAN已有同SHA依赖，不是算法/资源问题。新暂存按全部已核manifest路径解析，不修改算法或原包，不测温。')
    plan = json.loads((PKG / 'PLAN.json').read_bytes())
    paths = [PKG]
    rows = [dict(manifest_sha256=plan['component_manifest_sha256'])] + plan['reused_packages']
    for row in rows:
        matches = [p.parent for p in (BASE / 'candidates').glob('*/PACKAGE_MANIFEST.json') if sha(p) == row['manifest_sha256']]
        assert len(matches) == 1
        folder = matches[0]
        for file in json.loads((folder / 'PACKAGE_MANIFEST.json').read_bytes())['files']:
            assert sha(folder / file['path']) == file['sha256']
        paths.append(folder)
    stage = ROOT / 'tmp/m43102/component_stage'
    stage.mkdir(parents=True, exist_ok=False)
    for p in PKG.glob('*.py'):
        atomic(stage / p.name, p.read_bytes(), immutable=True)
    atomic(stage / 'PLAN.json', (PKG / 'PLAN.json').read_bytes(), immutable=True)
    local = [str(p.relative_to(ROOT)).replace('\\', '/') for p in paths[1:]]
    entry = (ROOT / 'tmp/m43101/component_stage/entry.py').read_text(encoding='utf-8')
    entry = entry.replace("tmp/m43101/component_stage", "tmp/m43102/component_stage")
    oldline = "sys.path[:0]=[str(stage),str(root/'deployment/mage_vl4b/optimization_v1/candidates/M430-late11-visual-warm-02'),str(root/'deployment/mage_vl4b/optimization_v1/candidates/M417-layer13-saved-reference-02')]"
    assert entry.count(oldline) == 1
    entry = entry.replace(oldline, 'sys.path[:0]=[str(stage)]+[str(root/p) for p in '+repr(local)+']')
    atomic(stage / 'entry.py', entry.encode('utf-8'), immutable=True)
    print('M431_COMPLETE_REUSED_STAGE_READY')


def run():
    folder = ROOT / 'tmp/m43102/component'
    assert not folder.exists()
    cp = subprocess.run(['wsl.exe', '-d', 'Ubuntu-24.04', '--', '/home/lyy/projects/qwen_baseline/.venv/bin/python', '-I', '-B',
                         '/mnt/c/Users/30429/Desktop/TeLLMe_FPGA_2026/tmp/m43102/component_stage/entry.py'], capture_output=True, timeout=60)
    atomic(folder / 'stdout.bin', cp.stdout, immutable=True)
    atomic(folder / 'stderr.bin', cp.stderr, immutable=True)
    if cp.returncode:
        raise RuntimeError('Full actual reuse-path fixture rejected; preserve logs')
    lines = [x.split('=', 1)[1] for x in cp.stdout.decode('utf-8').splitlines() if x.startswith('M431_COMPONENT=')]
    assert len(lines) == 1
    c = json.loads(lines[0])
    assert c['window']['complete_batches'] == 286 and c['window']['staged_windows'] == 22 and len(c['negative']['negative_checks']) == 15
    result = dict(status='PASS_M431_ISOLATED_PACKET_CPU_FIXTURE_ONLY', component=c, manifest_sha256=sha(PKG / 'PACKAGE_MANIFEST.json'),
                  explicit_fake_DMA_MMIO_and_data=True, all_actual_reused_paths_checked=True, original_stage_failure_preserved=True,
                  stage_sha256={p.name: sha(p) for p in (ROOT / 'tmp/m43102/component_stage').iterdir()},
                  stdout_sha256=sha(folder / 'stdout.bin'), stderr_sha256=sha(folder / 'stderr.bin'),
                  board_run=False, performance_pass=False, temperature_measurement_enabled=False)
    out = BASE / 'runs/M431-isolated-packet-component-02/RESULT.json'
    atomic(out, encoded(result), immutable=True)
    sync('latest_m431_isolated_packet_component', dict(status=result['status'], result=out.relative_to(ROOT).as_posix(), sha256=sha(out), manifest_sha256=result['manifest_sha256']),
         f'## M431 完整复用路径隔离组件（2026-10-06）\n\nSHA {sha(out)}，真实02载荷-I暂存与全部核SHA的旧包路径通过，286批/22×四端口557056B暂存、143+143输出交替、15拒绝/超时保留/缓存失效；7数组33484832B，fake DMA/MMIO/数据明确。未上板或完整请求容量/数值/性能；原暂存失败保留，不测温。下一步实际export/host/control支持后板端CPU组件。')
    print('M431_FULL_COMPONENT_SYNC', sha(out))


if __name__ == '__main__':
    import sys
    if sys.argv[1:] == ['prepare']:
        prepare()
    elif sys.argv[1:] == ['run']:
        run()
    else:
        raise SystemExit('prepare | run')
