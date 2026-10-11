"""Freeze one observation-only layer gate from verified M365 package bytes."""
import ast
import json
import shutil
import symtable
import sys
from pathlib import Path
from m351_workflow import ROOT,HERE,BASE,sha,atomic,encoded,sync

OLD=BASE/'candidates/M365-staged-layer-03'
PKG=BASE/'candidates/M374-layer-future-wait-01'
OUT=BASE/'runs/M374-layer-wait-preparation-01'

def once(text,before,after):
    if text.count(before)!=1:raise RuntimeError('Expected unique source anchor: '+before)
    return text.replace(before,after)

def main():
    if PKG.exists() or OUT.exists():raise RuntimeError('Immutable preparation exists')
    board=json.loads((ROOT/'deployment/mage_vl4b/BOARD_GATE_RESULT.json').read_text(encoding='utf-8'))
    prerequisite={}
    for key in ('latest_m365_stage_support','latest_m365_staged_layer_closure','latest_m373_future_wait_closure','latest_m374_layer_wait_plan'):
        row=board[key];assert sha(ROOT/row['result'])==row['sha256']
        assert all(row['sha256'] in (ROOT/p).read_text(encoding='utf-8-sig') for p in ('CURRENT_STATE.md','docsMILESTONES.md'))
        prerequisite[key]=row['sha256']
    old_manifest=json.loads((OLD/'PACKAGE_MANIFEST.json').read_text(encoding='utf-8'))
    assert sha(OLD/'PACKAGE_MANIFEST.json')==board['latest_m365_stage_support']['manifest_sha256']
    for row in old_manifest['files']:assert sha(OLD/row['path'])==row['sha256']
    PKG.mkdir(parents=True)
    excluded={'m365_assemble.py','m365_staged_layer_gate.py','m365_export_result.py','run_m365_staged_layer.sh','SHA256SUMS'}
    for row in old_manifest['files']:
        if row['path'] not in excluded:shutil.copyfile(OLD/row['path'],PKG/row['path'])
    for name in ('m374_layer_wait.py','m374_assemble.py','m374_wait_validation.py'):shutil.copyfile(HERE/name,PKG/name)
    prior_pkg=BASE/'candidates/M373-future-wait-component-01'
    for name in ('m372_future_wait.py','decode_trace.py'):shutil.copyfile(prior_pkg/name,PKG/name)
    capability=ROOT/board['latest_m373_future_wait_board']['result']
    assert sha(capability)=='52d05d3aa2ab204fa53a9281804b5ad76e15fdd92c6376780bf506fe60868067'
    shutil.copyfile(capability,PKG/'M373_CAPABILITY_RESULT.json')
    source=(OLD/'m365_staged_layer_gate.py').read_text(encoding='utf-8')
    source=source.replace('/home/ubuntu/m365_staged_layer_02','/home/ubuntu/m374_layer_future_wait_01')
    source=source.replace('M365','M374').replace('from m365_export_result import emit_saved','from m374_export_result import emit_saved')
    # All existing loaders, source/hardware checks, memory and DMA policies remain.
    source=once(source,"        result['prior_board_sha256'] = PRIOR_SHA", "        result['prior_board_sha256'] = PRIOR_SHA\n        cap_path=HERE/'M373_CAPABILITY_RESULT.json'\n        cap=json.loads(cap_path.read_text(encoding='utf-8'))\n        if sha256(cap_path)!='52d05d3aa2ab204fa53a9281804b5ad76e15fdd92c6376780bf506fe60868067' or cap['gate_return_code']!=0 or cap['status']!='PASS_FUTURE_WAIT_CPU_COMPONENT_ONLY':raise RuntimeError('Wait capability prerequisite differs')\n        result['future_capability_raw_sha256']=sha256(cap_path)")
    source=once(source,'        model=engine.language;families=[];original_family=model._family',
        '        from m374_layer_wait import LayerWaitDiagnostic\n        scope=LayerWaitDiagnostic(runtime,enabled=True)\n        model=engine.language;families=[];original_family=model._family')
    source=once(source,'            output=original_family(layer,name,values)',
        '            with scope.family(layer,name,values):\n                output=original_family(layer,name,values)')
    source=once(source,'        output,kv=one_layer(model,hidden.copy())',
        "        try:\n            output,kv=scope.run(lambda:one_layer(model,hidden.copy()))\n        finally:\n            try:result['future_wait']=scope.report()\n            except BaseException as observation_error:result['future_wait_recovery_error']=type(observation_error).__name__+': '+str(observation_error)")
    source=once(source,"        result['numerical_pass']=True;result['single_layer_diagnostic_pass']=True",
        "        from m374_wait_validation import validate\n        result['future_wait_summary']=validate(result['future_wait'],result['transactions'])\n        result['ps_prefetch_enabled']=False\n        result['numerical_pass']=True;result['single_layer_diagnostic_pass']=True")
    source=source.replace("'Independent layer adjudication then separately freeze fixed-text admission; no full-model/video/performance unlocked automatically'", "'Adjudicate actual single-layer Future waiting; only then prepare a separate fixed-video narrow wait diagnostic. No prefetch or new performance claim.'")
    atomic(PKG/'m374_staged_layer_gate.py',source.encode('utf-8'))
    exporter=(OLD/'m365_export_result.py').read_text(encoding='utf-8').replace('M365','M374').replace('/home/ubuntu/m365_staged_layer_02','/home/ubuntu/m374_layer_future_wait_01')
    exporter=once(exporter,'import sys','import sys\nimport time')
    exporter=once(exporter,"    for i,p in enumerate(chunks):print(f'M374_RESULT_CHUNK={i}/{len(chunks)}:'+base64.b64encode(p).decode('ascii'),flush=True)",
        "    for i,p in enumerate(chunks):\n        print(f'M374_RESULT_CHUNK={i}/{len(chunks)}:'+base64.b64encode(p).decode('ascii'),flush=True)\n        time.sleep(0.04)")
    atomic(PKG/'m374_export_result.py',exporter.encode('utf-8'))
    runner=(OLD/'run_m365_staged_layer.sh').read_text(encoding='utf-8').replace('M365','M374').replace('m365_export_result','m374_export_result').replace('m365_staged_layer_gate','m374_staged_layer_gate').replace('/home/ubuntu/m365_staged_layer_02','/home/ubuntu/m374_layer_future_wait_01')
    runner=once(runner,'task_python=/usr/local/share/pynq-venv/bin/python', 'task_python=/usr/local/share/pynq-venv/bin/python\nexport PYTHONDONTWRITEBYTECODE=1')
    atomic(PKG/'run_m374_staged_layer.sh',runner.encode('utf-8'))
    collector=(HERE/'m365_collect.py').read_text(encoding='utf-8').replace('M365','M374').replace('M374-staged-layer-03','M374-layer-future-wait-01').replace('M374-staged-layer-board-01','M374-layer-wait-board-01').replace('latest_m365_staged_layer_board','latest_m374_layer_wait_board')
    collector=once(collector,'from board_safety import safe_to_release','from board_safety import safe_to_release\nfrom m374_wait_validation import validate')
    collector=once(collector,"        if not r['same_overlay_minimal_proof']['full_output_exact']", "        if r.get('future_wait_recovery_error') or r.get('ps_prefetch_enabled') is not False or r['future_capability_raw_sha256']!='52d05d3aa2ab204fa53a9281804b5ad76e15fdd92c6376780bf506fe60868067':raise ValueError('Wait observation prerequisite/scope differs')\n        if validate(r['future_wait'],r['transactions'])!=r['future_wait_summary']:raise ValueError('Wait attribution differs')\n        if not r['same_overlay_minimal_proof']['full_output_exact']")
    collector=collector.replace('latest_m365_staged_layer_board','latest_m374_layer_wait_board')
    collector=collector.replace('下一步先单层解读并同步，固定文本需独立论证与新包，不能自动扩大。','本次仅观察真实Future等待，下一步先解释单层结果；不能外推视频等待或新增提速，预读仍关闭。')
    atomic(HERE/'m374_collect.py',collector.encode('utf-8'))
    trees={p.stem:ast.parse(p.read_text(encoding='utf-8'),feature_version=(3,10)) for p in PKG.glob('*.py')}
    closure=json.loads((PKG/'SOURCE_CLOSURE.json').read_text(encoding='utf-8'))
    allowed=set(sys.stdlib_module_names)|set(closure['modules'])|{'numpy','pynq','tokenizers'}
    missing=[]
    for module,tree in trees.items():
        for node in ast.walk(tree):
            names=[r.name.split('.')[0] for r in node.names] if isinstance(node,ast.Import) else ([(node.module or '').split('.')[0]] if isinstance(node,ast.ImportFrom) else [])
            missing.extend((module,n) for n in names if n and n not in trees and n not in allowed)
    assert not missing,missing
    symbols=next(t for t in symtable.symtable(source,'gate','exec').get_children() if t.get_name()=='main')
    assert next(t for t in symbols.get_children() if t.get_name()=='tracked_allocate').lookup('SHAPES').is_global()
    hardware=json.loads((PKG/'HARDWARE_CLOSURE.json').read_text(encoding='utf-8'))
    assert hardware['status']=='PASS_ALL_NEW_CIRCUIT_PREREQUISITES'
    for r in hardware['prerequisites']:assert sha(ROOT/r['path'])==r['sha256']
    frozen=ROOT/'release_staging/kv260-mage-vl-4b-prebuilt-install-20260926-v7'
    for r in closure['files']:assert sha(frozen/r['path'])==r['sha256']
    for name in ('m365_stage_policy.py','owned_buffer_release.py','frozen_one_layer.py','LAYER_EXPECTED.json'):assert sha(PKG/name)==sha(OLD/name)
    rows=[dict(path=p.name,bytes=p.stat().st_size,sha256=sha(p)) for p in sorted(PKG.iterdir())]
    atomic(PKG/'SHA256SUMS',''.join(r['sha256']+'  '+r['path']+'\n' for r in rows).encode('ascii'))
    rows.append(dict(path='SHA256SUMS',bytes=(PKG/'SHA256SUMS').stat().st_size,sha256=sha(PKG/'SHA256SUMS')))
    atomic(PKG/'PACKAGE_MANIFEST.json',encoded(dict(schema='m374-layer-future-wait-v1',files=rows,file_count=len(rows),total_bytes=sum(r['bytes'] for r in rows))))
    assert {p.name for p in PKG.iterdir()}=={r['path'] for r in rows}|{'PACKAGE_MANIFEST.json'}
    r=dict(status='PASS_OFFLINE_LAYER_WAIT_PACKAGE_PREPARATION',build_id='0x4D333537',prior_sha256=prerequisite,
        manifest_sha256=sha(PKG/'PACKAGE_MANIFEST.json'),file_count=len(rows),total_bytes=sum(x['bytes'] for x in rows),
        hardware_prerequisites_same_sha=True,recursive_import_missing=missing,python310_syntax=True,allocator_shapes_global=True,
        original_layer_math_reference_policy_unchanged=True,observer_capability_board_pass=True,expected_results_per_kind=25,
        pack_token_order=[0,32,64,96,128],parse_token_order=[0,32,64,128,96],additional_explicit_cma_bytes=0,
        actual_model_wait_s=None,board_run=False,ps_prefetch_enabled=False,numerical_pass=False,performance_pass=False,
        rejected_attempts=['Initial offline validator assumed ascending parse tail. Frozen scheduler actually drains output slots at starts128 then96. One CPU test rejected; corrected validation only before packaging. Math/schedule unchanged; no board action.'],
        next_step='New collector/controller failure tests and observed callback support before upload; one same-terminal layer wait gate only.')
    atomic(OUT/'RESULT.json',encoded(r),immutable=True);digest=sha(OUT/'RESULT.json')
    sync('latest_m374_layer_wait_preparation',dict(status=r['status'],result=(OUT/'RESULT.json').relative_to(ROOT).as_posix(),sha256=digest,manifest_sha256=r['manifest_sha256']),
        f'## M374 单层实际等待观察包准备（2026-10-03）\n\nBuild0x4D333537；原M365数学/输入/参考/七DMA与内存停止/恢复保持同SHA。加入已M373板端通过的M372 result钩子及bounded trace，0新增DMA/worker/PS预读。源码递归missing=0、3.10语法、SHAPES作用域及同SHA硬件证据通过。离线初稿误设解析结尾为96→128，真实冻结双输出槽按128→96回收；验证拒绝后只修观察校验，不改调度。原PLAN仅规格，此处明确纠正解析序列。证据 SHA {digest}；manifest {r["manifest_sha256"]}。仍未上板/实际等待；下一步控制及回收支持通过后才上传执行一次。')
    print(json.dumps(r))

if __name__=='__main__':main()
