"""Freeze, transfer and collect the CPU component, separate from FPGA gates."""
import ast
import base64
import hashlib
import json
from pathlib import Path
import re
import sys
from m441_host_io08 import atomic
from m351_workflow import ROOT, BASE, HERE, encoded, sha, sync

PKG = BASE/'candidates/M442-A53-parser-component-01'
BOOT = BASE/'candidates/M442-A53-transfer-bootstrap-01'
RUN = BASE/'runs/M442-A53-parser-component-preparation-01'
OLD = BASE/'candidates/M442-direct-output-parser-02'


def manifest(directory, schema):
    rows = [dict(path=p.name, bytes=p.stat().st_size, sha256=sha(p)) for p in sorted(directory.iterdir())]
    atomic(directory/'SHA256SUMS', ''.join(r['sha256']+'  '+r['path']+'\n' for r in rows).encode(), immutable=True)
    rows.append(dict(path='SHA256SUMS', bytes=(directory/'SHA256SUMS').stat().st_size, sha256=sha(directory/'SHA256SUMS')))
    value = dict(schema=schema, files=rows, file_count=len(rows), total_bytes=sum(r['bytes'] for r in rows))
    atomic(directory/'PACKAGE_MANIFEST.json', encoded(value), immutable=True)
    return value


def prepare():
    if PKG.exists() or BOOT.exists() or RUN.exists():
        raise RuntimeError('Existing preparation: inspect only')
    prior = BASE/'runs/M442-direct-output-parser-preparation-02/RESULT.json'
    assert sha(prior) == '256d1fa5c1671e5e698261e09881732483cf95a5658a6b9a4e8eefedb5cbe0a4'
    old_manifest = json.loads((OLD/'PACKAGE_MANIFEST.json').read_bytes())
    assert sha(OLD/'PACKAGE_MANIFEST.json') == '4b9f62c1d492c303f06154661ad3ae2aecf2d7b974bb9814908d70f0fa6888a7'
    PKG.mkdir(parents=True)
    for row in old_manifest['files']:
        assert sha(OLD/row['path']) == row['sha256']
        if row['path'] != 'SHA256SUMS':
            atomic(PKG/row['path'], (OLD/row['path']).read_bytes(), immutable=True)
    gate = (HERE/'m442_component_gate01.py').read_bytes()
    ast.parse(gate, feature_version=(3,10))
    atomic(PKG/'m442_component_gate01.py', gate, immutable=True)
    shell = '''#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")"
manifest_sha=${1:?exact manifest SHA required}
mode=${2:?Run or Collect required}
printf '%s  PACKAGE_MANIFEST.json\n' "$manifest_sha" | sha256sum -c -
sha256sum -c SHA256SUMS
sudo -n true
[[ "$mode" == Run || "$mode" == Collect ]] || exit 2
set +e
if [[ "$mode" == Run ]]; then
 /usr/local/share/pynq-venv/bin/python -B ./m442_component_gate01.py Run "$manifest_sha" --enable-cpu-component
else
 /usr/local/share/pynq-venv/bin/python -B ./m442_component_gate01.py Collect
fi
gate_rc=$?
set -e
printf 'M442C_DONE gate_rc=%s export_rc=0\n' "$gate_rc"
exit "$gate_rc"
'''
    atomic(PKG/'run_m442_component.sh', shell.encode(), immutable=True)
    spec = manifest(PKG, 'm442-a53-cpu-component-v1')
    BOOT.mkdir(parents=True)
    transfer = (HERE/'m441_transfer.py').read_text(encoding='utf-8')
    transfer = transfer.replace("DESTINATION=Path('/home/ubuntu/m441_candidate_01')", "DESTINATION=Path('/home/ubuntu/m442_a53_component_candidate_01')")
    transfer = transfer.replace("EVIDENCE=Path('/home/ubuntu/m441_transfer_evidence_01')", "EVIDENCE=Path('/home/ubuntu/m442_a53_transfer_evidence_01')")
    ast.parse(transfer, feature_version=(3,10))
    atomic(BOOT/'m442_transfer01.py', transfer.encode(), immutable=True)
    rows = [dict(path='PACKAGE_MANIFEST.json', bytes=(PKG/'PACKAGE_MANIFEST.json').stat().st_size, sha256=sha(PKG/'PACKAGE_MANIFEST.json'))]+spec['files']
    transport = dict(schema='m441-specific-peer-transfer-v1', package_manifest_sha256=sha(PKG/'PACKAGE_MANIFEST.json'), files=rows,
                     file_count=len(rows), total_bytes=sum(r['bytes'] for r in rows))
    atomic(BOOT/'TRANSPORT_MANIFEST.json', encoded(transport), immutable=True)
    runner = '''#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")"
mode=${1:?receive or collect required}
digest=${2:?exact bootstrap manifest SHA required}
printf '%s  PACKAGE_MANIFEST.json\n' "$digest" | sha256sum -c -
sha256sum -c SHA256SUMS
sudo -n true
exec /usr/local/share/pynq-venv/bin/python -B ./m442_transfer01.py "$mode" . "$digest"
'''
    atomic(BOOT/'run_m442_transfer.sh', runner.encode(), immutable=True)
    manifest(BOOT, 'm442-a53-specific-peer-bootstrap')
    import m441_transfer as original
    original.verify_directory(PKG, sha(PKG/'PACKAGE_MANIFEST.json'))
    original.verify_directory(BOOT, sha(BOOT/'PACKAGE_MANIFEST.json'))
    result = dict(status='PREPARED_M442_A53_CPU_COMPONENT01', prior_sha256=sha(prior), manifest_sha256=sha(PKG/'PACKAGE_MANIFEST.json'),
                  bootstrap_manifest_sha256=sha(BOOT/'PACKAGE_MANIFEST.json'), candidate_sha256=sha(PKG/'m442_output_parser06.py'),
                  file_count=spec['file_count'], bytes=spec['total_bytes'], original_transfer_sha256=sha(HERE/'m441_transfer.py'),
                  transfer_only_delta='destination and evidence paths only', CPU_board_run=False, FPGA_gate_run=False,
                  fixture_scope='Saved actual RTL packets; actual scheduler with explicit fake hardware; no PYNQ/model/Overlay',
                  intended_component_budget_s=240, full_request_performance_proven=False)
    assert transfer.replace('/home/ubuntu/m442_a53_component_candidate_01','/home/ubuntu/m441_candidate_01').replace('/home/ubuntu/m442_a53_transfer_evidence_01','/home/ubuntu/m441_transfer_evidence_01') == (HERE/'m441_transfer.py').read_text(encoding='utf-8')
    atomic(RUN/'RESULT.json', encoded(result), immutable=True)
    auth = ROOT/'tmp/m442_board01/authorization_sudo02.log'
    assert '__M442_SUDO_RC_0__' in auth.read_text(encoding='utf-8-sig')
    sync('latest_m442_a53_component_preparation', dict(status=result['status'], result=(RUN/'RESULT.json').relative_to(ROOT).as_posix(), sha256=sha(RUN/'RESULT.json'), manifest_sha256=result['manifest_sha256'], board=False),
         f'## M442实板A53组件包冻结（2026-10-10）\n\nSHA {sha(RUN / "RESULT.json")}，manifest {result["manifest_sha256"]}；用户恢复上板、登录续期，同COM3 sudo rc0日志SHA {sha(auth)}。新隔离包复用原parser06/99真实RTL包/完整位型及重试所有权检查；仅CPU组件与明确fake硬件，不当新PL数值或完整请求提速。指定192.168.0.2/0.10:8777有界SHA传输，旧地址/路由恢复，不用SSH。之后严格组件原字节通过才准备本候选PL数值门禁。')
    print(json.dumps(result))


