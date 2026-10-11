"""Freeze isolated reference-entry repair and unchanged layer12 candidate."""
import ast,json
from m351_workflow import ROOT,BASE,HERE,atomic,encoded,sha,sync
from m414_workflow import PKG
from m414_quality import THRESHOLDS
from m414_policy import POLICY


def main():
    if PKG.exists():raise RuntimeError('Immutable candidate already exists')
    recovery={n:dict(sha256=sha(ROOT/n),characters=len((ROOT/n).read_text(encoding='utf-8-sig')),full_read=True) for n in ('CURRENT_STATE.md','DEPLOYMENT_OPERATION_MISTAKES_REVIEW.md','docsMILESTONES.md','deployment/mage_vl4b/BOARD_GATE_RESULT.json')}
    b=json.loads((ROOT/'deployment/mage_vl4b/BOARD_GATE_RESULT.json').read_bytes())
    for key in ('latest_m413_layer12_visual_board','latest_m413_layer12_visual_closure','latest_m413_original_reference_audit','latest_m412_complete_mlp_closure','latest_m410_visual_lower_closure','latest_m409_reference_closure'):
        row=b[key];assert sha(ROOT/row['result'])==row['sha256'];assert all(row['sha256'] in (ROOT/n).read_text(encoding='utf-8-sig') for n in ('CURRENT_STATE.md','docsMILESTONES.md'))
    source=BASE/'candidates/M413-layer12-full-visual-01'
    m=json.loads((source/'PACKAGE_MANIFEST.json').read_bytes())
    for row in m['files']:assert sha(source/row['path'])==row['sha256']
    plan=json.loads((source/'PLAN.json').read_bytes())
    plan.update(reference_entry_repair=dict(parent_component_removed=True,component_separate_CPU_process=True,
                original_call_boundary_restored=True,reference_before_Overlay=True,
                all_existing_original_SHA_and_capture_required=True,save_before_failed_comparison=True,
                board_root_cause_not_yet_proven=True,prior_failure_sha256=b['latest_m413_layer12_visual_board']['sha256']))
    plan['independent_admission']=POLICY
    context=BASE/'runs/M414-context-component-01/RESULT.json';entry=BASE/'runs/M414-entry-component-01/RESULT.json'
    c=json.loads(context.read_bytes());e=json.loads(entry.read_bytes())
    assert c['visual_bit_equal'] and c['owner_collected'] and all(c['layer12_capture_bit_equal'].values()) and e['component_process']['parent_state_unchanged'] and e['negative_checks']==3
    component=dict(e['component'],status='PASS_M414_ACTUAL_TORCH_COMPONENT_FROM_ISOLATED_PROCESS',WSL_not_board=True,origin_sha256=sha(entry))
    atomic(BASE/'runs/M414-component-02/RESULT.json',encoded(component),immutable=True)
    PKG.mkdir()
    names=('m414_gate.py','m414_policy.py','m414_quality.py','m414_export.py','m414_entry.py','test_m414_quality.py')
    for name in names:
        data=(HERE/name).read_bytes();ast.parse(data,feature_version=(3,10));atomic(PKG/name,data,immutable=True)
    for name in ('m411_mlp_binding.py','EXPECTED_VISUAL.json'):atomic(PKG/name,(source/name).read_bytes(),immutable=True)
    atomic(PKG/'PLAN.json',encoded(plan),immutable=True)
    runner=(source/'run_m413_mlp.sh').read_text(encoding='utf-8').replace('M413','M414').replace('m413','m414')
    atomic(PKG/'run_m414_mlp.sh',runner.encode('utf-8'),immutable=True)
    files=sorted(PKG.iterdir());atomic(PKG/'SHA256SUMS',''.join(f'{sha(p)}  {p.name}\n' for p in files).encode('ascii'),immutable=True)
    files=sorted(PKG.iterdir());manifest=dict(file_count=len(files),total_bytes=sum(p.stat().st_size for p in files),files=[dict(path=p.name,bytes=p.stat().st_size,sha256=sha(p)) for p in files])
    atomic(PKG/'PACKAGE_MANIFEST.json',encoded(manifest),immutable=True)
    assert {p.name for p in PKG.iterdir()}==set(names)|{'m411_mlp_binding.py','EXPECTED_VISUAL.json','PLAN.json','run_m414_mlp.sh','SHA256SUMS','PACKAGE_MANIFEST.json'}
    control=(HERE/'m413_control.ps1').read_text(encoding='utf-8').replace('M413','M414').replace('m413','m414')
    anchor="foreach ($key in @('latest_m409_reference_board'"
    assert control.count(anchor)==1
    control=control.replace(anchor,"VerifyEvidence 'latest_m413_layer12_visual_closure'\nVerifyEvidence 'latest_m413_original_reference_audit'\n"+anchor)
    atomic(HERE/'m414_control.ps1',control.encode('utf-8'),immutable=True)
    value=dict(status='PASS_M414_REFERENCE_ENTRY_REPAIR_PREPARATION_ONLY',recovery=recovery,
        manifest_sha256=sha(PKG/'PACKAGE_MANIFEST.json'),file_count=manifest['file_count'],total_bytes=manifest['total_bytes'],
        context_comparison_sha256=sha(context),entry_component_sha256=sha(entry),derivation_sha256=sha(BASE/'runs/M414-entry-derivation-01/RESULT.json'),
        WSL_outer_context_did_not_change_values=True,component_parent_state_unchanged=True,
        bounded_reference_artifact_checks=3,actual_component_checks=9,
        original_reference_before_Overlay=True,original_reference_and_thresholds_preserved=True,
        unchanged_binding_sha256=sha(PKG/'m411_mlp_binding.py'),prior_failure_sha256=b['latest_m413_layer12_visual_board']['sha256'],
        board_root_cause_proven=False,board_run=False,thresholds=THRESHOLDS,policy=POLICY,
        next_concrete_step='Single repaired entry: original visual/capture strict reference before Overlay; only if PASS unchanged layer12 PL candidate, no expansion.')
    out=BASE/'runs/M414-reference-entry-preparation-01/RESULT.json';atomic(out,encoded(value),immutable=True)
    sync('latest_m414_layer12_visual_preparation',dict(status=value['status'],result=out.relative_to(ROOT).as_posix(),sha256=sha(out),manifest_sha256=value['manifest_sha256']),
        f'## M414 原视觉参考入口隔离准备（2026-10-06）\n\nSHA {sha(out)}，原M413 FAIL {value["prior_failure_sha256"]}保持。冻结真实输入/运行时WSL两种上下文的全部特征和六capture逐位相同，不能认定外围上下文为板端根因。组件改独立CPU进程，真实父Torch RNG/线程/dtype不变，9组件与3有界失败数组检查通过；恢复旧调用边界，原版参考前移任何Overlay/分配之前。严格原SHA和六capture通过才第12层候选，失败先存七数组；0新板端/语义/性能/扩层，复用旧同SHA电路与生命周期。配套检查后直接同COM3执行一次修复入口。')
    print('M414_PREPARATION_SYNC',sha(out),value['manifest_sha256'],manifest['file_count'],manifest['total_bytes'])


if __name__=='__main__':main()
