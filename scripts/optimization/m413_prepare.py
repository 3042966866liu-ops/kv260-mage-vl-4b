"""One isolated selected-layer full-visual quality package; no UART."""
import ast,json,subprocess
from m351_workflow import ROOT,BASE,HERE,atomic,encoded,sha,sync
from m413_workflow import PKG
from m413_quality import THRESHOLDS
from m413_policy import POLICY
def main():
    if PKG.exists():raise RuntimeError('Immutable package already exists')
    recovery={name:dict(sha256=sha(ROOT/name),full_read=True,characters=len((ROOT/name).read_text(encoding='utf-8-sig'))) for name in ('CURRENT_STATE.md','DEPLOYMENT_OPERATION_MISTAKES_REVIEW.md','docsMILESTONES.md','deployment/mage_vl4b/BOARD_GATE_RESULT.json')}
    board=json.loads((ROOT/'deployment/mage_vl4b/BOARD_GATE_RESULT.json').read_bytes())
    for key in ('latest_m412_complete_mlp_board','latest_m412_complete_mlp_closure','latest_m410_visual_lower_closure','latest_m409_reference_closure','latest_m368_video_closure'):
        row=board[key];assert sha(ROOT/row['result'])==row['sha256'];assert all(row['sha256'] in (ROOT/n).read_text(encoding='utf-8-sig') for n in ('CURRENT_STATE.md','docsMILESTONES.md'))
    local=json.loads((ROOT/board['latest_m412_complete_mlp_board']['result']).read_bytes())
    assert local['numerical_pass'] and local['performance_pass'] and local['stable_restored'] and local['safe_buffers_released']
    source=BASE/'candidates/M412-complete-visual-MLP-01';plan=json.loads((source/'PLAN.json').read_bytes())
    for row in plan['reused_packages']:
        old=BASE/'candidates'/('M410-visual-linear-01' if 'm410' in row['directory'] else 'M409-saved-MLP-reference-01')
        assert sha(old/'PACKAGE_MANIFEST.json')==row['manifest_sha256']
        for item in json.loads((old/'PACKAGE_MANIFEST.json').read_bytes())['files']:assert sha(old/item['path'])==item['sha256']
    plan.update(scope='Only selected layer12 two Linear in complete original visual forward; unchanged first2 BF16/Attention/GELU/norm/other23 layers/input/language. Feature quality only, not recognition accuracy or performance.',
                previous_local_result='/home/ubuntu/m412_complete_mlp_01/BOARD_RESULT.json',previous_local_raw_sha256=board['latest_m412_complete_mlp_board']['sha256'],
                protocol=dict(original_full_visual_calls=1,candidate_full_visual_calls=1,additional_replay_or_timing=False,feature_thresholds=THRESHOLDS,
                              original_SHA_required=True,complete26_selected_layer_wire_reference_required=True,stop_on_screen_or_lifecycle_failure=True),
                PS_transient_bytes=768<<20,independent_admission=POLICY,full_visual_or_language_forward='visual only',allow_expand_24_layers=False,
                resolved_module_names=['ps_vision_runtime','m206_ps_vision_runtime','m207_ps_vision_runtime','m222_vectorized_w4_runtime','m258_vectorized_w4_runtime','m259_variable_vision_runtime','m260_cached_w4_runtime','m261_budgeted_w4_runtime','m273_latest_vision_runtime','m273_latest_multiscale_contract','contract_runtime'],
                PS_budget_basis='Retain768MiB original full-visual PS budget from M368 plus64MiB ordinary reserve; capture bounded32MiB, two final features<3MiB, existing cache26/66699264B; sampled layer and transaction boundaries, not continuous native peak.',
                user_authorization='2026-10-06: 先完成第12层接入后的完整视觉质量闭合，再决定扩大范围',
                earlier_M62_scope_correction='Actual M62 host full-model351 hooked modules/three temporal synthetic cases failed1; not isolated visual-MLP board evidence and not attributable to this change. Preserve priorFAIL.')
    capture=BASE/'runs/M413-component-02';capture.mkdir(parents=True,exist_ok=True)
    test=subprocess.run(['wsl.exe','-d','Ubuntu-24.04','--','/home/lyy/projects/qwen_baseline/.venv/bin/python','-B','/mnt/c/Users/30429/Desktop/TeLLMe_FPGA_2026/scripts/optimization/test_m413_quality.py'],capture_output=True,timeout=120)
    atomic(capture/'STDOUT.txt',test.stdout,immutable=True);atomic(capture/'STDERR.txt',test.stderr,immutable=True)
    if test.returncode:raise RuntimeError('Actual full-visual insertion fixture failed: '+test.stderr.decode('utf-8',errors='replace'))
    component=json.loads(next(x.split('=',1)[1] for x in test.stdout.decode('utf-8').splitlines() if x.startswith('M413_COMPONENT=')))
    component.update(status='PASS_M413_ACTUAL_TORCH_SELECTED_LAYER_INTEGRATION_COMPONENT',platform='WSL CPU fixtures only',command_return_code=test.returncode,
                     stdout_sha256=sha(capture/'STDOUT.txt'),source_files_sha256={n:sha(HERE/n) for n in ('test_m413_quality.py','m413_quality.py','m413_policy.py')})
    atomic(capture/'RESULT.json',encoded(component),immutable=True)
    PKG.mkdir()
    names=('m413_gate.py','m413_policy.py','m413_quality.py','m413_export.py','test_m413_quality.py')
    for name in names:
        raw=(HERE/name).read_bytes();ast.parse(raw,feature_version=(3,10));atomic(PKG/name,raw,immutable=True)
    atomic(PKG/'m411_mlp_binding.py',(source/'m411_mlp_binding.py').read_bytes(),immutable=True)
    atomic(PKG/'EXPECTED_VISUAL.json',(BASE/'candidates/M409-saved-MLP-reference-01/EXPECTED.json').read_bytes(),immutable=True)
    atomic(PKG/'PLAN.json',encoded(plan),immutable=True)
    runner=(source/'run_m412_mlp.sh').read_text(encoding='utf-8').replace('M412','M413').replace('m412_complete_mlp_01','m413_layer12_full_visual_01').replace('m412','m413').replace('--enable-complete-MLP-gate','--enable-layer12-visual-quality')
    atomic(PKG/'run_m413_mlp.sh',runner.encode('utf-8'),immutable=True)
    files=sorted(PKG.iterdir());atomic(PKG/'SHA256SUMS',''.join(f'{sha(p)}  {p.name}\n' for p in files).encode('ascii'),immutable=True)
    files=sorted(PKG.iterdir());manifest=dict(file_count=len(files),total_bytes=sum(p.stat().st_size for p in files),files=[dict(path=p.name,bytes=p.stat().st_size,sha256=sha(p)) for p in files]);atomic(PKG/'PACKAGE_MANIFEST.json',encoded(manifest),immutable=True)
    assert not list(PKG.rglob('*.pyc')) and not list(PKG.rglob('__pycache__'))
    # Exact clean routing derived from last tested controller; no package-path inference.
    control=(HERE/'m412_control.ps1').read_text(encoding='utf-8').replace('M412','M413').replace('m412','m413')
    control=control.replace('M413-complete-visual-MLP-01','M413-layer12-full-visual-01').replace('m413_complete_mlp_candidate_01','m413_layer12_visual_candidate_01').replace('M413-complete-MLP-board-01','M413-layer12-visual-board-01')
    control=control.replace('latest_m413_complete_mlp','latest_m413_layer12_visual')
    control=control.replace("'latest_m411_complete_mlp_capacity_closure'", "'latest_m412_complete_mlp_board','latest_m412_complete_mlp_closure'")
    atomic(HERE/'m413_control.ps1',control.encode('utf-8'))
    v=dict(status='PASS_M413_LAYER12_FULL_VISUAL_PREPARATION_ONLY',recovery=recovery,component_sha256=sha(capture/'RESULT.json'),
           manifest_sha256=sha(PKG/'PACKAGE_MANIFEST.json'),file_count=manifest['file_count'],total_bytes=manifest['total_bytes'],
           inverse_AST_source_diff_sha256=sha(BASE/'runs/M413-source-diff-03/RESULT.json'),actual_component=component,
           unchanged_binding_sha256=sha(PKG/'m411_mlp_binding.py'),prior_M412_raw_sha256=plan['previous_local_raw_sha256'],
           thresholds=THRESHOLDS,policy=POLICY,hardware_run=False,semantic_quality_proven=False,expanded_24_layers=False,
           source_sha256={n:sha(HERE/n) for n in ('m413_prepare.py','m413_generate.py','m413_gate.py','m413_quality.py','m413_policy.py','m413_workflow.py','m413_control.ps1')})
    p=BASE/'runs/M413-layer12-visual-preparation-01/RESULT.json';atomic(p,encoded(v),immutable=True)
    sync('latest_m413_layer12_visual_preparation',dict(status=v['status'],result=p.relative_to(ROOT).as_posix(),sha256=sha(p),manifest_sha256=v['manifest_sha256']),
         f'## M413 第12层接入完整视觉质量准备（2026-10-06）\n\nSHA {sha(p)}；M412完整局部数值/净时间闭合后只原第12层MLP接入。真实Torch24层包装/原Encoder及392行26包、两处绑定/恢复与9拒绝fixture通过，明确Attention/权重/PL为替身，非模型质量。原版1次视觉先原SHA，再候选1次完整视觉最终98×2560特征；相对L2≤2%/cos≥.999/min-token≥.995仅筛选，0语言/性能/24层扩展。实际七DMA3.281265MiB分配后封锁新增，CMA不设64门槛；完整视觉普通PS768MiB预算。原35SHA/49源码/输入/其他路径保持，配套控制回收通过才上板。')
    print('M413_PREPARED',sha(p),v['manifest_sha256'],manifest['file_count'],manifest['total_bytes'])
if __name__=='__main__':main()
