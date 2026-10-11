"""Prepare isolated CPU worker fixture, strict saved-byte recovery only."""
import ast
import base64
import copy
import hashlib
import json
from pathlib import Path
import re
import shutil
import subprocess
import sys
from m351_workflow import ROOT,HERE,BASE,sha,atomic,encoded,sync
from m376_gate_up_workers import PINNED
PRIOR='8ff1d4f94471584ec95ff60b8fa3c4c4a8840709f2c010ec356fd1a07fa05b56'
PKG=BASE/'candidates/M376-gate-up-worker-component-01'
PREP=BASE/'runs/M376-gate-up-worker-preparation-01'
RUN=BASE/'runs/M376-gate-up-worker-board-01'
FALSE_KEYS=('overlay_loaded','real_assets_read','model_forward_calls','fpga_transactions','extra_pynq_allocations',
            'ps_prefetch_enabled','memory_capacity_proven','numerical_pass','performance_pass','formal_promotion_allowed')
TEST_IDS=['test_actual_largest_gate_up_geometry','test_default_disabled_and_invalid_width',
 'test_dma_reuse_only_after_future_and_retry_confirmation','test_exact_tail_sizes_and_retry_counts',
 'test_independent_original_parser_reference','test_non_gate_up_stays_original_single_worker',
 'test_parser_exception_joins_workers_restores_bindings','test_phase_counts_with_forced_interleaving',
 'test_repeated_requests_keep_only_two_outputs','test_retry_one_output_while_other_parser_is_active',
 'test_source_drift_rejected_before_patch','test_two_real_tasks_overlap_and_write_disjoint_rows']

def decode(log):
    hs=re.findall(r'(?m)^M376_RESULT_SHA256=([0-9a-f]{64})\s*$',log)
    rc=re.findall(r'(?m)^M376_SAVED_GATE_RC=([01])\s*$',log)
    chunks=re.findall(r'(?m)^M376_RESULT_CHUNK=(\d+)/(\d+):([A-Za-z0-9+/=]+)\s*$',log)
    if len(hs)!=1 or len(rc)!=1 or not chunks or len(chunks)!=int(chunks[0][1]):raise ValueError('Missing/duplicate result')
    parts=[]
    for i,(index,total,b64) in enumerate(chunks):
        p=base64.b64decode(b64,validate=True)
        if int(index)!=i or int(total)!=len(chunks) or not 0<len(p)<=900:raise ValueError('Chunk order/bound')
        parts.append(p)
    raw=b''.join(parts);digest=hashlib.sha256(raw).hexdigest();r=json.loads(raw)
    if digest!=hs[0] or type(r['gate_return_code']) is not int or r['gate_return_code']!=int(rc[0]):raise ValueError('Raw SHA/rc')
    if r['manifest_sha256']!=sha(PKG/'PACKAGE_MANIFEST.json') or r['prior_raw_sha256']!=PRIOR or r['target_build_id']!='0x4D333537' or r['gate_level']!='CPU-gate-up-worker-capability':raise ValueError('Identity differs')
    if any(r[k] for k in FALSE_KEYS):raise ValueError('Scope promoted')
    done=re.findall(r'M376_DONE gate_rc=(\d+) export_rc=(\d+)',log)
    if done and done!=[(rc[0],'0')]:raise ValueError('Gate/export rc')
    if r['status']=='PASS_GATE_UP_TWO_WORKER_CPU_COMPONENT_ONLY':
        if done!=[('0','0')] or r['gate_return_code'] or r['errors'] or r['tests_run']!=12 or r['test_ids']!=TEST_IDS:raise ValueError('Incomplete PASS')
        if r['elapsed_s']>60 or r['platform']['euid']!=0 or r['platform']['uname'][0]!='Linux' or r['lifecycle']['active_workers']:raise ValueError('Environment/lifecycle')
        if 'Ran 12 tests' not in r['test_output'] or not r['test_output'].rstrip().endswith('OK') or any(n not in r['test_output'] for n in TEST_IDS):raise ValueError('Test transcript')
        if r['pinned_source_sha256']!=PINNED or r['worker_component_sha256']!=sha(PKG/'m376_gate_up_workers.py') or r['fixture_sha256']!=sha(PKG/'GATE_UP_FIXTURE.json'):raise ValueError('Component/source identity')
    elif r['status']!='FAIL_GATE_UP_WORKER_CPU_COMPONENT' or r['gate_return_code']!=1 or not r['errors']:raise ValueError('Invalid failed result')
    return digest,raw,r

