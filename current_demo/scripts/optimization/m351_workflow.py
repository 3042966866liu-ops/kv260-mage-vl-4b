"""Prepare immutable component package / recover exactly one saved board result."""
import ast
import base64
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
sys.dont_write_bytecode=True
ROOT=Path(__file__).resolve().parents[2]
HERE=Path(__file__).resolve().parent
BASE=ROOT/'deployment/mage_vl4b/optimization_v1'
PKG=BASE/'candidates/M351-ps-read-component-01'
PREP=BASE/'runs/M351-ps-read-preparation-01'
RUN=BASE/'runs/M351-ps-read-board-01'
PRIOR='087bd3fe93ef78d33e306f4b431937da01266b37a46995cd5a8b557e9719c256'
SOURCE='5d53ea406e57de88f8c14d9bc4e1cb0c0049ff0b8f4bcf620e05745fcd82b201'

def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def encoded(value):return (json.dumps(value,ensure_ascii=True,indent=2)+'\n').encode('utf-8')
def atomic(path,raw,immutable=False):
    path.parent.mkdir(parents=True,exist_ok=True)
    if immutable and path.exists():
        if path.read_bytes()!=raw:raise RuntimeError('Immutable result differs')
        return
    temp=path.with_name(path.name+'.m351-part')
    with temp.open('wb') as f:f.write(raw);f.flush();os.fsync(f.fileno())
    os.replace(temp,path)

def decode(log):
    hashes=re.findall(r'M351_RESULT_SHA256=([0-9a-f]{64})',log)
    codes=re.findall(r'M351_SAVED_GATE_RC=(\d+)',log)
    chunks=re.findall(r'M351_RESULT_CHUNK=(\d+)/(\d+):([A-Za-z0-9+/=]+)',log)
    if len(hashes)!=1 or len(codes)!=1 or not chunks or len(chunks)!=int(chunks[0][1]):raise RuntimeError('Incomplete/duplicate result')
    pieces=[]
    for i,(index,total,data) in enumerate(chunks):
        if int(index)!=i or int(total)!=len(chunks):raise RuntimeError('Unordered/duplicate chunk')
        part=base64.b64decode(data,validate=True)
        if not 0<len(part)<=1800:raise RuntimeError('Chunk exceeds limit')
        pieces.append(part)
    raw=b''.join(pieces);digest=hashlib.sha256(raw).hexdigest()
    if digest!=hashes[0]:raise RuntimeError('Raw SHA differs')
    r=json.loads(raw);code=int(codes[0])
    if r['gate_level']!='PS-only-fixture-component' or r['prior_raw_sha256']!=PRIOR or r['build_id']!='0x4D395832':raise RuntimeError('Wrong gate/identity')
    if type(r['gate_return_code']) is not int or r['gate_return_code']!=code or code not in (0,1):raise RuntimeError('Original rc differs')
    for key in ('overlay_loaded','model_forward_calls','fpga_transactions','real_assets_read','memory_capacity_proven','numerical_pass','performance_pass','formal_promotion_allowed','cache_eviction','extra_pynq_allocations'):
        if r[key]:raise RuntimeError('Wrong evidence scope')
    done=re.findall(r'M351_DONE gate_rc=(\d+) export_rc=(\d+)',log)
    if done and (len(done)!=1 or done[0]!=(str(code),'0')):raise RuntimeError('Gate/export code differs')
    if r['status']=='PASS_PS_COMPONENT_ONLY_NO_FPGA':
        if code or r['errors'] or r['tests_run']!=28 or r['windows_ctime_adapter_active'] or r['copy_source_sha256']!=SOURCE:raise RuntimeError('Incomplete PASS')
        if r['maximum_ps_payload_bytes']!=27852800 or r['maximum_window_bytes_per_port']!=6963200:raise RuntimeError('Window geometry differs')
        if r['lifecycle']['active_workers'] or r['lifecycle']['remaining_fixture_files']:raise RuntimeError('Lifecycle incomplete')
        if r['elapsed_s']>60 or r['platform']['euid']!=0 or r['platform']['uname'][0]!='Linux':raise RuntimeError('Environment/budget differs')
        if r['strict_linux_file_identity_fields']!=['dev','ino','size','mtime_ns','ctime_ns','mode','nlink']:raise RuntimeError('Identity check weakened')
        if 'Ran 28 tests' not in r['test_output'] or not r['test_output'].rstrip().endswith('OK'):raise RuntimeError('Test result incomplete')
    elif r['status']=='FAIL_PS_COMPONENT_ONLY':
        if code!=1 or not r['errors']:raise RuntimeError('Failure scope inconsistent')
    else:raise RuntimeError('Unknown status')
    return digest,raw,r

