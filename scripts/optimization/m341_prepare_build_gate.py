"""Prepare a stable-only Build-ID gate, leaving the prefetch candidate unlaunched."""
import ast
import hashlib
import json
import os
from pathlib import Path
import shutil
ROOT=Path(__file__).resolve().parents[2]
HERE=Path(__file__).resolve().parent
BASE=ROOT/'deployment/mage_vl4b/optimization_v1'


def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()


def atomic(path,data):
    part=path.with_name(path.name+'.m341-part');part.write_bytes(data);os.replace(part,path)


def once(text,old,new):
    if text.count(old)!=1:raise RuntimeError('Derivation context mismatch '+old)
    return text.replace(old,new)


def main():
    package=BASE/'candidates/M341-build-id-01'
    run=BASE/'runs/M341-build-id-preparation-01'
    if package.exists() or run.exists():raise RuntimeError('Immutable gate preparation exists')
    audit=BASE/'runs/M341-stable-hardware-reuse-audit-02/RESULT.json'
    value=json.loads(audit.read_text(encoding='utf-8'))
    if value['status']!='PASS_UNCHANGED_STABLE_HARDWARE_EVIDENCE_REVALIDATED' or value['errors']:
        raise RuntimeError('No hardware closure, do not package')
    for name in ('CURRENT_STATE.md','docsMILESTONES.md','DEPLOYMENT_OPERATION_MISTAKES_REVIEW.md','deployment/mage_vl4b/BOARD_GATE_RESULT.json'):
        (ROOT/name).read_text(encoding='utf-8-sig')
    run.mkdir(parents=True)
    for name in ('CURRENT_STATE.md','docsMILESTONES.md','deployment/mage_vl4b/BOARD_GATE_RESULT.json'):
        shutil.copyfile(ROOT/name,run/(Path(name).name+'.before'))
    package.mkdir(parents=True)
    text=(HERE/'op00_stable_probe.py').read_text(encoding='utf-8').replace('OP00','M341')
    text=once(text,"ROOT = Path('/home/ubuntu/tellme_m120_m89x2_20260901')\nSTABLE = ROOT / 'm175_m120_fixed_text_candidate'",
              "ROOT = Path('/home/ubuntu/tellme_release_install_20260926')\nSTABLE = ROOT / 'deployment/mage_vl4b/m175_m120_fixed_text_candidate'")
    text=once(text,'    verify_self(here, args.manifest_sha256)\n','')
    text=once(text,"    try:\n        if os.geteuid() != 0:",
        "    try:\n        verify_self(here, args.manifest_sha256)\n"
        "        closure = json.loads((here / 'HARDWARE_CLOSURE.json').read_text(encoding='utf-8'))\n"
        "        if closure['status'] != 'PASS_UNCHANGED_STABLE_HARDWARE_EVIDENCE_REVALIDATED' or closure['errors']:\n"
        "            raise RuntimeError('Hardware evidence closure rejected')\n"
        "        result['hardware_closure_sha256'] = sha256(here / 'HARDWARE_CLOSURE.json')\n"
        "        result['performance_pass'] = False\n"
        "        result['prefetch_candidate_executed'] = False\n"
        "        result['classification'] = 'Stable Build-ID-only and rollback zero transaction; no candidate descriptor/chain/layer/model/performance acceptance'\n"
        "        if os.geteuid() != 0:")
    text=once(text,"        print('M341_PROBE_JSON_BEGIN', flush=True)",
        "        import base64\n        raw = args.result.read_bytes()\n"
        "        print('M341_RESULT_SHA256=' + sha256(args.result), flush=True)\n"
        "        print('M341_RESULT_BASE64=' + base64.b64encode(raw).decode(), flush=True)\n"
        "        print('M341_PROBE_JSON_BEGIN', flush=True)")
    # All buffers must become owned immediately, including partial allocations.
    text=once(text,"        for _ in range(4):\n            buffers.append(allocate((9 * 16,), dtype=np.uint8))\n        buffers.append(allocate((len(packet),), dtype=np.uint8))\n        buffers.append(allocate((output_bytes,), dtype=np.uint8))\n        weights, input_buffer, output_buffer = buffers[:4], buffers[4], buffers[5]",
              "        for size in [9 * 16] * 4 + [len(packet), output_bytes]:\n            buffers.append(allocate((size,), dtype=np.uint8))\n        weights, input_buffer, output_buffer = buffers[:4], buffers[4], buffers[5]")
    (package/'m341_build_id_gate.py').write_text(text,encoding='utf-8',newline='\n')
    mapping=dict(measurement=HERE/'measurement.py',board_safety=HERE/'board_safety.py',
                 m120_board_common=ROOT/'deployment/mage_vl4b/m120_text4b_board_candidate/runtime/m120_board_common.py',
                 m120_board_env_preflight=ROOT/'deployment/mage_vl4b/m175_m120_fixed_text_candidate/runtime/m120_board_env_preflight.py')
    for name,source in mapping.items():shutil.copyfile(source,package/(name+'.py'))
    shutil.copyfile(audit,package/'HARDWARE_CLOSURE.json')
    shell='''#!/usr/bin/env bash
set -euo pipefail
package_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$package_dir"
manifest_sha=${1:?exact manifest SHA required}
printf '%s  PACKAGE_MANIFEST.json\\n' "$manifest_sha" | sha256sum -c -
sha256sum -c SHA256SUMS
sudo -n true
result=/home/ubuntu/m341_build_id_evidence_01/BOARD_RESULT.json
[[ ! -e "$result" ]] || { echo M341_IMMUTABLE_RESULT_EXISTS >&2; exit 2; }
set +e
sudo -n env XILINX_XRT=/usr TMPDIR=/dev/shm PATH=/usr/local/share/pynq-venv/bin:/usr/local/bin:/usr/bin:/bin PYTHONDONTWRITEBYTECODE=1 \\
  /usr/local/share/pynq-venv/bin/python3 -B "$package_dir/m341_build_id_gate.py" --manifest-sha256 "$manifest_sha" --result "$result"
gate_rc=$?
set -e
printf 'M341_BUILD_ID_DONE gate_rc=%s\\n' "$gate_rc"
exit "$gate_rc"
'''
    (package/'run_m341_build_id.sh').write_text(shell,encoding='utf-8',newline='\n')
    rows=[]
    for path in sorted(package.iterdir()):
        if path.suffix=='.py':ast.parse(path.read_text(encoding='utf-8'))
        rows.append(dict(path=path.name,bytes=path.stat().st_size,sha256=sha(path)))
    (package/'SHA256SUMS').write_text(''.join(r['sha256']+'  '+r['path']+'\n' for r in rows),encoding='utf-8',newline='\n')
    rows.append(dict(path='SHA256SUMS',bytes=(package/'SHA256SUMS').stat().st_size,sha256=sha(package/'SHA256SUMS')))
    manifest=dict(schema='tellme-m341-stable-build-id-only-v1',files=rows,file_count=len(rows),total_bytes=sum(r['bytes'] for r in rows),
                  hardware_evidence_sha256=sha(audit),new_hardware=False,prefetch_candidate_gate=False,performance_pass=False)
    (package/'PACKAGE_MANIFEST.json').write_text(json.dumps(manifest,indent=2)+'\n',encoding='utf-8',newline='\n')
    result=dict(status='PREPARED_BLOCKED_AT_COM3_SUDO_EXPIRED',build_id='0x4D395832',package_manifest_sha256=sha(package/'PACKAGE_MANIFEST.json'),
                package=package.relative_to(ROOT).as_posix(),hardware_audit_sha256=sha(audit),hardware_gate_run=False,overlay_loaded=False,
                control_log='tmp/m341/sudo_preflight_uart.log',control_exit=1,performance_pass=False,
                rejected_attempts=['Audit01 rejected appended historical hls.log; exact original100275-byte prefix SHA restored separately, audit02 all47 matches',
                                   'COM3 sudo expired, no overlay/model/FPGA started; awaiting operator sudo-v renewal, no repeated attempts'],
                next_step='After operator renewal, upload/hash/bash-n and same-terminal fixed environment preflight then Build-ID-only; collect/synchronize before descriptor gate')
    atomic(run/'RESULT.json',(json.dumps(result,indent=2)+'\n').encode())
    board_path=ROOT/'deployment/mage_vl4b/BOARD_GATE_RESULT.json';board=json.loads(board_path.read_text(encoding='utf-8-sig'))
    board['latest_m341_hardware_reuse_audit']=dict(status=value['status'],result=audit.relative_to(ROOT).as_posix(),sha256=sha(audit),hardware_gate_run=False)
    board['latest_m341_build_id_preparation']=dict(status=result['status'],result=(run/'RESULT.json').relative_to(ROOT).as_posix(),sha256=sha(run/'RESULT.json'),hardware_gate_run=False,performance_pass=False)
    atomic(board_path,(json.dumps(board,ensure_ascii=False,indent=2)+'\n').encode())
    note=('## M341 稳定电路证据闭合，最小门禁包已备，COM3 sudo过期（2026-10-01）\n\n'
          '稳定数值CSim/递归13依赖missing=0/RTL最大10 descriptor、8192 FIFO占用、AXI回压、word count/最终TLAST/ap_done/return及超时负门禁、整壳及原bitstream共47项哈希复核完成。'
          '首轮仅M132 hls.log整文件哈希不符：后续export_design追加1458B；单独恢复的原100275B前缀SHA `fba87da73b1bbff1ba326cc5ab7c27c0c0ed8f2a6bdefb21edf286011e7136b5` 与历史完全相同，未截断原日志、未重跑仿真，02审计PASS。'
          '证据 `'+audit.relative_to(ROOT).as_posix()+'` SHA `'+sha(audit)+'`。'
          '稳定Build-ID-only/rollback零事务隔离包已冻结，manifest `'+sha(package/'PACKAGE_MANIFEST.json')+'`，无预取候选启动或性能结论。'
          'COM3 `sudo -n true` 返回1/password required，停在授权前置，没有加载overlay；用户已收到sudo-v续期步骤，继续离线包准备，禁止反复尝试同一阻塞。'
          '准备/控制结果 `'+(run/'RESULT.json').relative_to(ROOT).as_posix()+'` SHA `'+sha(run/'RESULT.json')+'`。'
          '稳定Build `0x4D395832`、回滚/boot/DTB/CMA配置保持。下一步收到续期后同COM3固定预检执行Build-ID-only，结果原子回收并同步后才进入单descriptor与预取双缓冲单chain门禁。\n\n')
    for name in ('CURRENT_STATE.md','docsMILESTONES.md'):
        path=ROOT/name;heading,rest=path.read_text(encoding='utf-8-sig').split('\n',1)
        atomic(path,(heading+'\n\n'+note+rest.lstrip('\n')).encode())
    print(json.dumps(dict(status=result['status'],manifest_sha=result['package_manifest_sha256'],files=len(rows),bytes=manifest['total_bytes'])))


if __name__=='__main__':main()
