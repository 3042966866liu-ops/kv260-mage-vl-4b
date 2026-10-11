"""Freeze saved-only PS oracle from successful exact capture; immutable stage."""
import ast,json,re,subprocess
from m351_workflow import ROOT,BASE,HERE,atomic,encoded,sha,sync
from m409_workflow import PKG

def main():
    if PKG.exists():raise RuntimeError('Immutable package exists')
    recovery={n:dict(full_read=True,sha256=sha(ROOT/n),bytes=len((ROOT/n).read_text(encoding='utf-8-sig').encode('utf-8'))) for n in ('CURRENT_STATE.md','DEPLOYMENT_OPERATION_MISTAKES_REVIEW.md','docsMILESTONES.md')}
    b=json.loads((ROOT/'deployment/mage_vl4b/BOARD_GATE_RESULT.json').read_bytes())
    for k in ('latest_m407_visual_mlp_contract','latest_m407_visual_mlp_layout_closure','latest_m408_local_mlp_board04','latest_m408_local_mlp_closure04'):
        e=b[k];assert sha(ROOT/e['result'])==e['sha256']
        assert all(e['sha256'] in (ROOT/n).read_text(encoding='utf-8-sig') for n in ('CURRENT_STATE.md','docsMILESTONES.md'))
    raw=json.loads((ROOT/b['latest_m408_local_mlp_board04']['result']).read_bytes())
    assert raw['local_A8_screen_pass'] and raw['visual_owner_closed'] and raw['bindings_restored']
    test=subprocess.run([__import__('sys').executable,'-X','utf8','-B',str(HERE/'test_m409_ftz_reference.py')],capture_output=True)
    if test.returncode:raise RuntimeError(test.stderr.decode('utf-8',errors='replace'))
    pure=json.loads(test.stdout.decode('utf-8'))
    test=subprocess.run(['wsl.exe','-d','Ubuntu-24.04','--','/home/lyy/projects/qwen_baseline/.venv/bin/python','-B','/mnt/c/Users/30429/Desktop/TeLLMe_FPGA_2026/scripts/optimization/m409_torch_component.py'],capture_output=True)
    if test.returncode:raise RuntimeError(test.stderr.decode('utf-8',errors='replace'))
    torch=json.loads(re.search(r'(?m)^M409_TORCH_COMPONENT=(.*)$',test.stdout.decode('utf-8'))[1])
    assert torch['invalid_native_inputs_rejected']==4 and torch['independent_int32_full_output_equal'] and torch['bindings_restored']
    old=BASE/'candidates/M408-local-MLP-A8-capture-04';assert sha(old/'PACKAGE_MANIFEST.json')=='f7376efecdcecebd120f669d770bc4fef5d76f8c82e36082d7fc69c35b6bdc1d'
    PKG.mkdir()
    for row in json.loads((old/'PACKAGE_MANIFEST.json').read_bytes())['files']:
        assert sha(old/row['path'])==row['sha256']
        if row['path'] not in ('SHA256SUMS','run_m408_capture.sh'):atomic(PKG/row['path'],(old/row['path']).read_bytes(),immutable=True)
    for n in ('m409_gate.py','m409_ftz_reference.py','m409_torch_component.py','test_m409_ftz_reference.py','m355_reference.py','m120_group_reference.py'):
        blob=(HERE/n).read_bytes();ast.parse(blob,feature_version=(3,10));atomic(PKG/n,blob,immutable=True)
    atomic(PKG/'MLP_CHAINS.json',(BASE/'candidates/M407-vision-MLP-isolated-01/MLP_CHAINS.json').read_bytes(),immutable=True)
    expected={k:raw[k] for k in ('capture_manifest','capture','target_matrices','target_resolution')};expected['raw_sha256']=b['latest_m408_local_mlp_board04']['sha256']
    atomic(PKG/'M408_CAPTURE_EXPECTED.json',encoded(expected),immutable=True)
    runner='''#!/usr/bin/env bash
set -euo pipefail
[[ $EUID == 0 ]] || exit 65
cd "$(dirname "${BASH_SOURCE[0]}")"
task_manifest=${1:?manifest}
task_mode=${2:?Run or Collect}
task_python=/usr/local/share/pynq-venv/bin/python
export PYTHONDONTWRITEBYTECODE=1
if [[ $task_mode == Collect ]]; then exec "$task_python" -B ./m409_gate.py Collect; fi
[[ $task_mode == Run && ${M409_ENABLE_REFERENCE:-0} == 1 ]] || exit 66
printf '%s  PACKAGE_MANIFEST.json\\n' "$task_manifest" | sha256sum -c -
sha256sum -c SHA256SUMS
[[ ! -e /home/ubuntu/m409_mlp_reference_01 ]] || exit 67
set +e
"$task_python" -B ./m409_gate.py "$task_manifest" --enable-saved-MLP-reference
task_gate_rc=$?
"$task_python" -B ./m409_gate.py Collect
task_export_rc=$?
set -e
echo "M409_DONE gate_rc=$task_gate_rc export_rc=$task_export_rc"
if [[ $task_gate_rc != 0 ]]; then exit "$task_gate_rc"; fi
exit "$task_export_rc"
'''
    atomic(PKG/'run_m409_reference.sh',runner.encode('utf-8'),immutable=True)
    files=sorted(PKG.iterdir());atomic(PKG/'SHA256SUMS',''.join(f'{sha(p)}  {p.name}\n' for p in files).encode('ascii'),immutable=True)
    files=sorted(PKG.iterdir());m=dict(file_count=len(files),total_bytes=sum(p.stat().st_size for p in files),files=[dict(path=p.name,bytes=p.stat().st_size,sha256=sha(p)) for p in files]);atomic(PKG/'PACKAGE_MANIFEST.json',encoded(m),immutable=True)
    control=(HERE/'m408_control06.ps1').read_text(encoding='utf-8')
    for a,c in [('M408-local-MLP-A8-capture-04','M409-saved-MLP-reference-01'),('m408_local_mlp_candidate_04','m409_mlp_reference_candidate_01'),('latest_m408_local_mlp_preparation04','latest_m409_reference_preparation'),('latest_m408_local_mlp_support04','latest_m409_reference_support'),('latest_m408_local_mlp_transfer04','latest_m409_reference_transfer'),('m408_workflow04.py','m409_workflow.py'),('tmp/m40804','tmp/m40901'),('M408-local-MLP-A8-board-04','M409-reference-board-01'),('latest_m408_native_shape_failure_closure','latest_m408_local_mlp_closure04'),('run_m408_capture.sh','run_m409_reference.sh'),('M408_ENABLE_LOCAL_MLP','M409_ENABLE_REFERENCE'),('M408','M409')]:
        if a not in control:raise RuntimeError('Controller replacement missing '+a)
        control=control.replace(a,c)
    # New reference requires the already verified real capture, not a repeat capture.
    control=control.replace("'latest_m408_local_mlp_closure04',","'latest_m408_local_mlp_closure04','latest_m408_local_mlp_board04',")
    control=control.replace('-TimeoutSeconds 780','-TimeoutSeconds 1080')
    atomic(HERE/'m409_control.ps1',control.encode('utf-8'),immutable=True)
    p=BASE/'runs/M409-reference-preparation-01/RESULT.json'
    value=dict(status='PASS_M409_SAVED_INPUT_SOFTWARE_REFERENCE_PREPARATION',recovery=recovery,capture_raw_sha256=expected['raw_sha256'],capture_manifest_sha256=expected['capture_manifest']['sha256'],
        manifest_sha256=sha(PKG/'PACKAGE_MANIFEST.json'),file_count=m['file_count'],total_bytes=m['total_bytes'],pure_algorithm_component=pure,real_Torch_small_component=torch,
        board_run=False,PL_hardware_proven=False,performance_pass=False,source_sha256={n:sha(HERE/n) for n in ('m409_prepare.py','m409_gate.py','m409_ftz_reference.py','m409_torch_component.py','test_m409_ftz_reference.py','m409_workflow.py','m409_control.ps1')})
    atomic(p,encoded(value),immutable=True)
    sync('latest_m409_reference_preparation',dict(status=value['status'],result=p.relative_to(ROOT).as_posix(),sha256=sha(p),manifest_sha256=value['manifest_sha256']),
        f'## M409 原捕获输入精确软件参考准备（2026-10-05）\n\nSHA {sha(p)}；默认关闭，复用M408已保存六张量，不再视觉捕获。原T32/缩放重试、顺序FP32/FP16/FTZ与独立整数小fixture、真实Torch原M207/Siglip GELU/三维接口/四拒绝/恢复通过，仅组件。保留原35全SHA及49源码，板端只构造PS对象与两局部回放，0Overlay/DMA/语言。实际控制/回收配套检查后一次精确误差筛选；未上板、非性能。')
    print('M409_PREPARED',sha(p),value['manifest_sha256'],m['file_count'],m['total_bytes'])
if __name__=='__main__':main()