def self_test():
    def export(r):
        raw=encoded(r);parts=[raw[i:i+1800] for i in range(0,len(raw),1800)]
        return 'M351_RESULT_SHA256='+hashlib.sha256(raw).hexdigest()+'\nM351_SAVED_GATE_RC='+str(r['gate_return_code'])+'\n'+''.join('M351_RESULT_CHUNK='+str(i)+'/'+str(len(parts))+':'+base64.b64encode(p).decode('ascii')+'\n' for i,p in enumerate(parts))+'M351_DONE gate_rc='+str(r['gate_return_code'])+' export_rc=0\n'
    fail=dict(status='FAIL_PS_COMPONENT_ONLY',gate_level='PS-only-fixture-component',prior_raw_sha256=PRIOR,build_id='0x4D395832',gate_return_code=1,errors=['fixture failure'*500])
    for key in ('overlay_loaded','model_forward_calls','fpga_transactions','real_assets_read','memory_capacity_proven','numerical_pass','performance_pass','formal_promotion_allowed','cache_eviction','extra_pynq_allocations'):fail[key]=False
    good=dict(fail,status='PASS_PS_COMPONENT_ONLY_NO_FPGA',gate_return_code=0,errors=[],tests_run=28,windows_ctime_adapter_active=False,
        copy_source_sha256=SOURCE,maximum_ps_payload_bytes=27852800,maximum_window_bytes_per_port=6963200,
        lifecycle=dict(active_workers=[],remaining_fixture_files=[]),elapsed_s=1,platform=dict(euid=0,uname=['Linux']),
        strict_linux_file_identity_fields=['dev','ino','size','mtime_ns','ctime_ns','mode','nlink'],test_output='Ran 28 tests\nOK\n')
    assert decode(export(fail))[2]==fail and decode(export(good))[2]==good
    assert decode(export(fail).split('M351_DONE')[0])[2]==fail
    bads=[export(fail).replace('M351_SAVED_GATE_RC=1','M351_SAVED_GATE_RC=0'),export(fail).replace('M351_RESULT_CHUNK=1/','M351_RESULT_CHUNK=0/'),export(fail).replace('export_rc=0','export_rc=1'),export(fail)+'M351_RESULT_SHA256='+'0'*64]
    for k,v in [('tests_run',27),('windows_ctime_adapter_active',True),('maximum_ps_payload_bytes',1),('performance_pass',True),('extra_pynq_allocations',1),('elapsed_s',61),('errors',['error']),('strict_linux_file_identity_fields',['ino']),('lifecycle',dict(active_workers=['active'],remaining_fixture_files=[]))]:bads.append(export(dict(good,**{k:v})))
    for bad in bads:
        try:decode(bad)
        except (RuntimeError,ValueError):pass
        else:raise AssertionError('Invalid result accepted')
    return len(bads)

