"""Prepare exact route, assembly and receipt checks before any COM3 action."""
from m351_workflow import HERE,atomic


def main():
    control=(HERE/'m437_control.ps1').read_text(encoding='utf-8')
    control=control.replace('-TimeoutSeconds 1080','-TimeoutSeconds 1600')
    anchor='foreach ($row in $manifest.files) {'
    assert control.count(anchor)==1
    guard="""VerifyEvidence 'latest_m437_transfer_support'
$transferSupport=Get-Content -Raw -Encoding UTF8 -LiteralPath (Join-Path $workspace $board.latest_m437_transfer_support.result) | ConvertFrom-Json
if ($transferSupport.manifest_sha256 -ne $digest -or $transferSupport.candidate_remote -ne $remote) { throw 'Final supported routes differ' }
foreach ($p in $transferSupport.host_sources.PSObject.Properties) {
    if ((Get-FileHash -LiteralPath (Join-Path $PSScriptRoot $p.Name) -Algorithm SHA256).Hash.ToLowerInvariant() -ne $p.Value) { throw 'Final supported source changed' }
}
"""
    control=control.replace(anchor,guard+anchor)
    atomic(HERE/'m437_control02.ps1',control.encode('utf-8'),immutable=True)
    text=(HERE/'m433_transfer_support.py').read_text(encoding='utf-8').replace('M433','M437').replace('m433','m437')
    text=text.replace('latest_m437_performance_support','latest_m437_support')
    text=text.replace('M432-late11-integrated-video-02','M433-late11-complete-request-warm-01')
    text=text.replace('/home/ubuntu/m432_late11_integrated_candidate_02','/home/ubuntu/m433_late11_warm_candidate_01')
    text=text.replace('M437-performance-transfer-01','M437-natural-IO-transfer-01').replace('latest_m437_performance_transfer','latest_m437_natural_IO_transfer')
    start=text.index("    control=(HERE/")
    text=text[:start]+"""    import ast
    from pathlib import PurePosixPath
    control=(HERE/'m437_control02.ps1').read_text(encoding='utf-8')
    candidate='/home/ubuntu/m437_natural_IO_candidate_01';evidence='/home/ubuntu/m437_natural_IO_result_01'
    assert candidate!=evidence and not PurePosixPath(candidate).is_relative_to(PurePosixPath(evidence)) and not PurePosixPath(evidence).is_relative_to(PurePosixPath(candidate))
    assert f"$remote='{candidate}'" in control
    gate_ast=ast.parse((pkg/'m437_gate.py').read_text(encoding='utf-8'))
    main_fn=next(n for n in gate_ast.body if isinstance(n,ast.FunctionDef) and n.name=='main')
    assignments=[n for n in main_fn.body if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='EVIDENCE' for t in n.targets)]
    assert len(assignments)==1 and ast.literal_eval(assignments[0].value.args[0])==evidence
    exp=next(n for n in ast.parse((pkg/'m437_export.py').read_text(encoding='utf-8')).body if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='OUTPUT' for t in n.targets))
    assert ast.literal_eval(exp.value.args[0])==evidence+'/BOARD_RESULT.json'
    runner=(pkg/'run_m437.sh').read_text(encoding='utf-8')
    assert f'[[ ! -e {evidence} ]] || exit 67' in runner
    assert 'Collect' in runner and 'M437_ENABLE_INTEGRATED_VIDEO' in runner
    assert '1600' in control and '5100' in control
    assert w.OUT==BASE/'runs/M437-natural-IO-board-01/BOARD_RESULT.json'
    closure=json.loads((pkg/'DEPENDENCY_CLOSURE.json').read_bytes())
    assert not closure['missing'] and all(closure['files'][p.stem]==sha(p) for p in pkg.glob('*.py'))
    assert sha(pkg/'m433_timed_visual.py')==sha(old/'m433_timed_visual.py')
    assert sha(pkg/'m433_light_policy.py')==sha(old/'m433_light_policy.py')
    assert not any(p.name in ('m435_io_observer.py','m425_warm.py') for p in pkg.iterdir())
    cp=subprocess.run([ps,'-NoProfile','-File',str(HERE/'m437_control02.ps1'),'-Mode','SelfTest'],capture_output=True)
    assert cp.returncode==0 and b'M437_CONTROL_SELF_TEST_PASS' in cp.stdout
    record=dict(status='PASS_M437_ROUTE_ASSEMBLY_TRANSFER_SUPPORT_ONLY',manifest_sha256=digest,
        candidate_remote=candidate,evidence_remote=evidence,actual_assembly=True,actual_transfer_receipts=True,
        actual_PowerShell_delta=True,actual_route_AST=True,original_provider_and_policy_unchanged=True,
        local_dependency_SHA_complete=True,negative_checks=rejected,
        support_sha256=e['sha256'],host_sources={n:sha(HERE/n) for n in ('m437_control02.ps1','m437_workflow.py','m437_sequence.py','m437_transfer_support.py')},
        fixtures_explicitly_synthetic=True,board_run=False,performance_pass=False,temperature_measurement_enabled=False)
    p=BASE/'runs/M437-transfer-support-01/RESULT.json';atomic(p,encoded(record),immutable=True)
    sync('latest_m437_transfer_support',dict(status=record['status'],result=p.relative_to(ROOT).as_posix(),sha256=sha(p),manifest_sha256=digest),
        f'## M437 独立路径与实际组装传输配套（2026-10-07）\\n\\nSHA {sha(p)}；真实assembler同SHA白名单、实际PowerShell增量选择和host transfer回执/最终BOARD键、{len(rejected)}缺失/乱序/SHA/额外文件负例通过。actual gate/export/runner/control四路径严格独立，全部local依赖SHA，原provider/policy字节不改。02仅增收集预算至1600s覆盖4MiB原900B协议并强制本支持；Run5100s。0板端/性能，唯一下一步同COM3一次sudo、manifest-first上传及固定4＋8执行；已有run或raw只Collect，不测温。')
    print('M437_TRANSFER_SUPPORT_SYNC',sha(p),len(rejected))


if __name__=='__main__':main()
"""
    atomic(HERE/'m437_transfer_support.py',text.encode('utf-8'),immutable=True)
    print('M437_TRANSFER_SUPPORT_READY')


if __name__=='__main__':main()
