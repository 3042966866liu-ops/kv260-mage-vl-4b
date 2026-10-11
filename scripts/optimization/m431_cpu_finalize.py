"""Finalize CPU fixture paths, preserving the unexecuted first draft."""
import ast
import json
import subprocess
from m351_workflow import ROOT, BASE, HERE, atomic, encoded, sha, sync

PKG = BASE / 'candidates/M431-borrowed-late11-CPU-02'


def prepare():
    old = BASE / 'candidates/M431-borrowed-late11-CPU-01'
    if PKG.exists():
        raise RuntimeError('Immutable final packet exists')
    PKG.mkdir()
    for row in json.loads((old / 'PACKAGE_MANIFEST.json').read_bytes())['files']:
        if row['path'] != 'SHA256SUMS':
            p = old / row['path']
            assert sha(p) == row['sha256']
            raw = p.read_bytes()
            if p.name == 'test_m431_borrowed_visual.py':
                text = raw.decode('utf-8')
                before = "dir=Path(__file__).resolve().parents[2]/'tmp'"
                after = 'dir=Path(__file__).resolve().parent.parent'
                assert text.count(before) == 1
                text = text.replace(before, after)
                raw = text.encode('utf-8')
            atomic(PKG / p.name, raw, immutable=True)
    atomic(PKG / 'SHA256SUMS', ''.join(f'{sha(p)}  {p.name}\n' for p in sorted(PKG.iterdir())).encode('ascii'), immutable=True)
    files = sorted(PKG.iterdir())
    manifest = dict(file_count=len(files), total_bytes=sum(p.stat().st_size for p in files), files=[dict(path=p.name, bytes=p.stat().st_size, sha256=sha(p)) for p in files])
    atomic(PKG / 'PACKAGE_MANIFEST.json', encoded(manifest), immutable=True)
    stage = ROOT / 'tmp/m43101/component_stage'
    stage.mkdir(parents=True, exist_ok=False)
    for p in PKG.glob('*.py'):
        ast.parse(p.read_text(encoding='utf-8'), feature_version=(3, 10))
        atomic(stage / p.name, p.read_bytes(), immutable=True)
    atomic(stage / 'PLAN.json', (PKG / 'PLAN.json').read_bytes(), immutable=True)
    entry = '''import sys,json,contextlib,io
from pathlib import Path
if not sys.flags.isolated:raise RuntimeError('Isolation required')
root=Path('/mnt/c/Users/30429/Desktop/TeLLMe_FPGA_2026')
stage=root/'tmp/m43101/component_stage'
sys.path[:0]=[str(stage),str(root/'deployment/mage_vl4b/optimization_v1/candidates/M430-late11-visual-warm-02'),str(root/'deployment/mage_vl4b/optimization_v1/candidates/M417-layer13-saved-reference-02')]
from test_m431_borrowed_visual import main
capture=io.StringIO()
with contextlib.redirect_stdout(capture):main()
lines=[x.split('=',1)[1] for x in capture.getvalue().splitlines() if x.startswith('M431_COMPONENT=')]
if len(lines)!=1:raise RuntimeError('Unique actual negative receipt required')
from m431_window_component import component
plan=json.loads((stage/'PLAN.json').read_bytes())
print('M431_COMPONENT='+json.dumps(dict(window=component(plan['geometry_references'],stage.parent),negative=json.loads(lines[0]))),flush=True)
'''
    atomic(stage / 'entry.py', entry.encode('utf-8'), immutable=True)
    print('M431_CPU_FINAL_STAGE_READY')


def component():
    folder = ROOT / 'tmp/m43101/component'
    if folder.exists():
        raise RuntimeError('Saved component logs exist')
    cp = subprocess.run(['wsl.exe', '-d', 'Ubuntu-24.04', '--', '/home/lyy/projects/qwen_baseline/.venv/bin/python', '-I', '-B',
                         '/mnt/c/Users/30429/Desktop/TeLLMe_FPGA_2026/tmp/m43101/component_stage/entry.py'], capture_output=True, timeout=60)
    atomic(folder / 'stdout.bin', cp.stdout, immutable=True)
    atomic(folder / 'stderr.bin', cp.stderr, immutable=True)
    if cp.returncode:
        raise RuntimeError('Isolated actual packet fixture rejected; preserve original logs')
    lines = [x.split('=', 1)[1] for x in cp.stdout.decode('utf-8').splitlines() if x.startswith('M431_COMPONENT=')]
    assert len(lines) == 1
    c = json.loads(lines[0])
    assert c['window']['complete_batches'] == 286 and c['window']['staged_windows'] == 22 and len(c['negative']['negative_checks']) == 15
    result = dict(status='PASS_M431_ISOLATED_PACKET_CPU_FIXTURE_ONLY', component=c, manifest_sha256=sha(PKG / 'PACKAGE_MANIFEST.json'),
                  original_draft01_preserved=True, draft01_not_uploaded=True,
                  draft01_issue='Development-only parents[2]/tmp fixture path would be /home/tmp after transfer; changed only fixture storage to package parent before any board work.',
                  stage_sha256={p.name: sha(p) for p in (ROOT / 'tmp/m43101/component_stage').iterdir()},
                  stdout_sha256=sha(folder / 'stdout.bin'), stderr_sha256=sha(folder / 'stderr.bin'),
                  real_model_or_FPGA_execution=False, actual_full_request_numerics_pass=False, performance_pass=False, temperature_measurement_enabled=False)
    out = BASE / 'runs/M431-isolated-packet-component-01/RESULT.json'
    atomic(out, encoded(result), immutable=True)
    sync('latest_m431_isolated_packet_component', dict(status=result['status'], result=out.relative_to(ROOT).as_posix(), sha256=sha(out), manifest_sha256=result['manifest_sha256']),
         f'## M431 实际隔离包CPU组件（2026-10-06）\n\nSHA {sha(out)}。实际02载荷以-I独立staging执行，原33MiB七缓冲几何、286批/22暂存/输出143+143交替、15拒绝与超时保留通过；DMA/MMIO/数据明确fake，非实际容量或数值证明。01未上传稿的开发路径已在上板前修正，原稿保留，仅自有fixture目录变化。待实际export→host/control支持后COM3 CPU小门禁；不测温。')
    print('M431_PACKET_COMPONENT_SYNC', sha(out))


if __name__ == '__main__':
    import sys
    if sys.argv[1:] == ['prepare']:
        prepare()
    elif sys.argv[1:] == ['component']:
        component()
    else:
        raise SystemExit('prepare | component')
