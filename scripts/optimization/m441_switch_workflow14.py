"""Prepare one separately versioned zero-request diagnostic; saved-byte collection."""
import ast
import base64
import hashlib
import json
from pathlib import Path
import re
import shutil
import sys
import m351_workflow as w
from m441_host_io08 import atomic
PKG=w.BASE/'candidates/M441-first-switch-CMA-14'
RUN=w.BASE/'runs/M441-first-switch-CMA-14'

def prepare():
    from test_m441_cma_trace13 import run
    tests=run()
    b=json.loads((w.ROOT/'deployment/mage_vl4b/BOARD_GATE_RESULT.json').read_bytes())
    for key in ('latest_m441_complete_request_board','latest_m441_complete_request_closure','latest_m441_cma_source_readonly','latest_m441_performance_execution'):
        row=b[key];assert w.sha(w.ROOT/row['result'])==row['sha256']
        assert all(row['sha256'] in (w.ROOT/n).read_text(encoding='utf-8') for n in ('CURRENT_STATE.md','docsMILESTONES.md'))
    src=json.loads((w.ROOT/b['latest_m441_cma_source_readonly']['result']).read_bytes())
    identities=[dict(path=r['path'],sha256=r['sha256']) for r in src['sources']]
    assert len(identities)==5 and not any('unavailable' in r for r in src['sources'])
    PKG.mkdir(exist_ok=False)
    names=['m441_cma_trace13.py','m441_switch_entry13.py','m441_switch_export13.py']
    for n in names:
        raw=(w.HERE/n).read_bytes().replace(b'first_switch_cma_evidence_13',b'first_switch_cma_evidence_14').replace(b'first_switch_cma13',b'first_switch_cma14');ast.parse(raw,feature_version=(3,10));atomic(PKG/n,raw,immutable=True)
    atomic(PKG/'SOURCE_IDENTITIES.json',w.encoded(identities),immutable=True)
    protocol=dict(schema='m441-first-switch-CMA14',scope='One diagnostic at failed switch/resource level; zero complete/model requests',
                  original_performance09_raw_sha256=b['latest_m441_complete_request_board']['sha256'],original_guard_unchanged=True,
                  initial_minimal_B=1,first_switch_A_minimal=1,extra_DMA_slots=0,trace_owned_instance='m441_first_switch_cma14',trace_limit_bytes=1<<20,
                  no_trace_loss_allowed=True,unknown_allocations_rejected=True,no_baseline_reset=True,original_seven_owner_cleanup_only_if_safe=True,
                  maximum_gate_s=600,no_timeoutkill=True,model_requests=0,additional_old09_samples_allowed=False,
                  expected_guard_failure='Global CMA API counter changed; ownership unknown, stop diagnostic',direct_evidence_required='one exact bitstream-page allocation and matching release/PFN with actual FPGA driver stack',
                  numerical_pass=False,performance_pass=False,production_promotion=False)
    atomic(PKG/'PROTOCOL.json',w.encoded(protocol),immutable=True)
    script='\n'.join(['#!/usr/bin/env bash','set -euo pipefail','[[ $EUID == 0 && $# == 2 ]] || exit 65','cd "$(dirname "${BASH_SOURCE[0]}")"',
                     'if [[ $2 == Collect ]]; then /usr/local/share/pynq-venv/bin/python -B ./m441_switch_export13.py; exit 0; fi',
                     '[[ $2 == Run ]] || exit 66','printf "%s  PACKAGE_MANIFEST.json\\n" "$1" | sha256sum -c -','sha256sum -c SHA256SUMS',
                     '[[ ! -e /home/ubuntu/m441_first_switch_cma_evidence_14 ]] || exit 67',
                     'export XILINX_XRT=/usr TMPDIR=/dev/shm PATH=/usr/local/share/pynq-venv/bin:$PATH','set +e',
                     '/usr/local/share/pynq-venv/bin/python -I -B ./m441_switch_entry13.py --enable-first-switch-only','original_gate_rc=$?',
                     '/usr/local/share/pynq-venv/bin/python -B ./m441_switch_export13.py','export_rc=$?','set -e',
                     'printf "M441D_DONE original_gate_rc=%s export_rc=%s\\n" "$original_gate_rc" "$export_rc"',
                     'if [[ $original_gate_rc != 0 ]]; then exit "$original_gate_rc"; fi','exit "$export_rc"',''])
    atomic(PKG/'run.sh',script.encode(),immutable=True)
    rows=[dict(path=p.name,bytes=p.stat().st_size,sha256=w.sha(p)) for p in sorted(PKG.iterdir())]
    atomic(PKG/'SHA256SUMS',''.join(r['sha256']+'  '+r['path']+'\n' for r in rows).encode(),immutable=True)
    rows.append(dict(path='SHA256SUMS',bytes=(PKG/'SHA256SUMS').stat().st_size,sha256=w.sha(PKG/'SHA256SUMS')))
    atomic(PKG/'PACKAGE_MANIFEST.json',w.encoded(dict(schema='m441-first-switch-cma14',files=rows,file_count=len(rows),total_bytes=sum(r['bytes'] for r in rows))),immutable=True)
    manifest=w.sha(PKG/'PACKAGE_MANIFEST.json')
    control=f'''param([ValidateSet('Upload','Run','Collect')][string]$Mode)
$ErrorActionPreference='Stop'
Set-StrictMode -Version Latest
$taskRoot=(Resolve-Path (Join-Path $PSScriptRoot '../..')).Path
$taskUART=Join-Path $taskRoot 'scripts/m75c_uart_command.ps1'
$taskRemote='/home/ubuntu/m441_first_switch_cma_candidate_14'
$taskLog="tmp/m441_cma14/${{Mode}}.log"
if(Test-Path (Join-Path $taskRoot $taskLog)){{throw 'Existing attempt: fresh saved-byte collection only'}}
& $taskUART -Command 'sudo -n true' -LogPath "tmp/m441_cma14/${{Mode}}_sudo.log" -TimeoutSeconds 15 -MarkerPrefix '__M441D_AUTH_RC_'
if($Mode -eq 'Upload'){{
 foreach($taskName in @('PACKAGE_MANIFEST.json',{','.join(repr(r['path']) for r in rows)})){{
  & (Join-Path $taskRoot 'scripts/m212_uart_put_file_chunked.ps1') -LocalPath ('{PKG.relative_to(w.ROOT).as_posix()}/'+$taskName) -RemotePath ($taskRemote+'/'+$taskName) -LogPrefix ('tmp/m441_cma14/upload_'+$taskName.Replace('.','_')) -ChunkBytes 900 -TimeoutSeconds 25
 }}
 & $taskUART -Command "sudo -n bash -n $taskRemote/run.sh" -LogPath 'tmp/m441_cma14/syntax.log' -TimeoutSeconds 15 -MarkerPrefix '__M441D_SYNTAX_RC_'
 exit 0
}}
$taskError=$null
try{{& $taskUART -Command "sudo -n bash $taskRemote/run.sh {manifest} $Mode" -LogPath $taskLog -TimeoutSeconds 900 -MarkerPrefix '__M441D_GATE_RC_'}}catch{{$taskError=$_}}
& '{sys.executable}' -B -X utf8 (Join-Path $PSScriptRoot 'm441_switch_workflow14.py') collect (Join-Path $taskRoot $taskLog)
if($LASTEXITCODE -ne 0){{throw 'Collection incomplete: never repeat hardware'}}
if($taskError){{throw $taskError}}
'''
    atomic(w.HERE/'m441_switch_control14.ps1',control.encode(),immutable=True)
    value=dict(status='PREPARED_ONE_M441_FIRST_SWITCH_CMA14',manifest_sha256=manifest,protocol_sha256=w.sha(PKG/'PROTOCOL.json'),tests=tests,
               original_guard_unchanged=True,original_owner_gate_new_AST_literal_only=True,trial_dispatch_zero_requests=True,board_executed=False,
               rejected_component_gap='Old fake switch test replaced capture with no-op; did not exercise actual CMA policy after Overlay programming')
    atomic(RUN/'PREPARATION.json',w.encoded(value),immutable=True);sha=w.sha(RUN/'PREPARATION.json')
    w.sync('latest_m441_CMA14_preparation',dict(status=value['status'],result=(RUN/'PREPARATION.json').relative_to(w.ROOT).as_posix(),sha256=sha,manifest_sha256=manifest),
           f'## M441 单次切核CMA诊断13准备（2026-10-09）\n\nSHA {sha}；旧09FAIL及0请求保持，另立协议，原七owner门禁仅证据目录AST字面量更改、调度限定一次B→A最小，0请求。独立trace instance仅临时CMA事件/调用栈，有界原证据及无丢事件要求，原累计计数检查不放宽。{len(tests)}项实际policy/明确trace fixture检查通过；旧fake捕获无操作遗漏已识别，不当板端来源证明。尚未执行，失败只Collect。')
    print(value['status'],sha,manifest)

