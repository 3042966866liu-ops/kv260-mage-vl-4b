"""Freeze CPU-only package and strictly collect one saved board result."""
import ast
import base64
import hashlib
import json
from pathlib import Path
import re
import shutil
import subprocess
import sys
from m351_workflow import ROOT, HERE, BASE, sha, encoded, atomic, sync

PRIOR = '4a5b4ad459f06f0814ba7bc2b41f377718ac3828c5c311191b60eec62c82946c'
PKG = BASE/'candidates/M373-future-wait-component-01'
PREP = BASE/'runs/M373-future-wait-preparation-01'
RUN = BASE/'runs/M373-future-wait-board-01'
FALSE_KEYS = ('overlay_loaded','real_assets_read','model_forward_calls','fpga_transactions',
    'extra_pynq_allocations','ps_prefetch_enabled','memory_capacity_proven','numerical_pass',
    'performance_pass','formal_promotion_allowed')

def decode(log):
    hashes = re.findall(r'M373_RESULT_SHA256=([0-9a-f]{64})', log)
    codes = re.findall(r'M373_SAVED_GATE_RC=(\d+)', log)
    chunks = re.findall(r'M373_RESULT_CHUNK=(\d+)/(\d+):([A-Za-z0-9+/=]+)', log)
    if len(hashes)!=1 or len(codes)!=1 or not chunks or len(chunks)!=int(chunks[0][1]): raise RuntimeError('Incomplete/duplicate export')
    parts=[]
    for i,(index,total,data) in enumerate(chunks):
        if int(index)!=i or int(total)!=len(chunks): raise RuntimeError('Chunk order differs')
        part=base64.b64decode(data,validate=True)
        if not 0<len(part)<=900: raise RuntimeError('Chunk length differs')
        parts.append(part)
    raw=b''.join(parts); digest=hashlib.sha256(raw).hexdigest()
    if digest!=hashes[0]: raise RuntimeError('SHA differs')
    row=json.loads(raw); code=int(codes[0])
    if row['prior_raw_sha256']!=PRIOR or row['target_build_id']!='0x4D333537' or row['gate_level']!='CPU-Future-Condition-capability': raise RuntimeError('Evidence identity differs')
    if any(row[k] for k in FALSE_KEYS): raise RuntimeError('Scope differs')
    if type(row['gate_return_code']) is not int or row['gate_return_code']!=code or code not in (0,1): raise RuntimeError('Saved rc differs')
    done=re.findall(r'M373_DONE gate_rc=(\d+) export_rc=(\d+)',log)
    if done and (len(done)!=1 or done[0]!=(str(code),'0')): raise RuntimeError('Run/export rc differs')
    if row['status']=='PASS_FUTURE_WAIT_CPU_COMPONENT_ONLY':
        if code or row['errors'] or row['tests_run']!=17 or row['elapsed_s']>20: raise RuntimeError('PASS incomplete')
        if row['platform']['euid']!=0 or row['platform']['uname'][0]!='Linux': raise RuntimeError('Board identity missing')
        if 'Ran 17 tests' not in row['test_output'] or not row['test_output'].rstrip().endswith('OK'): raise RuntimeError('Test transcript missing')
        probe=row['blocking_probe']; wait=probe['summary']['parse']; record=probe['records']
        if probe['value']!=17 or not probe['condition_binding_restored'] or probe['trace_exclusive_closure_ns']!=0 or row['lifecycle']['active_workers']: raise RuntimeError('Lifecycle/closure differs')
        if len(record)!=1 or wait['calls']!=1 or wait['condition_wait_calls']!=1 or not 0<wait['condition_wait_s']<=wait['result_wall_s']: raise RuntimeError('Blocking wait unproven')
        if record[0]['condition_wait_calls']!=1 or record[0]['exception'] is not None or record[0]['ready_before'] or not 0<record[0]['condition_wait_ns']<=record[0]['result_wall_ns']: raise RuntimeError('Blocking record differs')
        if abs(record[0]['condition_wait_ns']/1e9-wait['condition_wait_s'])>1e-12 or abs(record[0]['result_wall_ns']/1e9-wait['result_wall_s'])>1e-12: raise RuntimeError('Wait totals differ')
        events=probe['trace_events']
        if sum(x['exclusive_ns'] for x in events)!=events[0]['inclusive_ns'] or sum(x['name']=='future_condition_wait' for x in events)!=1: raise RuntimeError('Trace wait differs')
        if not re.fullmatch('[0-9a-f]{64}',probe['future_result_source_sha256']): raise RuntimeError('Python source SHA missing')
    elif row['status']=='FAIL_FUTURE_WAIT_CPU_COMPONENT':
        if code!=1 or not row['errors']: raise RuntimeError('Failure inconsistent')
    else: raise RuntimeError('Unknown status')
    return digest,raw,row

