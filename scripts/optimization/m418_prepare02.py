"""Immutable real saved-input lower gates; unchanged hardware prerequisites only."""
import ast,json,re,subprocess,sys
from m351_workflow import ROOT,BASE,HERE,atomic,encoded,sha,sync
from m418_workflow import PKG
def main():
    if PKG.exists():raise RuntimeError('Immutable package exists')
    recovery={n:dict(full_read=True,sha256=sha(ROOT/n),bytes=len((ROOT/n).read_text(encoding='utf-8-sig').encode('utf-8'))) for n in ('CURRENT_STATE.md','DEPLOYMENT_OPERATION_MISTAKES_REVIEW.md','docsMILESTONES.md')}
    b=json.loads((ROOT/'deployment/mage_vl4b/BOARD_GATE_RESULT.json').read_bytes())
    allocation_e=b['latest_m418_allocation_component']
    assert sha(ROOT/allocation_e['result'])==allocation_e['sha256']
    allocation=json.loads((ROOT/allocation_e['result']).read_bytes())
    assert allocation['source_sha256']==sha(HERE/'m418_probe.py') and allocation['status']=='PASS_M418_ACTUAL_OWNER_ALLOCATION_COMPONENT'
    assert all(allocation_e['sha256'] in (ROOT/n).read_text(encoding='utf-8-sig') for n in ('CURRENT_STATE.md','docsMILESTONES.md'))

    for key in ('latest_m407_visual_mlp_contract','latest_m407_visual_mlp_layout_closure','latest_m417_reference_board02','latest_m417_reference_closure02'):
        e=b[key];assert sha(ROOT/e['result'])==e['sha256'];assert all(e['sha256'] in (ROOT/n).read_text(encoding='utf-8-sig') for n in ('CURRENT_STATE.md','docsMILESTONES.md'))
    rawpath=ROOT/b['latest_m417_reference_board02']['result'];r=json.loads(rawpath.read_bytes());assert r['local_exact_arithmetic_screen_pass'] and r['logical_reference_calls']==26
    closure=BASE/'candidates/M403-tail-performance-01/HARDWARE_CLOSURE.json';hw=json.loads(closure.read_bytes())
    assert hw['status']=='PASS_ALL_NEW_CIRCUIT_PREREQUISITES' and hw['original_source_closure_unchanged']
    for row in hw['prerequisites']:assert sha(ROOT/row['path'])==row['sha256']
    old=BASE/'candidates/M357-private-activation-01';hd=sha(old/'PACKAGE_MANIFEST.json')
    assert hd=='2e9cbd00d0d01edf05e171674f71f86a94ce389a0658ce6c5466cebb77220d18'
    for row in json.loads((old/'PACKAGE_MANIFEST.json').read_bytes())['files']:assert (old/row['path']).stat().st_size==row['bytes'] and sha(old/row['path'])==row['sha256']
    t=subprocess.run([sys.executable,'-X','utf8','-B',str(HERE/'test_m418_component.py')],capture_output=True)
    if t.returncode:raise RuntimeError(t.stderr.decode('utf-8',errors='replace'))
    component=json.loads(re.search(r'(?m)^M418_COMPONENT=(.*)$',t.stdout.decode('utf-8'))[1])
    chains=json.loads((BASE/'candidates/M407-vision-MLP-isolated-01/MLP_CHAINS.json').read_bytes())['chains'];cases={}
    layout_folder=ROOT/'deployment/mage_vl4b/m181_m120_video_board_candidate/vision_layout'
    layout=json.loads((layout_folder/'SIXPORT_LAYOUT_MANIFEST.json').read_bytes())
    for mode,part in (('Descriptor','fc2'),('Chain','fc1')):
        chain=next(x for x in chains if x['module']==f'model.visual.encoder.layers.13.mlp.{part}');first=r['reference_batches'][part][0]
        assert 0<=first['selected_shift']<=first['initial_shift']<=6 and first['start']==0 and first['rows']==32 and chain['descriptor_count']==(1 if mode=='Descriptor' else 2)
        windows=[]
        for w in r['windows'][part]:
            p=layout_folder/w['path'];row=next(x for x in layout['files'] if x['path']==w['path'])
            assert p.stat().st_size==row['bytes'] and sha(p)==row['sha256']
            with p.open('rb') as f:f.seek(w['offset']);data=f.read(w['bytes'])
            assert __import__('hashlib').sha256(data).hexdigest()==w['sha256']
            windows.append(dict(w,relative_file=p.relative_to(ROOT).as_posix(),file_bytes=p.stat().st_size))
        cases[mode]=dict(part=part,chain=chain,shift=first['selected_shift'],windows=windows,saved_batch={k:first[k] for k in ('input_bytes','output_bytes','packet_sha256','raw_sha256')})
    base=ROOT/'deployment/mage_vl4b/m175_m120_fixed_text_candidate/runtime'
    sources=[dict(path=(base/n).relative_to(ROOT).as_posix(),sha256=sha(base/n)) for n in ('board_runtime.py','contract_runtime.py')]
    original=json.loads((old/'BOARD_CASES.json').read_bytes());assert sources[0]['sha256']==original['stable_sources']['runtime/board_runtime.py']['sha256']
    spec=dict(reference_directory='/home/ubuntu/m417_layer13_reference_02',reference_result_bytes=rawpath.stat().st_size,reference_raw_sha256=sha(rawpath),cases=cases,
        hardware_directory='/home/ubuntu/m357_candidate_01',hardware_manifest_sha256=hd,stable_sources=sources,build_config=original['build_config'],
        build_bytes=dict(packet_sha256=sha(old/'build_packet.bin'),raw_sha256=sha(old/'build_golden.bin'),input_bytes=(old/'build_packet.bin').stat().st_size,output_bytes=(old/'build_golden.bin').stat().st_size))
    PKG.mkdir()
    for n in ('m418_probe.py','m418_saved_case.py','m418_export.py','measurement.py','owned_buffer_release.py','board_safety.py'):
        data=(HERE/n).read_bytes();ast.parse(data,feature_version=(3,10));atomic(PKG/n,data,immutable=True)
    for n in ('m341_build_id_gate.py','m120_board_common.py','m120_board_env_preflight.py','m357_completion_observer.py','build_packet.bin','build_golden.bin'):
        data=(old/n).read_bytes()
        if n.endswith('.py'):ast.parse(data,feature_version=(3,10))
        atomic(PKG/n,data,immutable=True)
    atomic(PKG/'HARDWARE_CLOSURE.json',closure.read_bytes(),immutable=True);atomic(PKG/'BOARD_CASES.json',encoded(spec),immutable=True)
    runner='''#!/usr/bin/env bash
set -euo pipefail
[[ $EUID == 0 ]] || exit 65
cd "$(dirname "${BASH_SOURCE[0]}")"
task_manifest=${1:?manifest}
task_mode=${2:?Run or Collect}
task_gate=${3:?Descriptor or Chain}
[[ $task_gate == Descriptor || $task_gate == Chain ]] || exit 66
task_python=/usr/local/share/pynq-venv/bin/python
export PYTHONDONTWRITEBYTECODE=1
if [[ $task_mode == Collect ]]; then exec "$task_python" -B ./m418_export.py "$task_gate"; fi
[[ $task_mode == Run && ${M418_ENABLE_VISUAL:-0} == 1 ]] || exit 66
export XILINX_XRT=/usr TMPDIR=/dev/shm
export PATH=/usr/local/share/pynq-venv/bin:$PATH
printf '%s  PACKAGE_MANIFEST.json\\n' "$task_manifest" | sha256sum -c -
sha256sum -c SHA256SUMS
[[ ! -e /home/ubuntu/m418_visual_linear_01/$task_gate ]] || exit 67
task_args=("$task_manifest" "$task_gate" --enable-visual-linear-gate)
if [[ $task_gate == Chain ]]; then task_args+=(--prior-sha "${4:?prior raw}"); fi
set +e
"$task_python" -B ./m418_probe.py "${task_args[@]}"
task_gate_rc=$?
"$task_python" -B ./m418_export.py "$task_gate"
task_export_rc=$?
set -e
echo "M418_DONE gate_rc=$task_gate_rc export_rc=$task_export_rc"
if [[ $task_gate_rc != 0 ]]; then exit "$task_gate_rc"; fi
exit "$task_export_rc"
'''
    atomic(PKG/'run_m418_visual.sh',runner.encode('utf-8'),immutable=True)
    files=sorted(PKG.iterdir());atomic(PKG/'SHA256SUMS',''.join(f'{sha(p)}  {p.name}\n' for p in files).encode('ascii'),immutable=True)
    files=sorted(PKG.iterdir());m=dict(file_count=len(files),total_bytes=sum(p.stat().st_size for p in files),files=[dict(path=p.name,bytes=p.stat().st_size,sha256=sha(p)) for p in files]);atomic(PKG/'PACKAGE_MANIFEST.json',encoded(m),immutable=True)
    p=BASE/'runs/M418-visual-linear-preparation-01/RESULT.json';v=dict(status='PASS_M418_SAVED_VISUAL_LOWER_GATE_PREPARATION',recovery=recovery,reference_raw_sha256=sha(rawpath),unchanged_hardware_closure_sha256=sha(closure),reused_hardware_prerequisites=hw['prerequisites'],
        manifest_sha256=sha(PKG/'PACKAGE_MANIFEST.json'),file_count=m['file_count'],total_bytes=m['total_bytes'],component=component,allocation_component=allocation,allocation_component_sha256=allocation_e['sha256'],board_run=False,performance_pass=False,
        source_sha256={n:sha(HERE/n) for n in ('m418_prepare02.py','m418_probe.py','m418_saved_case.py','m418_export.py','test_m418_component.py','m418_workflow.py','m418_control02.ps1')})
    atomic(p,encoded(v),immutable=True)
    sync('latest_m418_visual_linear_preparation',dict(status=v['status'],result=p.relative_to(ROOT).as_posix(),sha256=sha(p),manifest_sha256=v['manifest_sha256']),
        f'## M418 已保存视觉MLP最小硬件用例准备（2026-10-06）\n\nSHA {sha(p)}；冻结原M417输入/完整FTZ输出及四W4窗口，复用原并行Build0x4D333537同SHA11项电路证据。默认关闭单fc2 descriptor→fc1双descriptor chain，每次同Overlay合法minimal后执行，原稳定恢复。真实保存/原pack与七项明确fake DMA生命周期、损坏拒绝和普通PS容量停止通过；诊断取消固定CMA64MiB floor，实际分配失败停止，DMA安全和生产政策保持；尚未上板，不是完整MLP/净时间或24层质量证据。')
    print('M418_PREPARED',sha(p),v['manifest_sha256'],m['file_count'],m['total_bytes'])
if __name__=='__main__':main()