def export_fixture(r):
    blob=encoded(r);parts=[blob[i:i+900] for i in range(0,len(blob),900)];rc=r['gate_return_code']
    return 'M376_RESULT_SHA256='+hashlib.sha256(blob).hexdigest()+'\nM376_SAVED_GATE_RC='+str(rc)+'\n'+''.join(f'M376_RESULT_CHUNK={i}/{len(parts)}:'+base64.b64encode(p).decode()+'\n' for i,p in enumerate(parts))+f'M376_DONE gate_rc={rc} export_rc=0\n'

def self_test():
    r=dict(status='PASS_GATE_UP_TWO_WORKER_CPU_COMPONENT_ONLY',gate_level='CPU-gate-up-worker-capability',
        target_build_id='0x4D333537',prior_raw_sha256=PRIOR,manifest_sha256=sha(PKG/'PACKAGE_MANIFEST.json'),
        gate_return_code=0,errors=[],tests_run=12,test_ids=TEST_IDS,
        test_output='\n'.join(TEST_IDS)+'\nRan 12 tests\nOK\n',elapsed_s=1,
        platform=dict(euid=0,uname=['Linux']),lifecycle=dict(active_workers=[]),pinned_source_sha256=PINNED,
        worker_component_sha256=sha(PKG/'m376_gate_up_workers.py'),fixture_sha256=sha(PKG/'GATE_UP_FIXTURE.json'))
    r.update({k:False for k in FALSE_KEYS});good=export_fixture(r);assert decode(good)[2]==r
    bad=[]
    for k,v in [('tests_run',11),('test_ids',TEST_IDS[:-1]),('worker_component_sha256','0'*64),
         ('fixture_sha256','0'*64),('pinned_source_sha256',{}),('lifecycle',dict(active_workers=['parser'])),
         ('elapsed_s',61),('platform',dict(euid=1,uname=['Linux'])),('errors',['error']),('test_output','OK')]+[(k,True) for k in FALSE_KEYS]:
        x=copy.deepcopy(r);x[k]=v;bad.append(export_fixture(x))
    bad.extend([good.replace('CHUNK=0/','OMITTED=0/'),good.replace('CHUNK=1/','CHUNK=0/'),good.replace('export_rc=0','export_rc=1'),good.replace('M376_SAVED_GATE_RC=0','M376_SAVED_GATE_RC=1'),good[:good.rfind('M376_DONE')]])
    for x in bad:
        try:decode(x)
        except (RuntimeError,ValueError):pass
        else:raise AssertionError('Invalid component export accepted')
    fail=dict(r,status='FAIL_GATE_UP_WORKER_CPU_COMPONENT',gate_return_code=1,errors=['fixture failure'],tests_run=0)
    assert decode(export_fixture(fail))[2]==fail
    return len(bad)