def sync(key,value,note):
    path=ROOT/'deployment/mage_vl4b/BOARD_GATE_RESULT.json';b=json.loads(path.read_text(encoding='utf-8'));b[key]=value;atomic(path,encoded(b))
    for name in ('CURRENT_STATE.md','docsMILESTONES.md'):
        p=ROOT/name;old=p.read_text(encoding='utf-8-sig')
        if value['sha256'] not in old:
            title,rest=old.split('\n',1);atomic(p,(title+'\n\n'+note.rstrip()+'\n\n'+rest.lstrip('\n')).encode('utf-8'))
    assert json.loads(path.read_text(encoding='utf-8'))[key]['sha256']==value['sha256']
    assert all(value['sha256'] in (ROOT/n).read_text(encoding='utf-8') for n in ('CURRENT_STATE.md','docsMILESTONES.md'))

def prepare():
    if PKG.exists() or PREP.exists():raise RuntimeError('Immutable preparation exists')
    recovery={}
    for name in ('CURRENT_STATE.md','DEPLOYMENT_OPERATION_MISTAKES_REVIEW.md','docsMILESTONES.md','deployment/mage_vl4b/BOARD_GATE_RESULT.json'):
        p=ROOT/name;text=p.read_text(encoding='utf-8-sig');recovery[name]=dict(sha256=sha(p),bytes=p.stat().st_size,lines=len(text.splitlines()))
    b=json.loads((ROOT/'deployment/mage_vl4b/BOARD_GATE_RESULT.json').read_text(encoding='utf-8'));prior=b['latest_m350_ps_read_ahead_design']
    assert prior['sha256']==PRIOR and sha(ROOT/prior['result'])==PRIOR
    assert all(PRIOR in (ROOT/n).read_text(encoding='utf-8') for n in ('CURRENT_STATE.md','docsMILESTONES.md'))
    tested=subprocess.run([sys.executable,'-B',str(HERE/'test_ps_read_ahead.py')],capture_output=True,text=True,encoding='utf-8')
    if tested.returncode or 'Ran 28 tests' not in tested.stderr:raise RuntimeError(tested.stdout+tested.stderr)
    negatives=self_test()
    pwsh='C:/Users/30429/.cache/codex-runtimes/codex-primary-runtime/dependencies/native/powershell/pwsh.exe'
    control=subprocess.run([pwsh,'-NoProfile','-File',str(HERE/'m351_control.ps1'),'-Mode','SelfTest'],capture_output=True,text=True,encoding='utf-8')
    if control.returncode or 'M351_CONTROL_SELF_TEST_PASS' not in control.stdout:raise RuntimeError(control.stdout+control.stderr)
    names=('ps_read_ahead.py','board_safety.py','test_ps_read_ahead.py','m351_component_gate.py','m351_export_result.py')
    for name in names:
        tree=ast.parse((HERE/name).read_text(encoding='utf-8'),feature_version=(3,10))
        imports=[a.name.split('.')[0] for n in ast.walk(tree) if isinstance(n,ast.Import) for a in n.names]+[(n.module or '').split('.')[0] for n in ast.walk(tree) if isinstance(n,ast.ImportFrom)]
        if {'pynq','torch','board_runtime','video_server'}.intersection(imports):raise RuntimeError('Forbidden model/PL import')
        if name=='ps_read_ahead.py':
            attrs={n.func.attr for n in ast.walk(tree) if isinstance(n,ast.Call) and isinstance(n.func,ast.Attribute)}
            if attrs.intersection({'allocate','freebuffer','posix_fadvise','madvise','Overlay','forward'}):raise RuntimeError('Forbidden allocator/cache/model call')
    PKG.mkdir(parents=True);PREP.mkdir(parents=True)
    for name in names:shutil.copyfile(HERE/name,PKG/name)
    atomic(PKG/'DESIGN_PREREQUISITE.json',encoded(dict(raw_sha256=PRIOR,component_default_disabled=True,scope='CPU-only self-owned fixture tests; no model/PL')))
    runner='\n'.join(['#!/usr/bin/env bash','set -euo pipefail','cd "$(dirname "${BASH_SOURCE[0]}")"','manifest_sha=${1:?exact manifest SHA required}',
        '[[ "${2:-}" == "--enable-fixture-gate" ]] || { echo M351_DISABLED_BY_DEFAULT; exit 2; }',
        "printf '%s  PACKAGE_MANIFEST.json\\n' \"$manifest_sha\" | sha256sum -c -",'sha256sum -c SHA256SUMS','sudo -n true',
        '[[ ! -e /home/ubuntu/m351_ps_component_evidence_01 ]] || { echo M351_IMMUTABLE_RESULT_EXISTS; exit 2; }','set +e',
        'sudo -n env PYTHONDONTWRITEBYTECODE=1 /usr/local/share/pynq-venv/bin/python3 -B ./m351_component_gate.py "$manifest_sha" --enable-fixture-gate','gate_rc=$?',
        'sudo -n /usr/local/share/pynq-venv/bin/python3 -B ./m351_export_result.py','export_rc=$?','set -e',
        "printf 'M351_DONE gate_rc=%s export_rc=%s\\n' \"$gate_rc\" \"$export_rc\"",'if [[ "$gate_rc" -ne 0 ]]; then exit "$gate_rc"; fi','exit "$export_rc"',''])
    atomic(PKG/'run_m351_component.sh',runner.encode('utf-8'))
    rows=[dict(path=p.name,bytes=p.stat().st_size,sha256=sha(p)) for p in sorted(PKG.iterdir())]
    atomic(PKG/'SHA256SUMS',''.join(r['sha256']+'  '+r['path']+'\n' for r in rows).encode('ascii'))
    rows.append(dict(path='SHA256SUMS',bytes=(PKG/'SHA256SUMS').stat().st_size,sha256=sha(PKG/'SHA256SUMS')))
    atomic(PKG/'PACKAGE_MANIFEST.json',encoded(dict(schema='m351-ps-read-cpu-component-v1',files=rows,file_count=len(rows),total_bytes=sum(r['bytes'] for r in rows))))
    assert {p.name for p in PKG.iterdir()}=={r['path'] for r in rows}|{'PACKAGE_MANIFEST.json'}
    assert not list(PKG.rglob('*.pyc')) and not list(PKG.rglob('__pycache__'))
    atomic(PREP/'TEST_OUTPUT.txt',(tested.stdout+tested.stderr).encode('utf-8'));atomic(PREP/'CONTROL_OUTPUT.txt',(control.stdout+control.stderr).encode('utf-8'))
    r=dict(status='PASS_OFFLINE_PS_READ_COMPONENT_PREPARATION',evidence_level='L0_COMPONENT_AND_PACKAGE_ONLY',build_id='0x4D395832',
        recovery_read=recovery,prior_raw_sha256=PRIOR,component_tests=28,collector_negative_checks=negatives,controller_failure_self_test=True,
        python310_syntax=True,windows_ctime_test_adapter=True,strict_linux_identity_unchanged=True,
        component_implemented=True,component_default_disabled=True,planned_ps_payload_bytes=27852800,extra_pynq_allocation_calls=0,
        package_files=len(rows),package_bytes=sum(row['bytes'] for row in rows),manifest_sha256=sha(PKG/'PACKAGE_MANIFEST.json'),
        component_sha256=sha(HERE/'ps_read_ahead.py'),controller_sha256=sha(HERE/'m351_control.ps1'),workflow_sha256=sha(Path(__file__)),
        board_run=False,memory_capacity_proven=False,numerical_pass=False,performance_pass=False,formal_promotion_allowed=False,
        rejected_attempts=['Windows lstat/fstat ctime differs; initial checks rejected. Explicit Windows test-only adapter removes ctime field; production Linux retains all seven identity fields. No board execution during repair',
            'Python3.10 concurrent.futures.TimeoutError differs from builtin TimeoutError; use explicit FutureTimeoutError alias before package freeze'],
        next_step='One COM3 CPU-only fixture gate after same-terminal sudo, package SHA and bash-n; no model/Overlay/full baseline')
    atomic(PREP/'RESULT.json',encoded(r),immutable=True);digest=sha(PREP/'RESULT.json')
    note=('## M351 普通PS预读组件已实现，离线门禁通过（2026-10-01）\n\n'
        f'稳定Build0x4D395832；默认关闭组件、28项真实fixture/错误/生命周期检查、{negatives}项收集负例与控制故意失败自测通过。'
        f'隔离包{len(rows)}载荷/{r["package_bytes"]}B，manifest `{r["manifest_sha256"]}`。'
        '一个26.5625MiB普通PS slot，无额外PYNQ分配调用；后台读、前景复制同步、原bank复用。'
        'Windows测试ctime适配明确记录，Linux七字段检查未弱化；MMIO/缓冲/容量为明确测试替身。'
        '仅L0，未上板/Overlay/模型，非真实运行时容量、FPGA数值或性能PASS。'
        f'证据 `{(PREP/"RESULT.json").relative_to(ROOT).as_posix()}` SHA `{digest}`。'
        '下一步同COM3 sudo/包SHA/bash-n后执行一次CPU小文件组件门禁；失败只收集，不重复。稳定源/服务/回滚/boot/DTB/CMA保持。\n\n')
    sync('latest_m351_ps_component_preparation',dict(status=r['status'],result=(PREP/'RESULT.json').relative_to(ROOT).as_posix(),sha256=digest,
        manifest_sha256=r['manifest_sha256'],board_run=False,performance_pass=False),note)
    atomic(PREP/'REPORT.md',('# M351 组件准备\n\n'+note).encode('utf-8'))
    print(json.dumps(dict(status=r['status'],sha256=digest,manifest_sha256=r['manifest_sha256'],files=len(rows),bytes=r['package_bytes'])))

