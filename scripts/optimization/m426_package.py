"""Freeze checked CPU-only software packet after independent oracle component."""
import ast,json,subprocess
from m351_workflow import ROOT,BASE,HERE,atomic,encoded,sha,sync
from m426_prepare import PKG
def main():
    board=json.loads((ROOT/'deployment/mage_vl4b/BOARD_GATE_RESULT.json').read_bytes())
    for key in ('latest_m426_range_protocol','latest_m426_range_component'):
        e=board[key];assert sha(ROOT/e['result'])==e['sha256'] and all(e['sha256'] in (ROOT/n).read_text(encoding='utf-8-sig') for n in ('CURRENT_STATE.md','docsMILESTONES.md'))
    component=json.loads((ROOT/board['latest_m426_range_component']['result']).read_bytes())
    for n in ('m426_range.py','test_m426_range.py'):assert sha(HERE/n)==component['staged_sources'][n]
    protocol=json.loads((ROOT/board['latest_m426_range_protocol']['result']).read_bytes());plan=protocol['plan']
    old=BASE/'candidates/M420-layers12-13-full-visual-02';ref=BASE/'candidates/M417-layer13-saved-reference-02'
    locals=('M417-layer13-saved-reference-02','M418-visual-linear-01','M409-saved-MLP-reference-01','M410-visual-linear-01','M414-layer12-full-visual-01')
    for name,row in zip(locals,plan['reused_packages']):
        p=BASE/'candidates'/name;assert sha(p/'PACKAGE_MANIFEST.json')==row['manifest_sha256'];m=json.loads((p/'PACKAGE_MANIFEST.json').read_bytes())
        for f in m['files']:assert sha(p/f['path'])==f['sha256']
    if PKG.exists():raise RuntimeError('Packet immutable')
    PKG.mkdir()
    for n in ('m426_gate.py','m426_range.py','m426_export.py'):
        text=(HERE/n).read_text(encoding='utf-8');ast.parse(text,feature_version=(3,10))
        assert not any(x in text for x in ('import pynq','from pynq','/sys/class/thermal','/sys/class/hwmon','/sys/bus/iio','drop_caches','posix_fadvise'))
        atomic(PKG/n,(HERE/n).read_bytes(),immutable=True)
    atomic(PKG/'PLAN.json',encoded(plan),immutable=True)
    atomic(PKG/'SOURCE_IDENTITIES.json',(ref/'M348_SOURCE_IDENTITIES.json').read_bytes(),immutable=True)
    atomic(PKG/'EXPECTED_VISUAL.json',(old/'EXPECTED_VISUAL.json').read_bytes(),immutable=True)
    runner='''#!/usr/bin/env bash
set -euo pipefail
[[ $EUID == 0 ]] || exit 65
cd "$(dirname "${BASH_SOURCE[0]}")"
task_manifest=${1:?manifest}
task_mode=${2:?Run or Collect}
task_python=/usr/local/share/pynq-venv/bin/python
export PYTHONDONTWRITEBYTECODE=1
if [[ $task_mode == Collect ]]; then exec "$task_python" -B ./m426_export.py; fi
[[ $task_mode == Run && ${M426_ENABLE_SOFTWARE_RANGE:-0} == 1 ]] || exit 66
printf '%s  PACKAGE_MANIFEST.json\\n' "$task_manifest" | sha256sum -c -
sha256sum -c SHA256SUMS
[[ ! -e /home/ubuntu/m426_range_software_01 ]] || exit 67
set +e
"$task_python" -B ./m426_gate.py "$task_manifest" --enable-software-range
task_gate_rc=$?
"$task_python" -B ./m426_export.py
task_export_rc=$?
set -e
echo "M426_DONE gate_rc=$task_gate_rc export_rc=$task_export_rc"
if [[ $task_gate_rc != 0 ]]; then exit "$task_gate_rc"; fi
exit "$task_export_rc"
'''
    atomic(PKG/'run_m426.sh',runner.encode('utf-8'),immutable=True)
    files=sorted(PKG.iterdir());atomic(PKG/'SHA256SUMS',''.join(f'{sha(p)}  {p.name}\n' for p in files).encode('ascii'),immutable=True)
    files=sorted(PKG.iterdir());manifest=dict(file_count=len(files),total_bytes=sum(p.stat().st_size for p in files),files=[dict(path=p.name,bytes=p.stat().st_size,sha256=sha(p)) for p in files]);atomic(PKG/'PACKAGE_MANIFEST.json',encoded(manifest),immutable=True)
    gate=(PKG/'m426_gate.py').read_text(encoding='utf-8')
    assert gate.index("if identities.get(rel)!=digest(p)")<gate.index('runtime=M273LatestPSVisionRuntime')
    assert gate.index("if result['original_visual']!=expected['visual']")<gate.index("candidate=vision('software'")
    # Parse the runner locally; no hardware attempt is used for syntax discovery.
    cp=subprocess.run(['wsl.exe','-d','Ubuntu-24.04','--','/bin/bash','-n','/mnt/c/Users/30429/Desktop/TeLLMe_FPGA_2026/'+(PKG/'run_m426.sh').relative_to(ROOT).as_posix()],capture_output=True)
    atomic(ROOT/'tmp/m42601/bash.stdout.bin',cp.stdout,immutable=True);atomic(ROOT/'tmp/m42601/bash.stderr.bin',cp.stderr,immutable=True)
    if cp.returncode:raise RuntimeError('Runner syntax refused')
    r=dict(status='PREPARED_M426_ALL22_CPU_SOFTWARE_FEATURE_SCREEN',manifest_sha256=sha(PKG/'PACKAGE_MANIFEST.json'),
        files=manifest['file_count'],bytes=manifest['total_bytes'],protocol_sha256=board['latest_m426_range_protocol']['sha256'],
        component_sha256=board['latest_m426_range_component']['sha256'],unchanged_oracle_sha256=sha(ref/'m409_ftz_reference.py'),
        Python310_syntax=True,runner_bash_n=True,original_feature_SHA_before_candidate=True,source_check_before_constructor=True,
        no_Overlay_DMA_language_or_temperature=True,board_run=False,feature_screen_pass=False,task_screen_pass=False,performance_pass=False)
    out=BASE/'runs/M426-range-preparation-01/RESULT.json';atomic(out,encoded(r),immutable=True)
    sync('latest_m426_range_preparation',dict(status=r['status'],result=out.relative_to(ROOT).as_posix(),sha256=sha(out),manifest_sha256=r['manifest_sha256'],board_run=False,performance_pass=False),f'## M426 22层软件完整视觉质量包（2026-10-06）\n\nSHA {sha(out)}；{r["files"]}载荷/{r["bytes"]}B，manifest {r["manifest_sha256"]}。原精确算术同SHA、源检查在构造前、固定原feature SHA在候选前，Python3.10/bash-n通过。0候选PL/语言/测温；特征通过后仍需保存特征的原语言任务核对，尚未解锁视觉硬件计时。')
    print('M426_PACKAGE_SYNC',sha(out),r['manifest_sha256'],r['files'],r['bytes'])
if __name__=='__main__':main()
