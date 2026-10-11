"""Prepare one complete layer13 MLP after both unchanged-kernel lower gates."""
import ast,json
from m351_workflow import ROOT,BASE,HERE,atomic,encoded,sha,sync

def change(s,a,b):
    if a not in s:raise RuntimeError('Frozen anchor missing '+a)
    return s.replace(a,b)

def main():
    pkg=BASE/'candidates/M419-layer13-complete-MLP-01'
    if pkg.exists():raise RuntimeError('Immutable packet exists')
    recovery={n:dict(full_read=True,sha256=sha(ROOT/n),bytes=len((ROOT/n).read_text(encoding='utf-8-sig').encode('utf-8'))) for n in ('CURRENT_STATE.md','DEPLOYMENT_OPERATION_MISTAKES_REVIEW.md','docsMILESTONES.md')}
    board=json.loads((ROOT/'deployment/mage_vl4b/BOARD_GATE_RESULT.json').read_bytes())
    keys=('latest_m417_reference_board02','latest_m417_reference_closure02','latest_m418_visual_descriptor','latest_m418_visual_chain','latest_m418_visual_lower_closure','latest_m412_complete_mlp_preparation','latest_m412_complete_mlp_board')
    for k in keys:
        e=board[k];assert sha(ROOT/e['result'])==e['sha256']
        assert all(e['sha256'] in (ROOT/n).read_text(encoding='utf-8-sig') for n in ('CURRENT_STATE.md','docsMILESTONES.md'))
    assert board['latest_m418_visual_chain']['numerical_pass'] and board['latest_m418_visual_descriptor']['numerical_pass']
    old=BASE/'candidates/M412-complete-visual-MLP-01';oldm=json.loads((old/'PACKAGE_MANIFEST.json').read_bytes())
    for row in oldm['files']:assert sha(old/row['path'])==row['sha256']
    policyproof=json.loads((ROOT/board['latest_m412_complete_mlp_preparation']['result']).read_bytes())
    plan=json.loads((old/'PLAN.json').read_bytes());reuse=[]
    for name,remote in [('M418-visual-linear-01','/home/ubuntu/m418_visual_linear_candidate_01'),('M417-layer13-saved-reference-02','/home/ubuntu/m417_layer13_reference_candidate_02')]:
        p=BASE/'candidates'/name;manifest=json.loads((p/'PACKAGE_MANIFEST.json').read_bytes())
        for row in manifest['files']:assert sha(p/row['path'])==row['sha256']
        reuse.append(dict(directory=remote,manifest_sha256=sha(p/'PACKAGE_MANIFEST.json')))
    plan.update(reused_packages=reuse,lower_package=reuse[0]['directory'],reference_package=reuse[1]['directory'],
                chain_result='/home/ubuntu/m418_visual_linear_01/Chain/BOARD_RESULT.json',chain_raw_sha256=board['latest_m418_visual_chain']['sha256'],
                reference_result=board['latest_m417_reference_board02']['result'],reference_raw_sha256=board['latest_m417_reference_board02']['sha256'],selected_layer=13)
    plan.pop('prior_failed_attempt',None)
    plan['user_authorization']='2026-10-06: continue bounded one-additional-layer verification after saved-feature language consistency'
    pkg.mkdir()
    for n in ('m411_mlp_binding.py','test_m411_binding.py','m412_policy.py'):
        atomic(pkg/n,(old/n).read_bytes(),immutable=True)
    gate=(old/'m412_gate.py').read_text(encoding='utf-8').replace('M412','M419').replace('m412_complete_mlp_01','m419_layer13_complete_mlp_01').replace('m412_export','m419_export')
    for a,b in [('import m410_probe as lower','import m418_probe as lower'),('from m410_saved_case','from m418_saved_case'),('from m408_target03','from m416_target13'),('from m409_gate import load_capture','from m417_gate import load_capture'),('M408_CAPTURE_EXPECTED.json','M416_CAPTURE_EXPECTED.json')]:gate=change(gate,a,b)
    gate=change(gate,"        r['component']=component(ROOT,OUTPUT.parent)","        from m414_entry import run_component\n        r['component'],r['component_isolation']=run_component(ROOT,OUTPUT.parent,HERE/'m419_component_entry.py')")
    atomic(pkg/'m419_gate.py',gate.encode('utf-8'),immutable=True)
    export=(old/'m412_export.py').read_text(encoding='utf-8').replace('M412','M419').replace('m412_complete_mlp_01','m419_layer13_complete_mlp_01')
    atomic(pkg/'m419_export.py',export.encode('utf-8'),immutable=True)
    child='''"""Actual binding fixture in an isolated child, with no model or PL."""
import json,sys,tempfile
from pathlib import Path
from test_m411_binding import component
with tempfile.TemporaryDirectory(prefix='m419_component_') as temporary:
    answer=component(Path(sys.argv[1]),Path(temporary))
print('M414_COMPONENT='+json.dumps(answer),flush=True)
'''
    atomic(pkg/'m419_component_entry.py',child.encode('utf-8'),immutable=True)
    atomic(pkg/'PLAN.json',encoded(plan),immutable=True)
    runner=(old/'run_m412_mlp.sh').read_text(encoding='utf-8').replace('M412','M419').replace('m412','m419')
    # The original runner contains no hard-coded result directory.
    atomic(pkg/'run_m419_mlp.sh',runner.encode('utf-8'),immutable=True)
    workflow=(HERE/'m412_workflow.py').read_text(encoding='utf-8').replace('M412','M419').replace('latest_m412_complete_mlp_','latest_m419_complete_mlp_').replace('tmp/m41201','tmp/m41901').replace('M419-complete-visual-MLP-01','M419-layer13-complete-MLP-01').replace('m412_control','m419_control').replace('第12层','第13层')
    workflow=change(workflow,"        ref=json.loads((ROOT/plan['reference_result']).read_bytes())","        iso=r['component_isolation']\n        if not iso['separate_process'] or not iso['parent_state_unchanged'] or iso['return_code']!=0:raise ValueError('Component parent isolation differs')\n        ref=json.loads((ROOT/plan['reference_result']).read_bytes())")
    atomic(HERE/'m419_workflow.py',workflow.encode('utf-8'),immutable=True)
    control=(HERE/'m412_control.ps1').read_text(encoding='utf-8').replace('M412','M419').replace('m412','m419').replace('M419-complete-visual-MLP-01','M419-layer13-complete-MLP-01')
    start=control.index('foreach ($key in @(');end=control.index(' { VerifyEvidence $key }',start)
    control=control[:start]+"foreach ($key in @('latest_m417_reference_board02','latest_m417_reference_closure02','latest_m418_visual_descriptor','latest_m418_visual_chain','latest_m418_visual_lower_closure','latest_m419_complete_mlp_preparation','latest_m419_complete_mlp_support'))"+control[end:]
    anchor='        Write-Output "M419_FILE_TRANSFERRED $name"'
    control=change(control,anchor,anchor+'''\n        & $uart -Command 'sudo -n true' -LogPath "tmp/m41901/sudo_transfer_$($name.Replace('.','_')).log" -TimeoutSeconds 15 -MarkerPrefix '__M419_SUDO_RC_'
        if (-not $?) { throw 'Sudo expired; stop transfer without retry' }''')
    atomic(HERE/'m419_control.ps1',control.encode('utf-8'),immutable=True)
    for p in pkg.glob('*.py'):ast.parse(p.read_bytes(),feature_version=(3,10))
    files=sorted(pkg.iterdir());atomic(pkg/'SHA256SUMS',''.join(f'{sha(p)}  {p.name}\n' for p in files).encode('ascii'),immutable=True)
    files=sorted(pkg.iterdir());m=dict(file_count=len(files),total_bytes=sum(p.stat().st_size for p in files),files=[dict(path=p.name,bytes=p.stat().st_size,sha256=sha(p)) for p in files])
    atomic(pkg/'PACKAGE_MANIFEST.json',encoded(m),immutable=True)
    value=dict(status='PREPARED_M419_LAYER13_COMPLETE_MLP',selected_layer=13,recovery_file_loads=recovery,
               manifest_sha256=sha(pkg/'PACKAGE_MANIFEST.json'),files=m['file_count'],bytes=m['total_bytes'],
               lower_chain_raw_sha256=plan['chain_raw_sha256'],reference_raw_sha256=plan['reference_raw_sha256'],
               reused_policy_component_sha256=policyproof['actual_policy_component_sha256'],
               unchanged_binding_and_policy={n:sha(pkg/n) for n in ('m411_mlp_binding.py','test_m411_binding.py','m412_policy.py')},
               protocol=plan['protocol'],component_isolated=True,board_run=False,performance_pass=False,
               next='Clean packaged child and actual collector/control checks, then full392-row numerical before predeclared complete-segment comparison; no combination or full visual yet.')
    out=BASE/'runs/M419-complete-MLP-preparation-01/RESULT.json';atomic(out,encoded(value),immutable=True)
    sync('latest_m419_complete_mlp_preparation',dict(status=value['status'],result=out.relative_to(ROOT).as_posix(),sha256=sha(out),manifest_sha256=value['manifest_sha256']),
         f'## M419 第13层完整MLP段准备（2026-10-06）\n\nSHA {sha(out)}；M417精确参考和M418单descriptor/chain闭合后，只原13层392行fc1→原GELU→fc2。复用M412同SHA实际七块3,440,656B后封锁新增DMA、256MiB普通增长预算及64MiB普通余量；无固定CMA floor，生产政策不改。组件隔离进程，原数学/判据/AB预热＋ABBABAAB8完整段保留，所有准备/转换/传输/解析纳入；尚未上板，先clean组件及回收控制，不进入12+13组合或完整视觉。')
    print('M419_COMPLETE_MLP_PREPARED',sha(out),value['manifest_sha256'])

if __name__=='__main__':main()