def collect(logpath):
    digest,raw,r=decode((ROOT/logpath).read_text(encoding='utf-8-sig'))
    if r['manifest_sha256']!=sha(PKG/'PACKAGE_MANIFEST.json'):raise RuntimeError('Package mismatch')
    atomic(RUN/'BOARD_RESULT.json',raw,immutable=True)
    note=('## M351 板端PS预读组件 '+r['status']+'（2026-10-01）\n\n'
        '稳定Build0x4D395832；真实Linux文件读取及NumPy复制，MMIO/缓冲/容量为明确替身，无Overlay/模型/真实权重资产/FPGA事务。'
        f'原始结果 `{(RUN/"BOARD_RESULT.json").relative_to(ROOT).as_posix()}` SHA `{digest}`；'
        f'测试数{r.get("tests_run",0)}，错误 `{json.dumps(r["errors"],ensure_ascii=False)}`。'
        '不证明实际runtime容量、硬件输出一致或提速；原双bank90.5625MiB门槛及独立64MiB余量保持。'
        '通过后下一步仅准备独立只加载runtime容量门禁；失败仅在组件级调试，不重复完整模型。稳定源/服务/回滚/boot/DTB/CMA保持。\n\n')
    sync('latest_m351_ps_component_board',dict(status=r['status'],result=(RUN/'BOARD_RESULT.json').relative_to(ROOT).as_posix(),sha256=digest,
        evidence_level='BOARD_CPU_COMPONENT_ONLY',memory_capacity_proven=False,numerical_pass=False,performance_pass=False,formal_promotion_allowed=False),note)
    atomic(RUN/'REPORT.md',('# M351 板端组件结果\n\n'+note).encode('utf-8'))
    print(json.dumps(dict(status='M351_RESULT_SYNCHRONIZED',raw_sha256=digest,component_status=r['status'])))

if __name__=='__main__':
    if sys.argv[1:]==['prepare']:prepare()
    elif sys.argv[1:]==['selftest']:print('M351_COLLECTOR_SELF_TEST_PASS negatives='+str(self_test()))
    elif len(sys.argv)==3 and sys.argv[1]=='collect':collect(sys.argv[2])
    else:raise SystemExit('prepare | selftest | collect logpath')