def collect(log):
    text = Path(log).read_text(encoding='utf-8-sig')
    hashes = re.findall(r'(?m)^M442C_RESULT_SHA256=([0-9a-f]{64})\s*$', text)
    codes = re.findall(r'(?m)^M442C_SAVED_GATE_RC=([01])\s*$', text)
    rows = re.findall(r'(?m)^M442C_RESULT_CHUNK=(\d+)/(\d+):([A-Za-z0-9+/=]+)\s*$', text)
    if len(hashes)!=1 or len(codes)!=1 or not rows or int(rows[0][1]) != len(rows):
        raise RuntimeError('Missing/duplicate original result')
    parts=[]
    for i,(n,total,b64) in enumerate(rows):
        raw=base64.b64decode(b64,validate=True)
        if int(n)!=i or int(total)!=len(rows) or not 0<len(raw)<=900:
            raise RuntimeError('Result chunk order/bound differs')
        parts.append(raw)
    raw=b''.join(parts)
    if len(raw)>1<<20 or hashlib.sha256(raw).hexdigest()!=hashes[0]:
        raise RuntimeError('Original result SHA differs')
    result=json.loads(raw)
    if result['gate_return_code']!=int(codes[0]) or result['manifest_sha256']!=sha(PKG/'PACKAGE_MANIFEST.json'):
        raise RuntimeError('Original rc/manifest differs')
    if any(result[k] != 0 for k in ('Overlay_calls','DMA_allocations','FPGA_transactions','model_requests')):
        raise RuntimeError('Unexpected PL/model component scope')
    if result['status']=='PASS_M442_A53_COMPONENT01':
        integration=result['integration']
        if result['gate_return_code'] or result['errors'] or not result['numerical_pass'] or result['elapsed_s']>240 or result['platform']['machine'] not in ('aarch64','arm64'):
            raise RuntimeError('A53 CPU PASS contract differs')
        if integration['actual_packet_comparisons']!=99 or integration['all_fp16_bits_shifts']!=11 or integration['partial_strided_checks']!=81 or len(integration['pipeline_checks'])!=6:
            raise RuntimeError('CPU complete coverage differs')
        if integration['candidate_sha256']!=sha(PKG/'m442_output_parser06.py') or integration['driver_and_math_changed'] or not integration['accepted_class_unmodified']:
            raise RuntimeError('Candidate/source/scope differs')
    elif result['status']!='FAIL_M442_A53_COMPONENT01' or not result['errors'] or result['gate_return_code']!=1:
        raise RuntimeError('Original failure contract differs')
    out=BASE/'runs/M442-A53-parser-component-board-01/BOARD_RESULT.json'
    atomic(out,raw,immutable=True)
    atomic(out.with_name('COLLECTION.json'),encoded(dict(log=str(log),log_sha256=sha(Path(log)),raw_sha256=hashes[0],chunks=len(rows),hardware_rerun=False)),immutable=True)
    sync('latest_m442_a53_component_board',dict(status=result['status'],result=out.relative_to(ROOT).as_posix(),sha256=hashes[0],board_cpu=True,board_FPGA=False,performance_pass=False),
         f'## M442实板A53组件裁决（2026-10-10）\n\nSHA {hashes[0]}；{result["status"]}，原rc{result["gate_return_code"]}，全部CPU数值/重试/owner原字节保存。只有A53解析组件，不是PL完整请求收益；仍需本候选数值门禁与固定4＋8完整请求对照，不从微测外推。')
    print(result['status'],hashes[0])
    if result.get('integration'):
        print(json.dumps([{k:v for k,v in row.items() if not isinstance(v,list)} for row in result['integration']['timings']],indent=2))
    return result['gate_return_code']