def export_fake(row):
    raw=encoded(row); parts=[raw[i:i+900] for i in range(0,len(raw),900)]
    return 'M373_RESULT_SHA256='+hashlib.sha256(raw).hexdigest()+'\nM373_SAVED_GATE_RC='+str(row['gate_return_code'])+'\n'+''.join(f'M373_RESULT_CHUNK={i}/{len(parts)}:'+base64.b64encode(p).decode()+'\n' for i,p in enumerate(parts))+f'M373_DONE gate_rc={row["gate_return_code"]} export_rc=0\n'

def collector_test():
    row=dict(status='FAIL_FUTURE_WAIT_CPU_COMPONENT',gate_level='CPU-Future-Condition-capability',prior_raw_sha256=PRIOR,target_build_id='0x4D333537',gate_return_code=1,errors=['explicit simulated failure'*120])
    row.update({k:False for k in FALSE_KEYS}); log=export_fake(row)
    assert decode(log)[2]==row and decode(log.split('M373_DONE')[0])[2]==row
    bad=[log.replace('M373_SAVED_GATE_RC=1','M373_SAVED_GATE_RC=0'),log.replace('M373_RESULT_CHUNK=1/','M373_RESULT_CHUNK=0/'),log.replace('export_rc=0','export_rc=1'),log+'M373_RESULT_SHA256='+'0'*64,log.replace('M373_RESULT_CHUNK=0/','M373_RESULT_CHUNK=9/'),log.replace('M373_RESULT_CHUNK=1/','BROKEN=1/')]
    for key in FALSE_KEYS: bad.append(export_fake(dict(row,**{key:True})))
    for item in bad:
        try: decode(item)
        except (RuntimeError, ValueError): pass
        else: raise AssertionError('Invalid export accepted')
    return len(bad)

