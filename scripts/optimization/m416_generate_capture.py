"""Freeze one layer13 PS capture from the proven native-rank layer12 entry."""
import ast, json, re, subprocess, sys
from m351_workflow import ROOT, BASE, HERE, atomic, encoded, sha, sync

OLD = BASE/'candidates/M408-local-MLP-A8-capture-04'
PKG = BASE/'candidates/M416-layer13-PS-capture-01'

def replace(text, old, new):
    if text.count(old)!=1: raise RuntimeError('Exact derivative rejected: '+old)
    return text.replace(old,new)

def stage_helpers():
    target=re.sub(r'(?<!\d)12(?!\d)','13',(OLD/'m408_target03.py').read_text(encoding='utf-8'))
    atomic(HERE/'m416_target13.py',target.encode('utf-8'),immutable=True)
    fixture=(OLD/'m408_target_component04.py').read_text(encoding='utf-8')
    fixture=fixture.replace('from m408_target03 import','from m416_target13 import')
    fixture=re.sub(r'(?<!\d)12(?!\d)','13',fixture)
    fixture=replace(fixture,'[None]*11','[None]*10')
    atomic(HERE/'m416_target_component.py',fixture.encode('utf-8'),immutable=True)
    audit=(HERE/'m408_constructor_audit.py').read_text(encoding='utf-8')
    audit=audit.replace('from m408_target03 import','from m416_target13 import')
    audit=audit.replace('M408-local-MLP-A8-capture-02','M408-local-MLP-A8-capture-04')
    audit=re.sub(r'(?<!\d)12(?!\d)','13',audit).replace('M408_CONSTRUCTOR_JSON','M416_CONSTRUCTOR_JSON')
    atomic(HERE/'m416_constructor_audit.py',audit.encode('utf-8'),immutable=True)

