"""Verify new observation orchestration/collector; reused DMA policies unchanged."""
import ast
import base64
import copy
import hashlib
import json
import subprocess
import sys
from types import SimpleNamespace
from m351_workflow import ROOT,HERE,BASE,sha,atomic,encoded,sync
from m374_prepare import PKG,OLD,once

def main():
    original=(HERE/'m373_control.ps1').read_text(encoding='utf-8')
    controller=original.replace('M373','M374').replace('m373','m374')
    controller=controller.replace('M374-future-wait-component-01','M374-layer-future-wait-01').replace('/home/ubuntu/m374_future_wait_component_01','/home/ubuntu/m374_layer_future_wait_candidate_01')
    controller=controller.replace('latest_m374_future_wait_preparation','latest_m374_layer_wait_preparation').replace('latest_m374_future_wait_transfer','latest_m374_layer_wait_transfer')
    controller=controller.replace('M374-future-wait-board-01','M374-layer-wait-board-01')
    controller=controller.replace('m374_export_result.py\"','m374_export_result.py B1\"')
    controller=controller.replace('run_m374_component.sh','run_m374_staged_layer.sh')
    controller=controller.replace('sudo_precheck_02.log','sudo_precheck_01.log').replace('__M374_CHECK_SUDO_RC_0__','__M374_PRECHECK_SUDO_RC_0__')
    controller=once(controller,"    foreach ($name in (@('PACKAGE_MANIFEST.json')+@($manifest.files | ForEach-Object path))) {",
        "    $oldManifest=Get-Content -LiteralPath (Join-Path $workspace 'deployment/mage_vl4b/optimization_v1/candidates/M365-staged-layer-03/PACKAGE_MANIFEST.json') -Raw -Encoding UTF8 | ConvertFrom-Json\n    $oldEntries=@{}\n    foreach ($entry in $oldManifest.files) { $oldEntries[$entry.path]=$entry.sha256 }\n    $delta=@($manifest.files | Where-Object { -not $oldEntries.ContainsKey($_.path) -or $oldEntries[$_.path] -ne $_.sha256 } | ForEach-Object path)\n    foreach ($name in (@('PACKAGE_MANIFEST.json')+$delta)) {")
    controller=once(controller,'    & $python -X utf8 -B $workflow transfer',
        "    & $uart -Command \"sudo -n env PYTHONDONTWRITEBYTECODE=1 /usr/local/share/pynq-venv/bin/python -B $remote/m374_assemble.py $digest\" -LogPath 'tmp/m374/assembly_uart.log' -TimeoutSeconds 30 -MarkerPrefix '__M374_ASSEMBLY_RC_'\n    if (-not $?) { throw 'Assembly failed; no gate' }\n    & $uart -Command \"sudo -n bash -n $remote/run_m374_staged_layer.sh\" -LogPath 'tmp/m374/root_syntax_uart.log' -TimeoutSeconds 15 -MarkerPrefix '__M374_SYNTAX_RC_'\n    if (-not $?) { throw 'Root bash-n failed' }\n    & $python -X utf8 -B $workflow transfer")
    controller=once(controller,'-Command "bash $remote/run_m374_staged_layer.sh $digest --enable-fixture-gate"',
        '-Command "sudo -n env M374_ENABLE_STAGED_LAYER=1 bash $remote/run_m374_staged_layer.sh $digest Run B1"')
    controller=controller.replace("-TimeoutSeconds 60 -MarkerPrefix '__M374_COMPONENT_RC_'","-TimeoutSeconds 900 -MarkerPrefix '__M374_COMPONENT_RC_'")
    atomic(HERE/'m374_control.ps1',controller.encode('utf-8'))
    pwsh='C:/Users/30429/.cache/codex-runtimes/codex-primary-runtime/dependencies/native/powershell/pwsh.exe'
    checked=subprocess.run([pwsh,'-NoProfile','-File',str(HERE/'m374_control.ps1'),'-Mode','SelfTest'],capture_output=True,text=True,encoding='utf-8')
    assert checked.returncode==0 and 'M374_CONTROL_SELF_TEST_PASS' in checked.stdout,checked.stdout+checked.stderr
    # Execute the exact new gate's observed_family body with explicit CPU PL fakes.
    import test_m374_layer_wait as test
    from m374_layer_wait import LayerWaitDiagnostic,FAMILIES
    from m374_wait_validation import validate
    source=(PKG/'m374_staged_layer_gate.py').read_text(encoding='utf-8')
    main_node=next(n for n in ast.parse(source).body if isinstance(n,ast.FunctionDef) and n.name=='main')
    callback=next(n for n in main_node.body if isinstance(n,ast.Try) for n in ast.walk(n) if isinstance(n,ast.FunctionDef) and n.name=='observed_family')
    prior=json.loads((BASE/'runs/M365-staged-layer-board-01/BOARD_RESULT.json').read_text(encoding='utf-8'))
    chains={t['family']:t['chain_index'] for t in prior['transactions']}
    class Probe(test.Probe):
        def _language_chain(self,layer,family):return dict(chain_index=chains[family],layer=layer,family=family,groups=1)
    runtime=Probe();scope=LayerWaitDiagnostic(runtime,enabled=True);families=[];marks=[]
    namespace=dict(scope=scope,families=families,FAMILIES=FAMILIES,policy=SimpleNamespace(capture=lambda label,check:marks.append(label)),
        tensor=lambda v:dict(shape=list(v.shape)),original_family=lambda layer,name,values:runtime.language_family_many(layer,name,values))
    exec(compile(ast.Module(body=[callback],type_ignores=[]),str(PKG/'m374_staged_layer_gate.py'),'exec'),namespace)
    def layer():
        return [namespace['observed_family'](0,f,test.np.ones((159,64),test.np.float32)) for f in FAMILIES]
    output=scope.run(layer)
    assert len(output)==5 and len(marks)==10 and all(test.np.all(row['probe']==3) for row in output)
    observed=scope.report();attribution=validate(observed,prior['transactions'])
    # Collector uses original full layer/transaction/release reference; fake wait probe only.
    import m374_collect as collector
    row=copy.deepcopy(prior)
    row.update(status='PASS_M374_SINGLE_LAYER_DIAGNOSTIC',manifest_sha256=sha(PKG/'PACKAGE_MANIFEST.json'),future_wait=observed,
        future_wait_summary=attribution,future_capability_raw_sha256='52d05d3aa2ab204fa53a9281804b5ad76e15fdd92c6376780bf506fe60868067',ps_prefetch_enabled=False)
    def export(r):
        raw=encoded(r);parts=[raw[i:i+900] for i in range(0,len(raw),900)]
        return 'M374_RESULT_SHA256='+hashlib.sha256(raw).hexdigest()+'\nM374_SAVED_GATE_RC='+str(r['gate_return_code'])+'\n'+''.join(f'M374_RESULT_CHUNK={i}/{len(parts)}:'+base64.b64encode(p).decode()+'\n' for i,p in enumerate(parts))+f'M374_DONE case=B1 gate_rc={r["gate_return_code"]} export_rc=0\n'
    assert collector.decode(export(row))[2]==row
    fail=copy.deepcopy(row);fail.update(status='FAIL',gate_return_code=1,errors=['deliberate fixture failure'])
    assert collector.decode(export(fail))[2]==fail
    negatives=0
    for key,value in [('ps_prefetch_enabled',True),('future_capability_raw_sha256','0'*64),('future_wait_recovery_error','fake error'),('future_wait_summary',{}),('safe_buffers_released',False),('fpga_transactions',25),('errors',['error']),('memory_capacity_proven',True),('manifest_sha256','0'*64)]:
        try:collector.decode(export(dict(row,**{key:value})))
        except ValueError:negatives+=1
        else:raise AssertionError('Invalid PASS accepted')
    for log in (export(row)+export(row),export(row).replace('CHUNK=1/','CHUNK=0/'),export(row).replace('export_rc=0','export_rc=1')):
        try:collector.decode(log)
        except ValueError:negatives+=1
        else:raise AssertionError('Invalid log accepted')
    manifest=json.loads((PKG/'PACKAGE_MANIFEST.json').read_text(encoding='utf-8'))
    for r in manifest['files']:assert sha(PKG/r['path'])==r['sha256']
    path=BASE/'runs/M374-layer-wait-support-01/RESULT.json'
    r=dict(status='PASS_OFFLINE_ACTUAL_CALLBACK_AND_COLLECTION_SUPPORT',manifest_sha256=sha(PKG/'PACKAGE_MANIFEST.json'),
        callback_source_actual_package=True,explicit_cpu_pl_parser_memory_fakes=True,original_layer_reference_reused_for_collector_only=True,
        real_future_condition=True,observed_families=5,pack_results=25,parse_results=25,controller_failure_collects=True,
        collector_positive_and_failure=True,collector_negative_checks=negatives,new_workers_or_extra_dma=0,
        board_run=False,numerical_pass=False,performance_pass=False,
        source_sha256={n:sha(HERE/n) for n in ('m374_control.ps1','m374_collect.py','m374_workflow.py','m374_support.py','m374_layer_wait.py','m374_wait_validation.py')})
    atomic(path,encoded(r),immutable=True);digest=sha(path)
    sync('latest_m374_layer_wait_support',dict(status=r['status'],result=path.relative_to(ROOT).as_posix(),sha256=digest,manifest_sha256=r['manifest_sha256']),
        f'## M374 实际观察回调与回收控制支持通过（2026-10-03）\n\n从冻结新包提取真实 observed_family，显式CPU PL/解析替身、真实Future执行五family，25pack/25parse、50记录、方法恢复和trace独立闭合；collector接受明确fake等待加已有完整原数值参考/故意失败，{negatives}项负例拒绝，控制故意失败仍收集。没有上板或新增数值/性能证据。支持 SHA {digest}；下一步manifest-first新字节和同SHA旧依赖组装核对后，一次单层。')
    print('M374_SUPPORT_PASS',digest,negatives)

if __name__=='__main__':main()
