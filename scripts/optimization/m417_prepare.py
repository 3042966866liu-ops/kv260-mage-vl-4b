"""Prepare saved-only layer13 ordered FP32/FP16/FTZ oracle; no board commands."""
import ast,json
from m351_workflow import ROOT,BASE,HERE,atomic,encoded,sha,sync

PKG=BASE/'candidates/M417-layer13-saved-reference-01'

def change(source,a,b):
    if a not in source:raise RuntimeError('Missing frozen anchor: '+a)
    return source.replace(a,b)

def main():
    if PKG.exists():raise RuntimeError('Immutable packet already exists')
    recovery={n:dict(full_read=True,sha256=sha(ROOT/n),bytes=len((ROOT/n).read_text(encoding='utf-8-sig').encode('utf-8'))) for n in ('CURRENT_STATE.md','DEPLOYMENT_OPERATION_MISTAKES_REVIEW.md','docsMILESTONES.md')}
    board=json.loads((ROOT/'deployment/mage_vl4b/BOARD_GATE_RESULT.json').read_bytes())
    keys=('latest_m407_visual_mlp_contract','latest_m407_visual_mlp_layout_closure','latest_m416_local_mlp_board04','latest_m416_local_mlp_closure','latest_m409_reference_preparation','latest_m409_reference_board','latest_m409_reference_closure')
    priors={}
    for k in keys:
        e=board[k];assert sha(ROOT/e['result'])==e['sha256']
        assert all(e['sha256'] in (ROOT/n).read_text(encoding='utf-8-sig') for n in ('CURRENT_STATE.md','docsMILESTONES.md'))
        priors[k]=e
    raw=json.loads((ROOT/board['latest_m416_local_mlp_board04']['result']).read_bytes())
    assert raw['selected_layer']==13 and raw['local_A8_screen_pass'] and raw['capture_exact'] and raw['bindings_restored'] and raw['visual_owner_closed']
    old=BASE/'candidates/M409-saved-MLP-reference-01'
    old_manifest=json.loads((old/'PACKAGE_MANIFEST.json').read_bytes())
    old_rows={x['path']:x for x in old_manifest['files']}
    proven=json.loads((ROOT/board['latest_m409_reference_preparation']['result']).read_bytes())
    assert proven['pure_algorithm_component'] and proven['real_Torch_small_component']['independent_int32_full_output_equal']
    current=BASE/'candidates/M416-layer13-PS-capture-01';m=json.loads((current/'PACKAGE_MANIFEST.json').read_bytes())
    assert sha(current/'PACKAGE_MANIFEST.json')==raw['manifest_sha256']
    PKG.mkdir()
    for row in m['files']:
        assert sha(current/row['path'])==row['sha256']
        if row['path'] not in ('SHA256SUMS','run_m416_capture.sh'):atomic(PKG/row['path'],(current/row['path']).read_bytes(),immutable=True)
    reused={}
    for n in ('m409_ftz_reference.py','m409_torch_component.py','test_m409_ftz_reference.py','m355_reference.py','m120_group_reference.py','m408_target_component04.py','MLP_CHAINS.json'):
        assert sha(old/n)==old_rows[n]['sha256']
        if n.endswith('.py'):ast.parse((old/n).read_bytes(),feature_version=(3,10))
        reused[n]=sha(old/n);atomic(PKG/n,(old/n).read_bytes(),immutable=True)
    gate=(old/'m409_gate.py').read_text(encoding='utf-8')
    assert sha(old/'m409_gate.py')==old_rows['m409_gate.py']['sha256']
    gate=gate.replace('M409','M417')
    for a,b in [('from m408_gate import','from m416_gate import'),('from m408_target03 import','from m416_target13 import'),('m409_mlp_reference_01','m417_layer13_reference_01'),('m408_mlp_capture_04','m416_layer13_capture_01'),('M408_CAPTURE_EXPECTED.json','M416_CAPTURE_EXPECTED.json'),('selected_layer=12','selected_layer=13'),('encoder.layers.12.mlp.','encoder.layers.13.mlp.')]:gate=change(gate,a,b)
    gate=change(gate,"        result['component']=component(torch,RELEASE,host,initial)","        from m414_entry import run_component\n        result['component'],result['component_isolation']=run_component(RELEASE,OUTPUT.parent,HERE/'m417_component_entry.py')")
    atomic(PKG/'m417_gate.py',gate.encode('utf-8'),immutable=True)
    child='''"""Independent exact-math fixture child; no model constructor or FPGA."""
import json,sys
from pathlib import Path
from m409_torch_component import component
from test_m409_ftz_reference import actual_host
import torch
root=Path(sys.argv[1]);host,initial=actual_host(root)
print('M414_COMPONENT='+json.dumps(component(torch,root,host,initial)),flush=True)
'''
    atomic(PKG/'m417_component_entry.py',child.encode('utf-8'),immutable=True)
    expected={k:raw[k] for k in ('capture_manifest','capture','target_matrices','target_resolution')};expected['raw_sha256']=board['latest_m416_local_mlp_board04']['sha256']
    atomic(PKG/'M416_CAPTURE_EXPECTED.json',encoded(expected),immutable=True)
    runner=(old/'run_m409_reference.sh').read_text(encoding='utf-8').replace('M409','M417').replace('m409_gate.py','m417_gate.py').replace('m409_mlp_reference_01','m417_layer13_reference_01')
    atomic(PKG/'run_m417_reference.sh',runner.encode('utf-8'),immutable=True)
    workflow=(HERE/'m409_workflow.py').read_text(encoding='utf-8').replace('M409','M417').replace('latest_m409_reference_','latest_m417_reference_')
    for a,b in [('M417-saved-MLP-reference-01','M417-layer13-saved-reference-01'),('tmp/m40901','tmp/m41701'),('M417-reference-transfer-01','M417-layer13-reference-transfer-01'),('M417-reference-board-01','M417-layer13-reference-board-01'),("r['selected_layer']!=12","r['selected_layer']!=13"),('encoder.layers.12.mlp.','encoder.layers.13.mlp.'),('M408_CAPTURE_EXPECTED.json','M416_CAPTURE_EXPECTED.json'),('第12层','第13层'),('2026-10-05','2026-10-06')]:workflow=change(workflow,a,b)
    workflow=change(workflow,"        c=r['component']","        iso=r['component_isolation']\n        if not iso['separate_process'] or not iso['parent_state_unchanged'] or iso['return_code']!=0:raise ValueError('Component parent-state isolation differs')\n        c=r['component']")
    atomic(HERE/'m417_workflow.py',workflow.encode('utf-8'),immutable=True)
    control=(HERE/'m416_control.ps1').read_text(encoding='utf-8').replace('M416','M417').replace('m416','m417')
    control=change(control,'M417-layer13-PS-capture-01','M417-layer13-saved-reference-01')
    control=change(control,'m417_layer13_candidate_01','m417_layer13_reference_candidate_01')
    control=change(control,'M417-layer13-PS-board-01','M417-layer13-reference-board-01')
    control=change(control,'run_m417_capture.sh','run_m417_reference.sh')
    control=change(control,'M417_ENABLE_LOCAL_MLP=1','M417_ENABLE_REFERENCE=1')
    control=control.replace('latest_m417_local_mlp_preparation04','latest_m417_reference_preparation').replace('latest_m417_local_mlp_support04','latest_m417_reference_support').replace('latest_m417_local_mlp_transfer04','latest_m417_reference_transfer')
    control=change(control,"'latest_m417_bounded_expansion_plan','latest_m415_saved_feature_language_closure'","'latest_m416_local_mlp_board04','latest_m416_local_mlp_closure'")
    control=change(control,'-TimeoutSeconds 780','-TimeoutSeconds 1080')
    # Keep the authorized terminal timestamp live during the bounded full packet transfer.
    anchor='        Write-Output "M417_FILE_TRANSFERRED $name"'
    control=change(control,anchor,anchor+'''\n        & $uart -Command 'sudo -n true' -LogPath "tmp/m41701/sudo_transfer_$($name.Replace('.','_')).log" -TimeoutSeconds 15 -MarkerPrefix '__M417_SUDO_RC_'
        if (-not $?) { throw 'Sudo expired; stop transfer without retry' }''')
    atomic(HERE/'m417_control.ps1',control.encode('utf-8'),immutable=True)
    for path in PKG.glob('*.py'):ast.parse(path.read_bytes(),feature_version=(3,10))
    files=sorted(PKG.iterdir());atomic(PKG/'SHA256SUMS',''.join(f'{sha(p)}  {p.name}\n' for p in files).encode('ascii'),immutable=True)
    files=sorted(PKG.iterdir());manifest=dict(file_count=len(files),total_bytes=sum(p.stat().st_size for p in files),files=[dict(path=p.name,bytes=p.stat().st_size,sha256=sha(p)) for p in files])
    atomic(PKG/'PACKAGE_MANIFEST.json',encoded(manifest),immutable=True)
    value=dict(status='PREPARED_M417_LAYER13_SAVED_EXACT_REFERENCE',prerequisites=priors,recovery_file_loads=recovery,
               capture_raw_sha256=expected['raw_sha256'],capture_manifest_sha256=expected['capture_manifest']['sha256'],manifest_sha256=sha(PKG/'PACKAGE_MANIFEST.json'),
               files=manifest['file_count'],bytes=manifest['total_bytes'],unchanged_proven_math_sources=reused,
               reused_algorithm_checks=proven['pure_algorithm_component'],reused_Torch_component=proven['real_Torch_small_component'],
               selected_layer=13,component_isolated=True,visual_forward_calls=0,overlay_loads=0,DMA_allocations=0,PL_transactions=0,
               board_run=False,performance_pass=False,next='Check actual isolated child, actual producer/collector/control/failure and transfer receipts; then one saved-only PS reference, no visual rerun or combination.')
    out=BASE/'runs/M417-layer13-reference-preparation-01/RESULT.json';atomic(out,encoded(value),immutable=True)
    sync('latest_m417_reference_preparation',dict(status=value['status'],result=out.relative_to(ROOT).as_posix(),sha256=sha(out),manifest_sha256=value['manifest_sha256']),
         f'## M417 第13层已保存输入精确数学参考准备（2026-10-06）\n\nSHA {sha(out)}；复用M416原六张量与原视觉精确证据；M409原T32/顺序FP32/FP16/FTZ/重试/GELU/bias代码同SHA，旧小组件证据复用不重跑。只定位13层、组件隔离进程、默认关闭、原35全SHA及49源码保持，0新视觉/Overlay/DMA/语言/PL。尚未执行参考，配套入口/回收/控制检查后才一次PS参考；12+13组合保持未解锁。')
    print('M417_REFERENCE_PREPARED',sha(out),value['manifest_sha256'],manifest['file_count'],manifest['total_bytes'])

if __name__=='__main__':main()