def transfer_collect(log):
    text=Path(log).read_text(encoding='utf-8-sig')
    hashes=re.findall(r'(?m)^M441_TRANSFER_SHA256=([0-9a-f]{64})\s*$',text)
    rows=re.findall(r'(?m)^M441_TRANSFER_CHUNK=(\d+)/(\d+):([A-Za-z0-9+/=]+)\s*$',text)
    if len(hashes)!=1 or not rows or int(rows[0][1])!=len(rows):
        raise RuntimeError('Original transfer evidence incomplete')
    parts=[]
    for i,(n,total,b64) in enumerate(rows):
        part=base64.b64decode(b64,validate=True)
        if int(n)!=i or int(total)!=len(rows) or not 0<len(part)<=900:
            raise RuntimeError('Transfer chunk order/bound differs')
        parts.append(part)
    raw=b''.join(parts)
    if hashlib.sha256(raw).hexdigest()!=hashes[0] or len(raw)>1<<20:
        raise RuntimeError('Original transfer SHA differs')
    result=json.loads(raw)
    if result['bootstrap_manifest_sha256']!=sha(BOOT/'PACKAGE_MANIFEST.json') or result['package_manifest_sha256']!=sha(PKG/'PACKAGE_MANIFEST.json'):
        raise RuntimeError('Transfer manifests differ')
    if result['overlay_loaded'] or result['fpga_transactions'] or result['board_gate_executed']:
        raise RuntimeError('Transfer executed model/PL')
    if result['status']=='PASS_M441_ARTIFACT_TRANSFER_ONLY':
        expected=json.loads((BOOT/'TRANSPORT_MANIFEST.json').read_bytes())['files']
        if result['files']!=expected or result['errors'] or not result['temporary_address_restored']:
            raise RuntimeError('Exact transfer/address restoration differs')
    elif result['status']!='FAIL_M441_ARTIFACT_TRANSFER' or not result['errors']:
        raise RuntimeError('Original transfer failure differs')
    out=BASE/'runs/M442-A53-artifact-transfer-01/BOARD_RESULT.json'
    atomic(out,raw,immutable=True)
    sync('latest_m442_a53_artifact_transfer',dict(status=result['status'],result=out.relative_to(ROOT).as_posix(),sha256=hashes[0],manifest_sha256=result['package_manifest_sha256'],board_gate=False),
         f'## M442 A53包指定对端传输回收（2026-10-10）\n\nSHA {hashes[0]}；{result["status"]}。manifest-first/逐文件原SHA，0Overlay/FPGA；临时地址恢复={result["temporary_address_restored"]}，原字节保存，不是数值/性能PASS。')
    print(result['status'],hashes[0])
    return 0 if result['status']=='PASS_M441_ARTIFACT_TRANSFER_ONLY' else 1


def send():
    import m441_transfer as transfer
    return transfer.send(PKG,sha(PKG/'PACKAGE_MANIFEST.json'),BOOT/'TRANSPORT_MANIFEST.json',
                         BASE/'runs/M442-A53-artifact-transfer-01/SENDER_RESULT.json')


if __name__=='__main__':
    if sys.argv[1:] == ['prepare']:
        prepare()
    elif len(sys.argv)==3 and sys.argv[1]=='collect':
        raise SystemExit(collect(sys.argv[2]))
    elif len(sys.argv)==3 and sys.argv[1]=='transfer-collect':
        raise SystemExit(transfer_collect(sys.argv[2]))
    elif sys.argv[1:]==['send']:
        raise SystemExit(send())
    else:
        raise RuntimeError('Explicit prepare or saved collect required')