def prepare():
    if PKG.exists() or PREP.exists():raise RuntimeError('Preparation exists')
    board=json.loads((ROOT/'deployment/mage_vl4b/BOARD_GATE_RESULT.json').read_text(encoding='utf-8-sig'))
    row=board['latest_m376_gate_up_worker_audit'];assert row['sha256']==PRIOR and sha(ROOT/row['result'])==PRIOR
    assert all(PRIOR in (ROOT/n).read_text(encoding='utf-8-sig') for n in ('CURRENT_STATE.md','docsMILESTONES.md'))
    audit=json.loads((ROOT/row['result']).read_text(encoding='utf-8'));assert sha(HERE/'m376_gate_up_workers.py')==audit['source_sha256']
    PKG.mkdir()
    for name in ('m376_gate_up_workers.py','test_m376_gate_up_workers.py','m376_component_gate.py'):shutil.copyfile(HERE/name,PKG/name)
    source=json.loads((BASE/'candidates/M369-light-video-01/SOURCE_CLOSURE.json').read_text(encoding='utf-8'))
    release=ROOT/'release_staging/kv260-mage-vl-4b-prebuilt-install-20260926-v7'
    for name in ('m238_prefill_runtime','m236_prefill_runtime','m231_prefill_runtime','m230_prefill_runtime'):
        p=release/source['modules'][name];shutil.copyfile(p,PKG/(name+'.py'))
    shutil.copyfile(ROOT/row['result'],PKG/'M376_AUDIT.json')
    shutil.copyfile((ROOT/row['result']).parent/'GATE_UP_FIXTURE.json',PKG/'GATE_UP_FIXTURE.json')
    export=(HERE/'m373_export_result.py').read_text(encoding='utf-8').replace('M373','M376').replace('m373_future_wait_evidence_01','m376_gate_up_component_evidence_01')
    atomic(PKG/'m376_export_result.py',export.encode('utf-8'))
    runner=(BASE/'candidates/M373-future-wait-component-01/run_m373_component.sh').read_text(encoding='utf-8').replace('M373','M376').replace('m373','m376').replace('m376_future_wait_evidence_01','m376_gate_up_component_evidence_01')
    atomic(PKG/'run_m376_component.sh',runner.encode('utf-8'))
    for p in PKG.glob('*.py'):ast.parse(p.read_text(encoding='utf-8'),feature_version=(3,10))
    tested=subprocess.run([sys.executable,'-X','utf8','-B',str(PKG/'test_m376_gate_up_workers.py'),'-v'],capture_output=True,text=True,encoding='utf-8')
    if tested.returncode or 'Ran 12 tests' not in tested.stderr or not tested.stderr.rstrip().endswith('OK'):raise RuntimeError(tested.stdout+tested.stderr)
    rows=[dict(path=p.name,bytes=p.stat().st_size,sha256=sha(p)) for p in sorted(PKG.iterdir())]
    atomic(PKG/'SHA256SUMS',''.join(r['sha256']+'  '+r['path']+'\n' for r in rows).encode('ascii'))
    rows.append(dict(path='SHA256SUMS',bytes=(PKG/'SHA256SUMS').stat().st_size,sha256=sha(PKG/'SHA256SUMS')))
    atomic(PKG/'PACKAGE_MANIFEST.json',encoded(dict(schema='m376-gate-up-two-worker-component-v1',files=rows,file_count=len(rows),total_bytes=sum(r['bytes'] for r in rows))))
    assert {p.name for p in PKG.iterdir()}=={r['path'] for r in rows}|{'PACKAGE_MANIFEST.json'}
    negative=self_test()
    controller=(HERE/'m373_control.ps1').read_text(encoding='utf-8').replace('M373-future-wait','M376-gate-up-worker').replace('m373_future_wait_component_01','m376_gate_up_worker_component_01').replace('m373','m376').replace('M373','M376').replace('latest_m376_future_wait','latest_m376_gate_up_worker').replace('sudo_precheck_02','sudo_precheck_01')
    anchor='$prep=$board.latest_m376_gate_up_worker_preparation'
    assert controller.count(anchor)==1
    controller=controller.replace(anchor,anchor+"\n$receipt=Get-Content -LiteralPath (Join-Path $workspace $prep.result) -Raw -Encoding UTF8 | ConvertFrom-Json\nforeach ($entry in $receipt.host_source_sha256.PSObject.Properties) { if ((Get-FileHash -LiteralPath (Join-Path $PSScriptRoot $entry.Name) -Algorithm SHA256).Hash.ToLowerInvariant() -ne $entry.Value) { throw 'Host workflow changed' } }")
    anchor="if ($Mode -eq 'Upload') {"
    controller=controller.replace(anchor,anchor+"\n    & $uart -Command \"test ! -e $remote\" -LogPath 'tmp/m376/package_absence_uart.log' -TimeoutSeconds 15 -MarkerPrefix '__M376_ABSENT_RC_'\n    if (-not $?) { throw 'Remote package exists; no overwrite' }")
    atomic(HERE/'m376_control.ps1',controller.encode('utf-8'))
    ps=Path(r'C:\Users\30429\.cache\codex-runtimes\codex-primary-runtime\dependencies\native\powershell\pwsh.exe')
    check=subprocess.run([str(ps),'-NoProfile','-File',str(HERE/'m376_control.ps1'),'-Mode','SelfTest'],capture_output=True,text=True,encoding='utf-8')
    if check.returncode or 'M376_CONTROL_SELF_TEST_PASS' not in check.stdout:raise RuntimeError(check.stdout+check.stderr)
    result=dict(status='PASS_OFFLINE_GATE_UP_WORKER_COMPONENT_READY',target_build_id='0x4D333537',prior_raw_sha256=PRIOR,
        manifest_sha256=sha(PKG/'PACKAGE_MANIFEST.json'),tests_run=12,collector_negative_checks=negative,
        package_files=len(rows),package_bytes=sum(r['bytes'] for r in rows),python310_syntax=True,default_disabled=True,
        host_source_sha256={n:sha(HERE/n) for n in ('m376_control.ps1','m376_workflow.py','m376_gate_up_workers.py')},
        evidence_level='L0_CPU_PACKAGE_ONLY',board_run=False,performance_pass=False,
        next_step='COM3 same-terminal sudo; manifest-first900B full hashes then one CPU-only component; no Overlay until this gate is closed')
    atomic(PREP/'TEST_OUTPUT.txt',(tested.stdout+tested.stderr).encode('utf-8'),immutable=True)
    atomic(PREP/'CONTROL_TEST_OUTPUT.txt',(check.stdout+check.stderr).encode('utf-8'),immutable=True)
    atomic(PREP/'RESULT.json',encoded(result),immutable=True);digest=sha(PREP/'RESULT.json')
    sync('latest_m376_gate_up_worker_preparation',dict(status=result['status'],result=(PREP/'RESULT.json').relative_to(ROOT).as_posix(),sha256=digest,manifest_sha256=result['manifest_sha256']),
        f'## M376 gate_up双worker板端CPU组件准备（2026-10-03）\n\nBuild0x4D333537未加载；12项新包真实冻结解析/Future检查、{negative}项回收负例、控制故意失败仍收集/收集失败停止通过。仅显式fake DMA/合成packet，0Overlay/真实资产/模型/FPGA。准备SHA {digest}，manifest {result["manifest_sha256"]}，{len(rows)}载荷{result["package_bytes"]}B。下一步同COM3 sudo及manifest-first900B板端全SHA后一次CPU组件，再独立代表family；数值/完整请求收益尚未验证，原M36940.81%保持。')
    print(json.dumps(result))