def prepare():
    if PKG.exists() or PREP.exists(): raise RuntimeError('Immutable preparation exists')
    board=json.loads((ROOT/'deployment/mage_vl4b/BOARD_GATE_RESULT.json').read_text(encoding='utf-8'))
    prior=board['latest_m372_prefetch_future_review']
    assert prior['sha256']==PRIOR and sha(ROOT/prior['result'])==PRIOR
    assert all(PRIOR in (ROOT/p).read_text(encoding='utf-8-sig') for p in ('CURRENT_STATE.md','docsMILESTONES.md'))
    sources=json.loads((ROOT/prior['result']).read_text(encoding='utf-8'))
    assert sha(HERE/'m372_future_wait.py')==sources['source_sha256']['m372_future_wait.py']
    assert sha(HERE/'test_m372_future_wait.py')==sources['source_sha256']['test_m372_future_wait.py']
    PKG.mkdir(parents=True)
    for name in ('m372_future_wait.py','m373_component_gate.py','m373_export_result.py'): shutil.copyfile(HERE/name,PKG/name)
    for row in sources['verified_source_files']:
        if row['module'] not in ('m238_prefill_runtime','m236_prefill_runtime'): continue
        source=ROOT/row['path']; assert sha(source)==row['sha256']; shutil.copyfile(source,PKG/source.name)
    trace=BASE/'candidates/M371-candidate-prefill-profile-01/decode_trace.py'
    trace_manifest=json.loads((trace.parent/'PACKAGE_MANIFEST.json').read_text(encoding='utf-8'))
    entry=next(x for x in trace_manifest['files'] if x['path']=='decode_trace.py')
    assert sha(trace)==entry['sha256']; shutil.copyfile(trace,PKG/trace.name)
    text=(HERE/'test_m372_future_wait.py').read_text(encoding='utf-8')
    text=text.replace("ROOT = Path(__file__).resolve().parents[2]", "ROOT = Path(__file__).resolve().parent")
    text=text.replace("FROZEN = ROOT / 'release_staging/kv260-mage-vl-4b-prebuilt-install-20260926-v7/deployment/mage_vl4b/m242_m241_fixed_text_board_candidate'", 'FROZEN = ROOT')
    text=text.replace("path=ROOT/'deployment/mage_vl4b/optimization_v1/candidates/M371-candidate-prefill-profile-01/decode_trace.py'", "path=ROOT/'decode_trace.py'")
    atomic(PKG/'m373_test_future_wait.py',text.encode('utf-8'))
    shutil.copyfile(ROOT/prior['result'],PKG/'M372_PREREQUISITE.json')
    tested=subprocess.run([sys.executable,'-X','utf8','-B',str(PKG/'m373_test_future_wait.py')],capture_output=True,text=True,encoding='utf-8')
    if tested.returncode or 'Ran 17 tests' not in tested.stderr: raise RuntimeError(tested.stdout+tested.stderr)
    for path in PKG.glob('*.py'): ast.parse(path.read_text(encoding='utf-8'),feature_version=(3,10))
    negatives=collector_test()
    runner='\n'.join(['#!/usr/bin/env bash','set -euo pipefail','cd "$(dirname "${BASH_SOURCE[0]}")"','manifest_sha=${1:?exact manifest SHA required}',
        '[[ "${2:-}" == "--enable-fixture-gate" ]] || { echo M373_DISABLED_BY_DEFAULT; exit 2; }',
        'printf \'%s  PACKAGE_MANIFEST.json\\n\' "$manifest_sha" | sha256sum -c -','sha256sum -c SHA256SUMS','sudo -n true',
        '[[ ! -e /home/ubuntu/m373_future_wait_evidence_01 ]] || { echo M373_RESULT_EXISTS_COLLECT_ONLY; exit 2; }','set +e',
        'sudo -n env PYTHONDONTWRITEBYTECODE=1 /usr/local/share/pynq-venv/bin/python3 -B ./m373_component_gate.py "$manifest_sha" --enable-fixture-gate','gate_rc=$?',
        'sudo -n env PYTHONDONTWRITEBYTECODE=1 /usr/local/share/pynq-venv/bin/python3 -B ./m373_export_result.py','export_rc=$?','set -e',
        'printf \'M373_DONE gate_rc=%s export_rc=%s\\n\' "$gate_rc" "$export_rc"','if [[ "$gate_rc" -ne 0 ]]; then exit "$gate_rc"; fi','exit "$export_rc"',''])
    atomic(PKG/'run_m373_component.sh',runner.encode('utf-8'))
    rows=[dict(path=p.name,bytes=p.stat().st_size,sha256=sha(p)) for p in sorted(PKG.iterdir())]
    atomic(PKG/'SHA256SUMS',''.join(x['sha256']+'  '+x['path']+'\n' for x in rows).encode('ascii'))
    rows.append(dict(path='SHA256SUMS',bytes=(PKG/'SHA256SUMS').stat().st_size,sha256=sha(PKG/'SHA256SUMS')))
    atomic(PKG/'PACKAGE_MANIFEST.json',encoded(dict(schema='m373-future-wait-capability-v1',files=rows,file_count=len(rows),total_bytes=sum(x['bytes'] for x in rows))))
    whitelist={'m372_future_wait.py','m373_component_gate.py','m373_export_result.py','m238_prefill_runtime.py','m236_prefill_runtime.py','decode_trace.py','m373_test_future_wait.py','M372_PREREQUISITE.json','run_m373_component.sh','SHA256SUMS','PACKAGE_MANIFEST.json'}
    assert {p.name for p in PKG.iterdir()}==whitelist
    result=dict(status='PASS_OFFLINE_FUTURE_WAIT_BOARD_PACKAGE_READY',evidence_level='L0_CPU_PACKAGE_ONLY',target_build_id='0x4D333537',prior_raw_sha256=PRIOR,
        adapted_tests=17,collector_negative_checks=negatives,python310_syntax=True,manifest_sha256=sha(PKG/'PACKAGE_MANIFEST.json'),
        package_files=len(rows),package_bytes=sum(x['bytes'] for x in rows),default_disabled=True,
        paths_only_test_adaptation=True,frozen_observer_unchanged=True,frozen_scheduler_sources_unchanged=True,
        board_python_support_proven=False,actual_model_wait_s=None,ps_candidate_admission_resolved=False,
        next_step='COM3 sudo, manifest-first 900B upload and bash-n; execute one CPU-only capability gate. Never repeat to repair collection.')
    result.update({k:False for k in FALSE_KEYS})
    atomic(PREP/'TEST_OUTPUT.txt',(tested.stdout+tested.stderr).encode('utf-8'),immutable=True)
    atomic(PREP/'RESULT.json',encoded(result),immutable=True); digest=sha(PREP/'RESULT.json')
    sync('latest_m373_future_wait_preparation',dict(status=result['status'],result=(PREP/'RESULT.json').relative_to(ROOT).as_posix(),sha256=digest,manifest_sha256=result['manifest_sha256']),
        f'## M373 板端等待钩子能力包准备完成（2026-10-03）\n\n候选目标 Build0x4D333537；M372 同 SHA 观察组件和冻结调度方法，测试仅适配打包路径，17项 CPU 检查通过，{negatives}项回收负例通过。10载荷，默认关闭，无 Overlay/真实资产/模型/FPGA。原始证据 {(PREP/"RESULT.json").relative_to(ROOT).as_posix()} SHA {digest}；manifest {result["manifest_sha256"]}。下一步只运行一次板端 Python Future/Condition 能力门禁；未证明实际解析等待、PS预读容量或新增收益。')
    print(json.dumps(result))

