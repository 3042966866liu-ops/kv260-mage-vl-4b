"""Immutable numerical retry: isolated bootstrap only; same math and owners."""
import ast,json
from m351_workflow import ROOT,BASE,HERE,atomic,encoded,sha,sync
from m427_prepare import once
OLD=BASE/'candidates/M429-late11-visual-PL-numeric-02'
PKG=BASE/'candidates/M429-late11-visual-PL-numeric-03'
def main():
    b=json.loads((ROOT/'deployment/mage_vl4b/BOARD_GATE_RESULT.json').read_bytes())
    e=b['latest_m429_isolated_bootstrap_board'];assert sha(ROOT/e['result'])==e['sha256'] and e['CPU_bootstrap_pass']
    assert all(e['sha256'] in (ROOT/n).read_text(encoding='utf-8-sig') for n in ('CURRENT_STATE.md','docsMILESTONES.md'))
    cpu=json.loads((ROOT/e['result']).read_bytes());assert cpu['status']=='PASS_M429_ISOLATED_CPU_BOOTSTRAP_ONLY'
    plan=json.loads((OLD/'PLAN.json').read_bytes());plan.update(release='/home/ubuntu/tellme_release_install_20260926',component_package='/home/ubuntu/m429_late11_visual_candidate_03',isolated_bootstrap_source_sha256=e['sha256'],isolated_bootstrap_result_path='/home/ubuntu/m429_isolated_bootstrap_result_01/BOARD_RESULT.json')
    entry=(BASE/'candidates/M429-isolated-bootstrap-03/m429_component_entry.py').read_bytes()
    gate=(OLD/'m429_gate.py').read_text(encoding='utf-8').replace('/home/ubuntu/m429_late11_visual_numeric_01/','/home/ubuntu/m429_late11_visual_numeric_02/')
    gate=once(gate,"        import subprocess\n        child=",'''        bootstrap_path=Path(plan['isolated_bootstrap_result_path'])
        if digest(bootstrap_path)!=plan['isolated_bootstrap_source_sha256']:raise RuntimeError('Saved CPU bootstrap receipt differs')
        bootstrap_prior=json.loads(bootstrap_path.read_bytes())
        if bootstrap_prior['status']!='PASS_M429_ISOLATED_CPU_BOOTSTRAP_ONLY' or bootstrap_prior['gate_return_code'] or bootstrap_prior['errors']:raise RuntimeError('Same-level CPU bootstrap not passed')
        result['isolated_bootstrap_source_sha256']=plan['isolated_bootstrap_source_sha256']
        import subprocess
        child=''')
    gate=once(gate,"        lines=[x.split('=',1)[1]",'''        boots=[x.split('=',1)[1] for x in child.stdout.decode('utf-8').splitlines() if x.startswith('M429_BOOTSTRAP=')]
        if len(boots)!=1:raise RuntimeError('Unique frozen backend receipt required')
        result['component_bootstrap']=json.loads(boots[0])
        if result['component_bootstrap']!=bootstrap_prior['bootstrap']:raise RuntimeError('CPU isolated backend differs from passed small gate')
        lines=[x.split('=',1)[1]''')
    # Every math, transaction, allocator, cleanup and scope function stays exact.
    original=ast.parse((OLD/'m429_gate.py').read_text(encoding='utf-8'));revised=ast.parse(gate)
    def named(t,name):return next(x for x in ast.walk(t) if isinstance(x,(ast.ClassDef,ast.FunctionDef)) and x.name==name)
    unchanged={}
    for name in ('WorkOwner','zero','restore','stage','vision','candidate_sink','load_case'):
        assert ast.dump(named(original,name),include_attributes=False)==ast.dump(named(revised,name),include_attributes=False);unchanged[name]='identical_AST_to_02'
    PKG.mkdir(parents=True,exist_ok=False)
    for p in OLD.iterdir():
        if p.name not in ('m429_gate.py','m429_component_entry.py','PLAN.json','m429_export.py','run_m429.sh','DEPENDENCY_CLOSURE.json','SHA256SUMS','PACKAGE_MANIFEST.json'):atomic(PKG/p.name,p.read_bytes(),immutable=True)
    atomic(PKG/'m429_gate.py',gate.encode(),immutable=True);atomic(PKG/'m429_component_entry.py',entry,immutable=True);atomic(PKG/'PLAN.json',encoded(plan),immutable=True)
    for name in ('m429_export.py','run_m429.sh'):atomic(PKG/name,(OLD/name).read_text(encoding='utf-8').replace('/home/ubuntu/m429_late11_visual_numeric_01','/home/ubuntu/m429_late11_visual_numeric_02').encode(),immutable=True)
    closure=json.loads((OLD/'DEPENDENCY_CLOSURE.json').read_bytes())
    for name in ('m429_gate','m429_component_entry','m429_export'):closure['sources'][name]=sha(PKG/(name+'.py'))
    # New entry imports an already-closed frozen_video_identity module.
    assert 'frozen_video_identity' in closure['sources'] and closure['missing']==[]
    atomic(PKG/'DEPENDENCY_CLOSURE.json',encoded(closure),immutable=True)
    for p in PKG.glob('*.py'):ast.parse(p.read_text(encoding='utf-8'),feature_version=(3,10))
    atomic(PKG/'SHA256SUMS',''.join(f'{sha(p)}  {p.name}\n' for p in sorted(PKG.iterdir())).encode(),immutable=True)
    files=sorted(PKG.iterdir());m=dict(file_count=len(files),total_bytes=sum(p.stat().st_size for p in files),files=[dict(path=p.name,bytes=p.stat().st_size,sha256=sha(p)) for p in files]);atomic(PKG/'PACKAGE_MANIFEST.json',encoded(m),immutable=True)
    workflow=(HERE/'m429_workflow03.py').read_text(encoding='utf-8').replace('M429-late11-visual-PL-numeric-02','M429-late11-visual-PL-numeric-03').replace('M429-late11-visual-PL-board-01','M429-late11-visual-PL-board-02').replace('tmp/m42903','tmp/m42904').replace('M429-late11-visual-transfer-01','M429-late11-visual-transfer-02')
    workflow=once(workflow,"    for k in ('overlay_loaded'",'''    bootstrap=r['component_bootstrap']
    prior=json.loads((BASE/'runs/M429-isolated-bootstrap-board-01/BOARD_RESULT.json').read_bytes())
    if r['isolated_bootstrap_source_sha256']!=plan['isolated_bootstrap_source_sha256'] or bootstrap!=prior['bootstrap']:raise ValueError('Passed isolated bootstrap identity differs')
    for k in ('overlay_loaded' ''').replace("for k in ('overlay_loaded' ,","for k in ('overlay_loaded',")
    atomic(HERE/'m429_workflow04.py',workflow.encode(),immutable=True)
    control=(HERE/'m429_control.ps1').read_text(encoding='utf-8').replace('M429-late11-visual-PL-numeric-02','M429-late11-visual-PL-numeric-03').replace('/home/ubuntu/m429_late11_visual_candidate_02','/home/ubuntu/m429_late11_visual_candidate_03').replace('tmp/m42902','tmp/m42904').replace("'m429_workflow.py'","'m429_workflow04.py'").replace('M429-late11-visual-PL-board-01','M429-late11-visual-PL-board-02').replace('latest_m429_numeric_support','latest_m429_repair_support').replace('latest_m429_final_packet','latest_m429_repair_packet')
    control=once(control,"if ($Mode -ne 'Run')", "VerifyEvidence 'latest_m429_isolated_bootstrap_board'\nif (-not $board.latest_m429_isolated_bootstrap_board.CPU_bootstrap_pass) { throw 'CPU bootstrap unresolved' }\nif ($Mode -ne 'Run')")
    atomic(HERE/'m429_control04.ps1',control.encode(),immutable=True)
    support=(HERE/'m429_support.py').read_text(encoding='utf-8').replace('from m429_workflow import','from m429_workflow04 import').replace('m429_control.ps1','m429_control04.ps1').replace('m429_workflow.py','m429_workflow04.py').replace('m429_support.py','m429_support04.py').replace('tmp/m42902','tmp/m42904').replace('M429-numeric-support-01','M429-numeric-support-02').replace('latest_m429_numeric_support','latest_m429_repair_support')
    support=once(support,"    r['PL_rows']=[]", "    r['component_bootstrap']=json.loads((BASE/'runs/M429-isolated-bootstrap-board-01/BOARD_RESULT.json').read_bytes())['bootstrap']\n    r['isolated_bootstrap_source_sha256']=plan['isolated_bootstrap_source_sha256']\n    r['PL_rows']=[]")
    support=once(support,"('bool-rc',", "('bootstrap',lambda r:r['component_bootstrap'].__setitem__('threads',2)),('bool-rc',")
    support=support.replace('M429-late11-visual-PL-numeric-02/run_m429.sh','M429-late11-visual-PL-numeric-03/run_m429.sh')
    atomic(HERE/'m429_support04.py',support.encode(),immutable=True)
    close=(HERE/'m429_close.py').read_text(encoding='utf-8').replace('from m429_workflow03 import','from m429_workflow04 import').replace('M429-late11-visual-numerical-closure-01','M429-late11-visual-numerical-closure-02');atomic(HERE/'m429_close02.py',close.encode(),immutable=True)
    for name in ('m429_workflow04.py','m429_support04.py','m429_close02.py'):ast.parse((HERE/name).read_text(encoding='utf-8'),feature_version=(3,10))
    record=dict(status='M429_NUMERICAL_RETRY03_CPU_BOOTSTRAP_FIXED_SUPPORT_PENDING',manifest_sha256=sha(PKG/'PACKAGE_MANIFEST.json'),file_count=m['file_count'],total_bytes=m['total_bytes'],CPU_bootstrap_raw_sha256=e['sha256'],unchanged_math_and_owner_AST=unchanged,original_failure_preserved=True,missing=closure['missing'],performance_unlocked=False,temperature_measurement_enabled=False)
    out=BASE/'runs/M429-numerical-repair-packet-03/RESULT.json';atomic(out,encoded(record),immutable=True)
    sync('latest_m429_repair_packet',dict(status=record['status'],result=out.relative_to(ROOT).as_posix(),sha256=sha(out),manifest_sha256=record['manifest_sha256']),f'## M429 数值03入口修复包（2026-10-06）\n\nSHA {sha(out)}，manifest {record["manifest_sha256"]}；板端-I CPU入口已过。仅冻结runtime_site启动与独立结果目录；7处算术/事务/owner/scope函数AST相同，31递归模块missing0。旧失败原字节保留；尚需实际导出/host/control门禁，不测温，性能仍锁。')
    print('M429_REPAIR_PACKET_SYNC',sha(out),record['manifest_sha256'])
if __name__=='__main__':main()