def transfer():
    source=(HERE/'m373_workflow.py').read_text(encoding='utf-8');tree=ast.parse(source)
    node=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='transfer')
    text=ast.get_source_segment(source,node).replace('m373','m376').replace('M373-future-wait','M376-gate-up-worker').replace('M373','M376').replace('latest_m376_future_wait','latest_m376_gate_up_worker')
    env=dict(globals());exec(compile(text,'<pinned-transfer-receipts>','exec'),env);env['transfer']()

def finish_preparation():
    """Recover the prior local control-path failure; never replace a payload."""
    if PREP.exists():raise RuntimeError('Completed immutable preparation exists')
    manifest=json.loads((PKG/'PACKAGE_MANIFEST.json').read_text(encoding='utf-8'))
    for row in manifest['files']:
        assert sha(PKG/row['path'])==row['sha256'] and (PKG/row['path']).stat().st_size==row['bytes']
    assert {p.name for p in PKG.iterdir()}=={r['path'] for r in manifest['files']}|{'PACKAGE_MANIFEST.json'}
    for name in ('m376_gate_up_workers.py','test_m376_gate_up_workers.py','m376_component_gate.py'):
        assert sha(HERE/name)==sha(PKG/name)
    assert sha(PKG/'M376_AUDIT.json')==PRIOR
    tested=subprocess.run([sys.executable,'-X','utf8','-B',str(PKG/'test_m376_gate_up_workers.py'),'-v'],capture_output=True,text=True,encoding='utf-8')
    if tested.returncode or 'Ran 12 tests' not in tested.stderr or not tested.stderr.rstrip().endswith('OK'):raise RuntimeError(tested.stdout+tested.stderr)
    negative=self_test()
    check=subprocess.run([r'C:\Users\30429\.cache\codex-runtimes\codex-primary-runtime\dependencies\native\powershell\pwsh.exe','-NoProfile','-File',str(HERE/'m376_control.ps1'),'-Mode','SelfTest'],capture_output=True,text=True,encoding='utf-8')
    if check.returncode or 'M376_CONTROL_SELF_TEST_PASS' not in check.stdout:raise RuntimeError(check.stdout+check.stderr)
    result=dict(status='PASS_OFFLINE_GATE_UP_WORKER_COMPONENT_READY',target_build_id='0x4D333537',prior_raw_sha256=PRIOR,
        manifest_sha256=sha(PKG/'PACKAGE_MANIFEST.json'),tests_run=12,collector_negative_checks=negative,
        package_files=manifest['file_count'],package_bytes=manifest['total_bytes'],python310_syntax=True,default_disabled=True,
        host_source_sha256={n:sha(HERE/n) for n in ('m376_control.ps1','m376_workflow.py','m376_gate_up_workers.py')},
        evidence_level='L0_CPU_PACKAGE_ONLY',board_run=False,performance_pass=False,
        rejected_attempts=['Initial preparation derived wrong local PowerShell path; fixed to explicit prescribed runtime. No serial/upload/board action in that attempt. Existing payloads unchanged and fullSHA rechecked; finish only current failed preparation level.'],
        next_step='Await human COM3 sudo renewal, then one check/upload/CPU component, representative family numerical gate afterward')
    atomic(PREP/'TEST_OUTPUT.txt',(tested.stdout+tested.stderr).encode('utf-8'),immutable=True)
    atomic(PREP/'CONTROL_TEST_OUTPUT.txt',(check.stdout+check.stderr).encode('utf-8'),immutable=True)
    atomic(PREP/'RESULT.json',encoded(result),immutable=True);digest=sha(PREP/'RESULT.json')
    sync('latest_m376_gate_up_worker_preparation',dict(status=result['status'],result=(PREP/'RESULT.json').relative_to(ROOT).as_posix(),sha256=digest,manifest_sha256=result['manifest_sha256']),
        f'## M376 gate_up双worker组件准备及本地路径修复闭合（2026-10-03）\n\nBuild0x4D333537未加载；初稿本地PowerShell路径推导错误、控制子进程未启动，改为固定显式路径，只续完本级，已生成载荷全SHA原字节不变。12项新包检查、{negative}项回收负例、控制故意失败/收集失败停止/Python3.10通过。准备SHA {digest}，manifest {result["manifest_sha256"]}，{result["package_files"]}载荷{result["package_bytes"]}B。未上传/Overlay/模型/FPGA；COM3 sudo另有阻塞记录，收到人工恢复后一次检查。下一步板端CPU组件→代表gate_up family→逐级数值→单/双worker轻量交错，无净收益关闭。原40.81%保持。')
    print(json.dumps(dict(status=result['status'],sha256=digest,manifest_sha256=result['manifest_sha256'],negatives=negative,files=result['package_files'],bytes=result['package_bytes'])))