def main():
    recovery={n:dict(bytes=(ROOT/n).stat().st_size,sha256=sha(ROOT/n),
                    lines=len((ROOT/n).read_text(encoding='utf-8-sig').splitlines()))
              for n in ('CURRENT_STATE.md','docsMILESTONES.md','DEPLOYMENT_OPERATION_MISTAKES_REVIEW.md')}
    b=json.loads((ROOT/'deployment/mage_vl4b/BOARD_GATE_RESULT.json').read_bytes())
    priors={k:b[k] for k in ('latest_m416_bounded_expansion_plan','latest_m415_saved_feature_language_closure','latest_m408_local_mlp_board04')}
    for row in priors.values():
        assert sha(ROOT/row['result'])==row['sha256']
        assert all(row['sha256'] in (ROOT/n).read_text(encoding='utf-8-sig') for n in ('CURRENT_STATE.md','docsMILESTONES.md'))
    assert priors['latest_m415_saved_feature_language_closure']['decision_consistency_pass']
    oldm=json.loads((OLD/'PACKAGE_MANIFEST.json').read_bytes())
    for row in oldm['files']: assert sha(OLD/row['path'])==row['sha256']
    stage_helpers()
    folder=ROOT/'tmp/m41601';folder.mkdir(parents=True,exist_ok=True)
    audit=folder/'constructor.json'
    run=subprocess.run(['wsl.exe','-d','Ubuntu-24.04','--','/home/lyy/projects/qwen_baseline/.venv/bin/python','-B',
        '/mnt/c/Users/30429/Desktop/TeLLMe_FPGA_2026/scripts/optimization/m416_constructor_audit.py',
        '/mnt/c/Users/30429/Desktop/TeLLMe_FPGA_2026/tmp/m41601/constructor.json'],capture_output=True)
    atomic(folder/'constructor_stdout.txt',run.stdout,immutable=True)
    atomic(folder/'constructor_stderr.txt',run.stderr,immutable=True)
    if run.returncode: raise RuntimeError(run.stderr.decode('utf-8',errors='replace')[-4000:])
    ctor=json.loads(audit.read_bytes());assert ctor['owner_collected'] and ctor['model_forward_calls']==0
    assert ctor['topology']['selected_layer']==13
    gate=(OLD/'m408_gate.py').read_text(encoding='utf-8')
    gate=gate.replace('M408','M416').replace('m408_mlp_capture_04','m416_layer13_capture_01')
    gate=gate.replace('from m408_target03 import','from m416_target13 import')
    gate=replace(gate,'from m408_target_component04 import from_sources','from m414_entry import run_component, retain_reference')
    gate=replace(gate,'selected_layer=12','selected_layer=13')
    gate=replace(gate,"        result['component'] = component(torch, contract_runtime.quantize_t32, M207FP32GemmW4Linear)\n        result['component_pass'] = True\n        print('M416_SMALL_WRAPPER_FIXTURE_BEGIN',flush=True)\n        result['target_component'] = from_sources(torch,RELEASE)\n        print('M416_SMALL_WRAPPER_FIXTURE_END',flush=True)",
        "        checked_component, result['component_isolation'] = run_component(RELEASE,OUTPUT.parent,HERE/'m416_component_entry.py')\n        result['component'] = checked_component['component']\n        result['target_component'] = checked_component['target_component']\n        result['component_pass'] = True")
    gate=replace(gate,"        if result['visual'] != expected['visual']: raise RuntimeError('Original visual reference differs')",
        "        if result['visual'] != expected['visual']:\n            result['failed_reference_files'] = retain_reference(OUTPUT.parent,visual,captured.values)\n            raise RuntimeError('Original visual reference differs')")
    gate=replace(gate,'time.sleep(.025)','time.sleep(.16)')
    gate=replace(gate,'    raw = OUTPUT.read_bytes()','    raw = OUTPUT.read_bytes()\n    if not 0 < len(raw) <= 1<<20: raise RuntimeError(\'Bounded saved result required\')')
    ast.parse(gate,feature_version=(3,10))
    if PKG.exists(): raise RuntimeError('Immutable package exists')
    PKG.mkdir()
    excluded={'m408_gate.py','m408_target03.py','m408_target_component04.py','EXPECTED_TARGET.json','run_m408_capture.sh','SHA256SUMS'}
    for row in oldm['files']:
        if row['path'] not in excluded: atomic(PKG/row['path'],(OLD/row['path']).read_bytes(),immutable=True)
    atomic(PKG/'m416_gate.py',gate.encode('utf-8'),immutable=True)
    atomic(PKG/'EXPECTED_TARGET.json',encoded(dict(topology=ctor['topology'],matrices=ctor['matrices'])),immutable=True)
    for name in ('m416_target13.py','m416_target_component.py','m414_entry.py','m414_quality.py'):
        atomic(PKG/name,(HERE/name).read_bytes(),immutable=True)
    child='''"""Isolated real Torch primitive/wrapper fixtures; no model or PYNQ."""
import json,sys
from pathlib import Path
from m408_component04 import component
from m416_target_component import from_sources
from frozen_video_identity import module_paths
sys.path[:0]=[str(p) for p in module_paths() if p.name!='runtime_site']
import torch
import contract_runtime
from m207_ps_vision_runtime import M207FP32GemmW4Linear
answer=dict(component=component(torch,contract_runtime.quantize_t32,M207FP32GemmW4Linear),
            target_component=from_sources(torch,Path(sys.argv[1])))
print('M414_COMPONENT='+json.dumps(answer),flush=True)
'''
    atomic(PKG/'m416_component_entry.py',child.encode('utf-8'),immutable=True)
    runner=(OLD/'run_m408_capture.sh').read_text(encoding='utf-8')
    runner=runner.replace('M408','M416').replace('m408_gate.py','m416_gate.py').replace('m408_mlp_capture_04','m416_layer13_capture_01')
    atomic(PKG/'run_m416_capture.sh',runner.encode('utf-8'),immutable=True)
    workflow=(HERE/'m408_workflow04.py').read_text(encoding='utf-8')
    workflow=workflow.replace('M408','M416').replace('latest_m408_local_mlp_','latest_m416_local_mlp_')
    workflow=workflow.replace('M416-local-MLP-A8-capture-04','M416-layer13-PS-capture-01').replace('tmp/m40804','tmp/m41601')
    workflow=workflow.replace('M416-local-MLP-transfer-04','M416-layer13-PS-transfer-01').replace('M416-local-MLP-A8-board-04','M416-layer13-PS-board-01')
    workflow=workflow.replace('m408_mlp_capture_04','m416_layer13_capture_01').replace('encoder.layers.12.layer.layer','encoder.layers.13.layer.layer')
    workflow=replace(workflow,"r['selected_layer'] != 12","r['selected_layer'] != 13")
    workflow=workflow.replace('第12层','第13层').replace('2026-10-05','2026-10-06')
    workflow=replace(workflow,"        c = r['component']","        if not r['component_isolation']['separate_process'] or not r['component_isolation']['parent_state_unchanged'] or r['component_isolation']['return_code'] != 0: raise ValueError('Parent Torch isolation incomplete')\n        c = r['component']")
    atomic(HERE/'m416_workflow.py',workflow.encode('utf-8'),immutable=True)
    # Full small package transfer is deliberately bounded; no inferred remote source path.
    control=(HERE/'m408_control06.ps1').read_text(encoding='utf-8')
    control=control.replace('M408','M416').replace('m408','m416')
    control=control.replace('M416-local-MLP-A8-capture-04','M416-layer13-PS-capture-01').replace('m416_local_mlp_candidate_04','m416_layer13_candidate_01')
    control=control.replace('tmp/m41604','tmp/m41601').replace('m416_workflow04.py','m416_workflow.py').replace('run_m416_capture.sh','run_m416_capture.sh')
    control=control.replace('M416-local-MLP-A8-board-04','M416-layer13-PS-board-01')
    start=control.index("foreach ($key in @(");end=control.index(' {',start)
    control=control[:start]+"foreach ($key in @('latest_m416_bounded_expansion_plan','latest_m415_saved_feature_language_closure','latest_m416_local_mlp_preparation04','latest_m416_local_mlp_support04'))"+control[end:]
    atomic(HERE/'m416_control.ps1',control.encode('utf-8'),immutable=True)
    files=sorted(PKG.iterdir());atomic(PKG/'SHA256SUMS',''.join(f'{sha(p)}  {p.name}\n' for p in files).encode('ascii'),immutable=True)
    files=sorted(PKG.iterdir());m=dict(file_count=len(files),total_bytes=sum(p.stat().st_size for p in files),files=[dict(path=p.name,bytes=p.stat().st_size,sha256=sha(p)) for p in files])
    atomic(PKG/'PACKAGE_MANIFEST.json',encoded(m),immutable=True)
    result=dict(status='PREPARED_M416_LAYER13_PS_CAPTURE',board_run=False,PL_run=False,selected_layer=13,
                prerequisites=priors,recovery_file_loads=recovery,actual_constructor=ctor,
                actual_constructor_sha256=sha(audit),old_manifest_sha256=sha(OLD/'PACKAGE_MANIFEST.json'),
                manifest_sha256=sha(PKG/'PACKAGE_MANIFEST.json'),payload_files=m['file_count'],payload_bytes=m['total_bytes'],
                component_isolated=True,native_shape=[1,392],original_visual_SHA_required=True,
                next='Actual isolated layer13 component, collector and control checks before one PS-only board capture/A8 screen; no PL or combination yet')
    out=BASE/'runs/M416-layer13-PS-preparation-01/RESULT.json';atomic(out,encoded(result),immutable=True)
    sync('latest_m416_local_mlp_preparation04',dict(status=result['status'],result=out.relative_to(ROOT).as_posix(),sha256=sha(out),manifest_sha256=result['manifest_sha256']),
         f'## M416 第13层PS捕获准备（2026-10-06）\n\nSHA {sha(out)}；实际冻结无forward构造核对13层双包装、FP32内部/BF16边界、两矩阵/bias和PS owner释放。原04捕获/数学/392行原批次保持，仅定位13；组件独立进程、原视觉失败保留七数组。{m["file_count"]}载荷{m["total_bytes"]}B，未板端/局部A8或PL质量，先实际组件/回收/控制核对，不进入12+13组合。')
    print('M416_PREPARATION_SYNC',sha(out),result['manifest_sha256'])

if __name__=='__main__':main()
