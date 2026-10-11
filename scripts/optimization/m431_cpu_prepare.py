"""Freeze the isolated CPU-only borrowed-DMA component packet."""
import ast
import json
from m351_workflow import ROOT, BASE, HERE, atomic, encoded, sha, sync

PKG = BASE / 'candidates/M431-borrowed-late11-CPU-01'


def main():
    if PKG.exists():
        raise RuntimeError('Immutable packet exists')
    board = json.loads((ROOT / 'deployment/mage_vl4b/BOARD_GATE_RESULT.json').read_bytes())
    e = board['latest_m430_complete_visual_closure']
    assert sha(ROOT / e['result']) == e['sha256'] and e['performance_pass']
    old = BASE / 'candidates/M429-isolated-bootstrap-03'
    m430 = BASE / 'candidates/M430-late11-visual-warm-02'
    previous_plan = json.loads((m430 / 'PLAN.json').read_bytes())
    parent = (old / 'm429_bootstrap.py').read_text(encoding='utf-8')
    parent = parent.replace('/home/ubuntu/m429_isolated_bootstrap_result_01', '/home/ubuntu/m431_borrowed_cpu_result_01')
    parent = parent.replace('m429_component_entry.py', 'm431_component_entry.py').replace('M429', 'M431')
    parent = parent.replace("        r['original_child_files']=[owned(Path('/home/ubuntu/m429_late11_visual_numeric_01')/n) for n in ('component_stdout.bin','component_stderr.bin')]\n", '')
    old_check = "        if c['complete_wire_batches']!=286 or len(c['negative_checks'])!=20 or not c['restored'] or not c['fake_PL_submit'] or not c['no_DMA_or_Overlay']:raise RuntimeError('Actual CPU fixture incomplete')"
    assert parent.count(old_check) == 1
    parent = parent.replace(old_check, "        if c['window']['complete_batches']!=286 or c['window']['staged_windows']!=22 or not c['window']['fake_DMA_MMIO_policy_and_byte_content'] or len(c['negative']['negative_checks'])!=15 or not c['negative']['timeout_preserves_original_owner']:raise RuntimeError('Borrowed CPU fixture incomplete')")
    parent = parent.replace("        root=Path(plan['release']);source=", "        numerical_path=Path(plan['visual_result_path'])\n        if digest(numerical_path)!=plan['visual_result_sha256']:raise RuntimeError('Completed visual source differs')\n        prior=json.loads(numerical_path.read_bytes())\n        if prior['status']!='PASS_M430_COMPLETE_VISUAL_WARM_COLLECTED' or not prior['performance_pass'] or not prior['stable_restored']:raise RuntimeError('Visual net-benefit prerequisite rejected')\n        root=Path(plan['release']);source=")
    child = '''import sys,json,contextlib,io
from pathlib import Path
if not sys.flags.isolated:raise RuntimeError('Isolated CPU child required')
here=Path(__file__).resolve().parent
plan=json.loads((here/'PLAN.json').read_bytes())
sys.path[:0]=[str(here),plan['component_package']]+[x['directory'] for x in plan['reused_packages']]
from frozen_video_identity import RELEASE,module_paths
if RELEASE!=Path(sys.argv[1]) or str(RELEASE)!=plan['release']:raise RuntimeError('Frozen release differs')
paths=[str(x) for x in module_paths()]
if paths[0]!=str(RELEASE/'runtime_site'):raise RuntimeError('Frozen runtime bootstrap differs')
sys.path[:0]=paths
import torch,numpy as np
Path(torch.__file__).resolve().relative_to((RELEASE/'runtime_site').resolve())
Path(np.__file__).resolve().relative_to((RELEASE/'runtime_site').resolve())
torch.set_num_threads(1)
print('M431_BOOTSTRAP='+json.dumps(dict(isolated=True,release=str(RELEASE),module_paths=paths,torch_path=str(Path(torch.__file__).resolve()),torch_version=torch.__version__,numpy_path=str(Path(np.__file__).resolve()),numpy_version=np.__version__,threads=torch.get_num_threads())),flush=True)
from test_m431_borrowed_visual import main as negative
text=io.StringIO()
with contextlib.redirect_stdout(text):negative()
lines=[x.split('=',1)[1] for x in text.getvalue().splitlines() if x.startswith('M431_COMPONENT=')]
if len(lines)!=1:raise RuntimeError('Unique negative component required')
from m431_window_component import component
window=component(plan['geometry_references'],here.parent)
if any(x=='pynq' or x.startswith('pynq.') for x in sys.modules):raise RuntimeError('Unexpected PYNQ import')
print('M431_COMPONENT='+json.dumps(dict(window=window,negative=json.loads(lines[0]))),flush=True)
'''
    # Geometry-only reference retains every original start, shift and wire size.
    software = json.loads((BASE / 'runs/M427-half-software-board-01/BOARD_RESULT.json').read_bytes())
    references = next(x for x in software['ranges'] if x['name'] == 'late_13_23')['reference_batches']
    geometry = {i: {p: [{k: v for k, v in row.items() if k not in ('packet_sha256', 'raw_sha256')} for row in rows] for p, rows in parts.items()} for i, parts in references.items()}
    plan = dict(release=previous_plan['release'], component_package='/home/ubuntu/m430_late11_visual_warm_candidate_02',
                component_manifest_sha256=sha(m430 / 'PACKAGE_MANIFEST.json'), reused_packages=previous_plan['reused_packages'],
                geometry_references=geometry, visual_result_path='/home/ubuntu/m430_late11_visual_warm_01/BOARD_RESULT.json',
                visual_result_sha256=board['latest_m430_complete_visual_board']['sha256'], default_off=True,
                no_Overlay_model_or_FPGA=True, temperature_measurement_enabled=False)
    PKG.mkdir()
    for name in ('m431_borrowed_visual.py', 'm431_window_component.py', 'test_m431_borrowed_visual.py'):
        atomic(PKG / name, (HERE / name).read_bytes(), immutable=True)
    atomic(PKG / 'm431_cpu.py', parent.encode('utf-8'), immutable=True)
    atomic(PKG / 'm431_component_entry.py', child.encode('utf-8'), immutable=True)
    atomic(PKG / 'SOURCE_IDENTITIES.json', (m430 / 'SOURCE_IDENTITIES.json').read_bytes(), immutable=True)
    atomic(PKG / 'PLAN.json', encoded(plan), immutable=True)
    runner = (old / 'run_bootstrap.sh').read_text(encoding='utf-8').replace('./m429_bootstrap.py', './m431_cpu.py')
    atomic(PKG / 'run_cpu.sh', runner.encode('utf-8'), immutable=True)
    for p in PKG.glob('*.py'):
        ast.parse(p.read_text(encoding='utf-8'), feature_version=(3, 10))
    atomic(PKG / 'SHA256SUMS', ''.join(f'{sha(p)}  {p.name}\n' for p in sorted(PKG.iterdir())).encode('ascii'), immutable=True)
    files = sorted(PKG.iterdir())
    manifest = dict(file_count=len(files), total_bytes=sum(p.stat().st_size for p in files), files=[dict(path=p.name, bytes=p.stat().st_size, sha256=sha(p)) for p in files])
    atomic(PKG / 'PACKAGE_MANIFEST.json', encoded(manifest), immutable=True)
    result = dict(status='PREPARED_M431_ISOLATED_BORROWED_CPU_PACKET', manifest_sha256=sha(PKG / 'PACKAGE_MANIFEST.json'),
                  file_count=manifest['file_count'], total_bytes=manifest['total_bytes'], default_off=True,
                  full286_geometry_only_synthetic_DMA=True, lower_M430_manifest_sha256=plan['component_manifest_sha256'],
                  no_original35asset_rehash=True, source_identities=49, board_run=False, temperature_measurement_enabled=False,
                  next_step='Actual exporter/host PASS/FAIL and isolated component support before COM3 CPU-only run. Full request remains unexecuted.')
    out = BASE / 'runs/M431-borrowed-CPU-packet-preparation-01/RESULT.json'
    atomic(out, encoded(result), immutable=True)
    sync('latest_m431_borrowed_CPU_packet', dict(status=result['status'], result=out.relative_to(ROOT).as_posix(), sha256=sha(out), manifest_sha256=result['manifest_sha256']),
         f'## M431 借用DMA隔离CPU小包（2026-10-06）\n\nSHA {sha(out)}，manifest {result["manifest_sha256"]}，{manifest["file_count"]}载荷/{manifest["total_bytes"]}B。仅实际33MiB NumPy缓冲几何与明确fake DMA/MMIO，286批/22暂存及15拒绝；原M430和49源码同SHA前置，不读35大资产，不构造模型/Overlay/真实DMA/PL。待实际收集支持；未上板或完整请求数值/性能，不测温。')
    print('M431_CPU_PACKET_PREPARED', sha(out))


if __name__ == '__main__':
    main()