def collect(path):
    digest,raw,r=decode((ROOT/path).read_text(encoding='utf-8-sig'))
    atomic(RUN/'BOARD_RESULT.json',raw,immutable=True)
    note=f'## M376 gate_up双worker板端CPU组件 {r["status"]}（2026-10-03）\n\n目标0x4D333537未加载；实际Linux Python/NumPy冻结parser/Future及显式fake DMA。原rc{r["gate_return_code"]}，原SHA {digest}。仅组件能力，无Overlay/模型/FPGA/实际runtime容量/性能。通过后准备代表gate_up family硬件数值；失败停本级。'
    sync('latest_m376_gate_up_worker_board',dict(status=r['status'],result=(RUN/'BOARD_RESULT.json').relative_to(ROOT).as_posix(),sha256=digest,performance_pass=False,numerical_pass=False),note)
    atomic(RUN/'REPORT.md',('# M376 gate_up双解析worker板端组件\n\n'+note+'\n\n'+r.get('test_output','')+'\n').encode('utf-8'),immutable=True)
    print(json.dumps(dict(status=r['status'],sha256=digest,gate_rc=r['gate_return_code'])))

if __name__=='__main__':
    if sys.argv[1:]==['prepare']:prepare()
    elif sys.argv[1:]==['finish']:finish_preparation()
    elif sys.argv[1:]==['transfer']:transfer()
    elif len(sys.argv)==3 and sys.argv[1]=='collect':collect(sys.argv[2])
    else:raise SystemExit('prepare | transfer | collect logpath')
