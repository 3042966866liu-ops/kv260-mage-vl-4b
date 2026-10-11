"""Only new four Python files plus a pinned reuse plan; no hardware repack."""
import ast,json
from m351_workflow import ROOT,BASE,HERE,atomic,encoded,sha,sync
from m411_workflow import PKG
def main():
    if PKG.exists():raise RuntimeError('Immutable package exists')
    recovery={n:dict(full_read=True,sha256=sha(ROOT/n),bytes=len((ROOT/n).read_text(encoding='utf-8-sig').encode('utf-8'))) for n in ('CURRENT_STATE.md','DEPLOYMENT_OPERATION_MISTAKES_REVIEW.md','docsMILESTONES.md')}
    board=json.loads((ROOT/'deployment/mage_vl4b/BOARD_GATE_RESULT.json').read_bytes())
    for key in ('latest_m409_reference_board','latest_m409_reference_closure','latest_m410_visual_descriptor','latest_m410_visual_chain','latest_m410_visual_lower_closure'):
        e=board[key];assert sha(ROOT/e['result'])==e['sha256'];assert all(e['sha256'] in (ROOT/n).read_text(encoding='utf-8-sig') for n in ('CURRENT_STATE.md','docsMILESTONES.md'))
    reuse=[]
    for name,remote,expected in [('M410-visual-linear-01','/home/ubuntu/m410_visual_linear_candidate_01','2872d62096da83f4aaf1428a9d9b25eb4ee389ce3be255f48ef49a556c12333e'),('M409-saved-MLP-reference-01','/home/ubuntu/m409_mlp_reference_candidate_01','002799969645d1e3da1b8254cd1f79c113cf11a8daa7cb2c494a8937868a64ac')]:
        p=BASE/'candidates'/name;assert sha(p/'PACKAGE_MANIFEST.json')==expected
        for row in json.loads((p/'PACKAGE_MANIFEST.json').read_bytes())['files']:assert sha(p/row['path'])==row['sha256']
        reuse.append(dict(directory=remote,manifest_sha256=expected))
    plan=dict(default_off=True,reused_packages=reuse,lower_package=reuse[0]['directory'],reference_package=reuse[1]['directory'],chain_result='/home/ubuntu/m410_visual_linear_01/Chain/BOARD_RESULT.json',chain_raw_sha256=board['latest_m410_visual_chain']['sha256'],
        reference_result=board['latest_m409_reference_board']['result'],reference_raw_sha256=board['latest_m409_reference_board']['sha256'],original_plan_sha256=sha(BASE/'candidates/M407-vision-MLP-isolated-01/CANDIDATE_PLAN.json'),
        selected_layer=12,rows=392,sequential_original_GELU_and_PS_bias=True,seven_DMA_payload_bytes=3440656,actual_CMA_reserve_bytes=64<<20,PS_transient_bytes=256<<20,PS_constructor_budget_bytes=1<<30,PS_extra_reserve_bytes=64<<20,
        protocol=dict(numerical_CPU_segments=1,numerical_PL_segments=1,warmups='AB',timed_order='ABBABAAB',timed_segments=8,minimum_mean_gain=.05,both_group_mean_saved_exceeds_max_within_variant_range=True,
            boundary='before first original weight decode/read through fc1+bias/originalGELU/fc2+bias PS-usable output; include all quantization/packing/staging/sync/DMA/wait/retry/parse/conversions; output checks and hashes outside timed segments',cache='natural shared cache; no eviction; keep every segment read_bytes/rchar and memory',backend='original constructor settings, fixed across both branches',extra_sampling=False),
        full_visual_or_language_forward=False,allow_expand_24_layers=False,scope='isolated original M273 constructed MLP; only the two instance Linear forwards change for PL branch; no service/boot/DTB/CMA/stable source changes')
    component=dict(actual_Torch_M207_Siglip_GELU=True,native392_rows_and_original_T32_32_8=True,full_software_reference_equal=True,finite_original_retry=True,bindings_restored_on_all_failures=True,negative_checks=6,actual_four_file_read_copy_sync=True,predeclared_order_noise_5percent_rejections=True,submit_explicit_PS_software_substitute=True,buffer_sync_explicit_fake=True,real_model_quality_or_PL=False,performance_evidence=False)
    PKG.mkdir()
    for n in ('m411_gate.py','m411_mlp_binding.py','m411_export.py','test_m411_binding.py'):
        raw=(HERE/n).read_bytes();ast.parse(raw,feature_version=(3,10));atomic(PKG/n,raw,immutable=True)
    atomic(PKG/'PLAN.json',encoded(plan),immutable=True)
    runner='''#!/usr/bin/env bash
set -euo pipefail
[[ $EUID == 0 ]] || exit 65
cd "$(dirname "${BASH_SOURCE[0]}")"
task_manifest=${1:?manifest}
task_mode=${2:?Run or Collect}
task_python=/usr/local/share/pynq-venv/bin/python
export PYTHONDONTWRITEBYTECODE=1
if [[ $task_mode == Collect ]]; then exec "$task_python" -B ./m411_export.py; fi
[[ $task_mode == Run && ${M411_ENABLE_MLP:-0} == 1 ]] || exit 66
export XILINX_XRT=/usr TMPDIR=/dev/shm
export PATH=/usr/local/share/pynq-venv/bin:$PATH
printf '%s  PACKAGE_MANIFEST.json\\n' "$task_manifest" | sha256sum -c -
sha256sum -c SHA256SUMS
[[ ! -e /home/ubuntu/m411_complete_mlp_01 ]] || exit 67
set +e
"$task_python" -B ./m411_gate.py "$task_manifest" --enable-complete-MLP-gate
task_gate_rc=$?
"$task_python" -B ./m411_export.py
task_export_rc=$?
set -e
echo "M411_DONE gate_rc=$task_gate_rc export_rc=$task_export_rc"
if [[ $task_gate_rc != 0 ]]; then exit "$task_gate_rc"; fi
exit "$task_export_rc"
'''
    atomic(PKG/'run_m411_mlp.sh',runner.encode('utf-8'),immutable=True)
    files=sorted(PKG.iterdir());atomic(PKG/'SHA256SUMS',''.join(f'{sha(p)}  {p.name}\n' for p in files).encode('ascii'),immutable=True)
    files=sorted(PKG.iterdir());manifest=dict(file_count=len(files),total_bytes=sum(p.stat().st_size for p in files),files=[dict(path=p.name,bytes=p.stat().st_size,sha256=sha(p)) for p in files]);atomic(PKG/'PACKAGE_MANIFEST.json',encoded(manifest),immutable=True)
    p=BASE/'runs/M411-complete-MLP-preparation-01/RESULT.json';v=dict(status='PASS_M411_COMPLETE_MLP_PREPARATION_ONLY',recovery=recovery,manifest_sha256=sha(PKG/'PACKAGE_MANIFEST.json'),file_count=manifest['file_count'],total_bytes=manifest['total_bytes'],real_Torch_small_component=component,component_platform='WSL CPU, not KV260 or actual input quality/performance',
        component_source_sha256=sha(HERE/'test_m411_binding.py'),protocol=plan['protocol'],seven_buffers_payload_bytes=3440656,board_run=False,performance_pass=False,expanded_24_layers=False,
        source_sha256={n:sha(HERE/n) for n in ('m411_prepare.py','m411_gate.py','m411_mlp_binding.py','m411_export.py','test_m411_binding.py','m411_workflow.py','m411_control.ps1')})
    atomic(p,encoded(v),immutable=True)
    sync('latest_m411_complete_mlp_preparation',dict(status=v['status'],result=p.relative_to(ROOT).as_posix(),sha256=sha(p),manifest_sha256=v['manifest_sha256']),
        f'## M411 完整原视觉MLP段准备（2026-10-06）\n\nSHA {sha(p)}；两M410硬件级闭合后，默认关闭原第12层392行fc1→原GELU→fc2。真实Torch392行小fixture/原M207/Siglip及T32尾批/全软件参考/六拒绝/恢复与真实四文件读拷贝同步通过，仅CPU组件。原35完整SHA与49源码、M273构造、七DMA3,440,656B及真实64MiB CMA/PS预算保持。先完整wire与输出数值，再各AB预热一次及固定ABBABAAB8完整段，所有准备/转换/传输/解析/GELU/bias计入；不加样、不扩24层，尚未上板。')
    print('M411_PREPARED',sha(p),v['manifest_sha256'],manifest['file_count'],manifest['total_bytes'])
if __name__=='__main__':main()
