"""Finish version02 clean packet; preserve review draft01 and all earlier evidence."""
import ast,json,subprocess,sys
from m351_workflow import ROOT,BASE,HERE,atomic,encoded,sha,sync
from m427_prepare import once
DRAFT=BASE/'candidates/M429-late11-visual-PL-numeric-01'
PKG=BASE/'candidates/M429-late11-visual-PL-numeric-02'

def main():
    plan=json.loads((DRAFT/'PLAN.json').read_bytes())
    lower=BASE/'candidates/M418-visual-linear-01'
    plan['hardware_closure_sha256']=sha(lower/'HARDWARE_CLOSURE.json')
    plan['board_case_sha256']=sha(lower/'BOARD_CASES.json')
    plan['main_DMA_sizes']=[557056]*4+[163856,524288,524288]
    plan['main_DMA_bytes']=sum(plan['main_DMA_sizes'])
    plan['expected_total_physical_transactions']=288
    gate=(DRAFT/'m429_gate.py').read_text(encoding='utf-8')
    gate=once(gate,"    result.update(transactions=[]", "    result.update(build_id='0x4D333537',transactions=[]")
    gate=gate.replace("result['physical_transactions_started']+len(result['transactions'])","result['physical_transactions_started']")
    gate=once(gate,"        # Acquire execution lock",'''        SavedWireCheck(accepted['reference_batches'],lambda *unused:None)
        lower_package=Path(plan['lower_directory'])
        if digest(lower_package/'HARDWARE_CLOSURE.json')!=plan['hardware_closure_sha256'] or digest(lower_package/'BOARD_CASES.json')!=plan['board_case_sha256']:raise RuntimeError('Reused hardware/ABI closure differs')
        closure=json.loads((lower_package/'HARDWARE_CLOSURE.json').read_bytes())
        if closure['status']!='PASS_ALL_NEW_CIRCUIT_PREREQUISITES' or closure['build_id']!='0x4D333537' or not closure['stable_rollback_intact'] or not closure['original_source_closure_unchanged']:raise RuntimeError('Reused numerical/header/RTL prerequisites rejected')
        result['hardware_closure_sha256']=plan['hardware_closure_sha256']
        import subprocess
        child=subprocess.run([sys.executable,'-I','-B',str(HERE/'m429_component_entry.py'),str(RELEASE)],capture_output=True,timeout=180)
        save(OUTPUT.parent/'component_stdout.bin',child.stdout);save(OUTPUT.parent/'component_stderr.bin',child.stderr)
        if child.returncode:raise RuntimeError('CPU-only frozen scope component rejected before Overlay')
        lines=[x.split('=',1)[1] for x in child.stdout.decode('utf-8').splitlines() if x.startswith('M429_COMPONENT=')]
        if len(lines)!=1:raise RuntimeError('Isolated component receipt differs')
        result['component']=json.loads(lines[0])
        if result['component']['complete_wire_batches']!=286 or not result['component']['restored'] or len(result['component']['negative_checks'])!=20:raise RuntimeError('Complete scope component required')
        result['CPU_component_before_Overlay']=True
        print('M429_CPU_COMPONENT_PASS_BEFORE_RESOURCES',flush=True)
        # Acquire execution lock''')
    gate=once(gate,"        host,initial=actual_host(RELEASE)","        for index in SELECTED:load_case(index)\n        host,initial=actual_host(RELEASE)")
    gate=once(gate,"    except BaseException as error:result['errors'].append(dict(type=type(error).__name__,message=str(error),traceback=traceback.format_exc()))",'''    except BaseException as error:
        result['errors'].append(dict(type=type(error).__name__,message=str(error),traceback=traceback.format_exc()))
        if owner is not None and owner.kernel is not None:
            result['failure_snapshot_before_cleanup']=owner.base.transaction_snapshot(owner.kernel,owner.dma)
            print('M429_FAILURE_STATE '+json.dumps(dict(snapshot=result['failure_snapshot_before_cleanup'],transaction=result.get('active_transaction'),physical_started=result['physical_transactions_started'])),flush=True)''')
    gate=gate.replace('"""One original and one all22 FP32 MLP exact-software visual quality screen.\n\nNo Overlay, DMA, model language forward or performance adjudication. Preserve\ncomplete features for a subsequent unchanged-language task consistency gate.\n"""','"""Default-off complete late11 visual PL numerical gate; one visual, no language.\n\nSaved exact software wire/boundary/features are reused without visual replay.\nNo performance adjudication; retain owner on unsafe DMA and restore stable.\n"""')
    # Actual owner class is byte-identical in AST, as are zero and restore lifecycles.
    old=ast.parse((BASE/'candidates/M420-layers12-13-full-visual-02/m420_gate.py').read_text(encoding='utf-8'));new=ast.parse(gate)
    def node(tree,name,typ):return next(n for n in ast.walk(tree) if isinstance(n,typ) and n.name==name)
    unchanged={}
    for name,typ in [('WorkOwner',ast.ClassDef),('zero',ast.FunctionDef),('restore',ast.FunctionDef)]:
        assert ast.dump(node(old,name,typ),include_attributes=False)==ast.dump(node(new,name,typ),include_attributes=False)
        unchanged[name]='identical_AST_to_actual_passed_M420'
    PKG.mkdir(parents=True,exist_ok=False)
    for p in DRAFT.iterdir():
        if p.name not in ('m429_gate.py','PLAN.json'):atomic(PKG/p.name,p.read_bytes(),immutable=True)
    atomic(PKG/'m429_gate.py',gate.encode('utf-8'),immutable=True);atomic(PKG/'PLAN.json',encoded(plan),immutable=True)
    atomic(PKG/'test_m429_range.py',(ROOT/'tmp/m42901/component_stage/test_m429_range.py').read_bytes(),immutable=True)
    entry='''import sys,json
from pathlib import Path
assert sys.flags.isolated
here=Path(__file__).resolve().parent
plan=json.loads((here/'PLAN.json').read_bytes())
sys.path[:0]=[str(here)]+[x['directory'] for x in plan['reused_packages']]
import torch
torch.set_num_threads(1)
from test_m429_range import component
value=component(Path(sys.argv[1]))
assert not any(x=='pynq' or x.startswith('pynq.') for x in sys.modules)
print('M429_COMPONENT='+json.dumps(value),flush=True)
'''
    atomic(PKG/'m429_component_entry.py',entry.encode('utf-8'),immutable=True)
    exporter=(BASE/'candidates/M427-saved-export-recovery-01/m427_export_saved02.py').read_text(encoding='utf-8').replace('M427','M429').replace('/home/ubuntu/m427_half_ranges_software_01/','/home/ubuntu/m429_late11_visual_numeric_01/').replace('CPU-only-two-half-visual-MLP-screen','late11-complete-visual-PL-numerical')
    assert "r['gate_level']!='late11-complete-visual-PL-numerical'" in exporter
    atomic(PKG/'m429_export.py',exporter.encode('utf-8'),immutable=True)
    runner='''#!/usr/bin/env bash
set -euo pipefail
[[ $EUID == 0 ]] || exit 65
cd "$(dirname "${BASH_SOURCE[0]}")"
task_manifest=${1:?manifest}
task_mode=${2:?Run or Collect}
task_python=/usr/local/share/pynq-venv/bin/python
export PYTHONDONTWRITEBYTECODE=1
export XILINX_XRT=/usr TMPDIR=/dev/shm
export PATH=/usr/local/share/pynq-venv/bin:$PATH
printf '%s  PACKAGE_MANIFEST.json\n' "$task_manifest" | sha256sum -c -
sha256sum -c SHA256SUMS
if [[ $task_mode == Collect ]]; then exec "$task_python" -B ./m429_export.py; fi
[[ $task_mode == Run && ${M429_ENABLE_PL_NUMERICAL:-0} == 1 ]] || exit 66
[[ ! -e /home/ubuntu/m429_late11_visual_numeric_01 ]] || exit 67
set +e
"$task_python" -B ./m429_gate.py "$task_manifest" --enable-PL-numerical
task_gate_rc=$?
"$task_python" -B ./m429_export.py
task_export_rc=$?
set -e
echo "M429_DONE gate_rc=$task_gate_rc export_rc=$task_export_rc"
if [[ $task_gate_rc != 0 ]]; then exit "$task_gate_rc"; fi
exit "$task_export_rc"
'''
    atomic(PKG/'run_m429.sh',runner.encode('utf-8'),immutable=True)
    for p in PKG.glob('*.py'):ast.parse(p.read_text(encoding='utf-8'),feature_version=(3,10))
    # Staged recursive Python dependencies must resolve in this packet or one exact reused packet.
    reuse=[BASE/'candidates'/n for n in ('M417-layer13-saved-reference-02','M418-visual-linear-01','M409-mlp-exact-software-01','M410-visual-linear-01','M414-layer12-full-visual-01')]
    # Manifest mapping uses the actual directories from the frozen parent plan.
    all_manifests=[]
    for remote in plan['reused_packages']:
        matches=[]
        for manifest in (BASE/'candidates').glob('*/PACKAGE_MANIFEST.json'):
            if sha(manifest)==remote['manifest_sha256']:matches.append(manifest.parent)
        if len(matches)!=1:raise RuntimeError('Exact reused local packet identity ambiguous')
        reuse_folder=matches[0]
        for row in json.loads((reuse_folder/'PACKAGE_MANIFEST.json').read_bytes())['files']:assert sha(reuse_folder/row['path'])==row['sha256']
        all_manifests.append(reuse_folder)
    modules={p.stem:p for folder in [PKG]+all_manifests for p in folder.glob('*.py')}
    # First-resolution order mirrors sys.path (new packet precedes reused frozen modules).
    modules={}
    for folder in [PKG]+all_manifests:
        for p in folder.glob('*.py'):modules.setdefault(p.stem,p)
    seen=set();missing=[]
    def closure(name):
        if name in seen:return
        seen.add(name);tree=ast.parse(modules[name].read_text(encoding='utf-8-sig'))
        imports=[a.name.split('.')[0] for n in ast.walk(tree) if isinstance(n,ast.Import) for a in n.names]+[(n.module or '').split('.')[0] for n in ast.walk(tree) if isinstance(n,ast.ImportFrom)]
        for dependency in imports:
            if dependency in modules:closure(dependency)
            elif dependency.startswith('m') and dependency[:2]=='m' and len(dependency)>1 and dependency[1].isdigit():missing.append((name,dependency))
    for name in ('m429_gate','m429_component_entry','m429_export'):closure(name)
    if missing:raise RuntimeError('Missing staged recursive imports '+repr(missing))
    atomic(PKG/'DEPENDENCY_CLOSURE.json',encoded(dict(recursive_module_count=len(seen),missing=missing,sources={name:sha(modules[name]) for name in sorted(seen)})),immutable=True)
    atomic(PKG/'SHA256SUMS',''.join(f'{sha(p)}  {p.name}\n' for p in sorted(PKG.iterdir())).encode('ascii'),immutable=True)
    files=sorted(PKG.iterdir());manifest=dict(file_count=len(files),total_bytes=sum(p.stat().st_size for p in files),files=[dict(path=p.name,bytes=p.stat().st_size,sha256=sha(p)) for p in files]);atomic(PKG/'PACKAGE_MANIFEST.json',encoded(manifest),immutable=True)
    out=BASE/'runs/M429-final-packet-02/RESULT.json'
    record=dict(status='M429_FINAL_NUMERICAL_PACKET_SUPPORT_PENDING',manifest_sha256=sha(PKG/'PACKAGE_MANIFEST.json'),file_count=manifest['file_count'],total_bytes=manifest['total_bytes'],
        unchanged_owner_lifecycle=unchanged,recursive_import_modules=len(seen),missing=missing,main_DMA_bytes=plan['main_DMA_bytes'],expected_total_physical_transactions=288,
        draft_corrections=['Metadata main DMA bytes recalculated from exact seven sizes; draft01 mistyped total was not executed.',
                           'Count lower.Owner minimal transactions once; original counter already increments them.',
                           'Validate saved wire/reused hardware and actual CPU-only component before Overlay.'],
        board_run=False,hardware_visual_numerics_pass=False,performance_pass=False,temperature_measurement_enabled=False)
    atomic(out,encoded(record),immutable=True)
    sync('latest_m429_final_packet',dict(status=record['status'],result=out.relative_to(ROOT).as_posix(),sha256=sha(out),manifest_sha256=record['manifest_sha256']),
        f'## M429 后11层视觉PL数值02包（2026-10-06）\n\nSHA {sha(out)}；manifest {record["manifest_sha256"]}、{manifest["file_count"]}文件/{manifest["total_bytes"]}B，递归imports {len(seen)}、missing0。实际M420 WorkOwner/zero/restore AST相同；七main DMA {plan["main_DMA_bytes"]}B，286MLP+2合法最小事务共288；修正未执行draft01统计元数据，原稿保留。真实CPU组件、保存参考与硬件closure必须在Overlay之前通过。待真实export→hostdecode、故障、bash/control自测；无上板或性能证据。')
    print('M429_FINAL_PACKET_SYNC',sha(out),record['manifest_sha256'])

if __name__=='__main__':main()