def transfer():
    manifest=json.loads((PKG/'PACKAGE_MANIFEST.json').read_text(encoding='utf-8'))
    rows=[]
    for name in ['PACKAGE_MANIFEST.json']+[x['path'] for x in manifest['files']]:
        log=ROOT/('tmp/m373/upload_'+name.replace('.','_')+'_final.log')
        text=log.read_text(encoding='utf-8-sig')
        if 'M212_CHUNKED_FILE_PASS' not in text or sha(PKG/name) not in text: raise RuntimeError('Transfer final SHA missing')
        prefix='upload_'+name.replace('.','_')
        chunks=sorted((ROOT/'tmp/m373').glob(prefix+'_chunk_*.log'))
        expected=((PKG/name).stat().st_size+899)//900
        if len(chunks)!=expected: raise RuntimeError('Transfer chunk count differs')
        for i,chunk in enumerate(chunks,1):
            data=chunk.read_text(encoding='utf-8-sig')
            if not re.search(r'M212_CHUNK_PASS\s+'+str(i)+r'\s+'+str(expected)+r'\s+'+str(min(i*900,(PKG/name).stat().st_size))+r'\s',data): raise RuntimeError('Transfer chunk receipt differs')
        rows.append(dict(path=name,sha256=sha(PKG/name),final_log_sha256=sha(log),chunks=expected))
    path=BASE/'runs/M373-future-wait-transfer-01/RESULT.json'
    result=dict(status='PASS_MANIFEST_FIRST_900B_FILE_SHA_TRANSFER',manifest_sha256=sha(PKG/'PACKAGE_MANIFEST.json'),files=rows,overlay_loaded=False,gate_started=False)
    atomic(path,encoded(result),immutable=True);digest=sha(path)
    sync('latest_m373_future_wait_transfer',dict(status=result['status'],result=path.relative_to(ROOT).as_posix(),sha256=digest,manifest_sha256=result['manifest_sha256']),f'## M373 CPU 等待组件上传已核对（2026-10-03）\n\nmanifest-first、900B 分块、各块序号/长度及全部文件最终 SHA 通过；尚未执行门禁或 Overlay。证据 {path.relative_to(ROOT).as_posix()} SHA {digest}。下一步 bash-n 与同终端 sudo 后执行一次。')
    print('M373_TRANSFER_SYNCHRONIZED',digest)

def collect(logpath):
    digest,raw,row=decode((ROOT/logpath).read_text(encoding='utf-8-sig'))
    assert row['manifest_sha256']==sha(PKG/'PACKAGE_MANIFEST.json')
    atomic(RUN/'BOARD_RESULT.json',raw,immutable=True)
    note=f'## M373 板端等待钩子小组件 {row["status"]}（2026-10-03）\n\n目标 Build0x4D333537 未加载；CPU-only，实际 Linux Future/Condition、NumPy 与冻结调度方法的明确 PL/解析测试替身。17项检查及真正阻塞等待的观察、方法恢复和 trace 闭合均仅为组件能力证据。原始结果 {(RUN/"BOARD_RESULT.json").relative_to(ROOT).as_posix()} SHA {digest}，原 gate rc{row["gate_return_code"]}。无模型/FPGA/真实资产，非完整模型数值或性能、非PS预读容量PASS。下一步通过后仅准备代表family实际等待诊断；失败停组件级。'
    sync('latest_m373_future_wait_board',dict(status=row['status'],result=(RUN/'BOARD_RESULT.json').relative_to(ROOT).as_posix(),sha256=digest,evidence_level='BOARD_CPU_COMPONENT_ONLY',performance_pass=False,numerical_pass=False),note)
    atomic(RUN/'REPORT.md',('# M373 等待钩子板端能力验证\n\n'+note+'\n\n'+json.dumps(row.get('blocking_probe',{}).get('summary',{}),indent=2)+'\n').encode('utf-8'),immutable=True)
    print(json.dumps(dict(status=row['status'],raw_sha256=digest,gate_rc=row['gate_return_code'])))

if __name__=='__main__':
    if sys.argv[1:]==['prepare']: prepare()
    elif sys.argv[1:]==['transfer']: transfer()
    elif len(sys.argv)==3 and sys.argv[1]=='collect': collect(sys.argv[2])
    else: raise SystemExit('prepare | collect logpath')