def collect(path):
    text=Path(path).read_text(encoding='utf-8-sig')
    hashes=re.findall(r'(?m)^M441D_RESULT_SHA256=([0-9a-f]{64})\s*$',text)
    codes=re.findall(r'(?m)^M441D_ORIGINAL_GATE_RC=([01])\s*$',text)
    chunks=re.findall(r'(?m)^M441D_RESULT_CHUNK=(\d+)/(\d+):([A-Za-z0-9+/=]+)\s*$',text)
    assert len(hashes)==len(codes)==1 and chunks and len(chunks)==int(chunks[0][1]),'Incomplete original evidence; collect only'
    parts=[]
    for i,(n,total,data) in enumerate(chunks):
        raw=base64.b64decode(data,validate=True)
        assert int(n)==i and int(total)==len(chunks) and 0<len(raw)<=900
        parts.append(raw)
    raw=b''.join(parts);sha=hashlib.sha256(raw).hexdigest();assert sha==hashes[0]
    # Reuse component evidence format13; fresh14 artifact paths and manifest are separate.
    r=json.loads(raw);assert r['schema']=='m441-first-switch-cma13' and r['original_gate_rc']==int(codes[0]) and not r['gate'].get('samples')
    assert re.findall(r'M441D_DONE original_gate_rc=(\d+) export_rc=(\d+)',text) in ([],[(codes[0],'0')])
    atomic(RUN/'DIAG_RESULT.json',raw,immutable=True)
    atomic(RUN/'COLLECTION.json',w.encoded(dict(source_log=str(path),source_log_sha256=w.sha(Path(path)),chunks=len(chunks),sha256=sha,hardware_reexecuted=False)),immutable=True)
    w.sync('latest_m441_CMA14_board',dict(status=r['status'],result=(RUN/'DIAG_RESULT.json').relative_to(w.ROOT).as_posix(),sha256=sha,original_gate_rc=r['original_gate_rc'],performance_pass=False),
           f'## M441 单次切核CMA诊断13回收（2026-10-09）\n\nSHA {sha}；{len(chunks)}原字节块，旧计数门禁原rc{r["original_gate_rc"]}保留，诊断{r["status"]}。0请求，原七owner/稳定恢复见原raw；只读解释调用栈及申请释放，不是性能或完整请求PASS。原09FAIL不改，未知申请检查未放宽。')
    print(r['status'],sha,r['diagnostic'].get('problems'))

if __name__=='__main__':
    if sys.argv[1]=='prepare':prepare()
    elif sys.argv[1]=='collect':collect(sys.argv[2])
