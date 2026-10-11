"""Freeze one offline load-only package, collect saved board bytes, never deploy."""
import ast
import base64
import importlib.util
import json
from pathlib import Path
import re
import subprocess
import sys
sys.dont_write_bytecode=True
ROOT=Path(__file__).resolve().parents[2]
HERE=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('m351_support',HERE/'m351_workflow.py')
w=importlib.util.module_from_spec(spec);spec.loader.exec_module(w)
BASE=ROOT/'deployment/mage_vl4b/optimization_v1'
PKG=BASE/'candidates/M352-load-ps-slot-01'
PREP=BASE/'runs/M352-load-ps-slot-preparation-01'
RUN=BASE/'runs/M352-load-ps-slot-board-01'
PRIOR='6274767c15ac4ea5c81e6289ef4f90d6cd7cd32c5735b5617e6c3a450cf8ef41'
AUDIT='e4ed4b37bfa2122e0d9dd5998665767dfd47bf3e346cd312bbd7080d3437ff8e'


def validate(r):
    if r['build_id']!='0x4D395832' or r['gate_level']!='load-only-memory-diagnostic':raise RuntimeError('Wrong build/gate')
    if r.get('prior_board_sha256')!=PRIOR:raise RuntimeError('Wrong prerequisite')
    code=r['gate_return_code']
    if type(code) is not int or code not in (0,1):raise RuntimeError('Invalid saved rc')
    for k in ('numerical_pass','performance_pass','formal_promotion_allowed','worker_started','model_forward_calls','fpga_transactions','serving_after_vision_capacity_proven'):
        if r[k]:raise RuntimeError('Wrong evidence scope: '+k)
    if r.get('host_calls',0) or r.get('logical_calls',0) or r['blocked_inference_attempts']:raise RuntimeError('Unexpected transaction/guard call')
    if code==0:
        if r['status']!='PASS_LOAD_ONLY_PS_SLOT_CAPACITY' or r['errors'] or not r['memory_capacity_proven']:raise RuntimeError('Invalid capacity PASS')
        if not r['overlay_loaded'] or r['unsafe_buffers_retained'] or not r['safe_buffers_released'] or not r['ps_slot_released']:raise RuntimeError('Incomplete lifecycle')
        if len(r['allocated_buffers'])!=7 or len(r['released_buffers'])!=7 or r['extra_pynq_allocations']!=0:raise RuntimeError('Allocation count differs')
        if sorted(r['allocated_buffers'],key=lambda x:x['address'])!=sorted(r['released_buffers'],key=lambda x:x['address']):raise RuntimeError('Allocation/free identity differs')
        if r['ps_slot']['payload_bytes']!=27852800 or len(r['ps_slot']['ports'])!=4 or not r['ps_slot']['all_ports_materialized']:raise RuntimeError('PS slot unproven')
        for row in r['ps_slot']['ports']:
            if row['bytes']!=6963200 or not row['readback'] or not row['last_byte_touched']:raise RuntimeError('Incomplete touch proof')
        for key in ('pre_slot_eligibility','post_slot_eligibility','settled_eligibility'):
            e=r[key]
            if e['required_cma_bytes']!=67108864 or e['required_mem_available_bytes']!=(94961664 if key=='pre_slot_eligibility' else 67108864):raise RuntimeError('Reserve weakened')
            if not e['meets_load_only_threshold'] or e['cma_free_bytes']<67108864 or e['mem_available_bytes']<e['required_mem_available_bytes']:raise RuntimeError('Capacity contradiction')
        if not r['boot_unchanged'] or not r['cmdline_unchanged'] or r['elapsed_s_diagnostic_not_performance']>600:raise RuntimeError('Protection/budget differs')
    elif not r['errors'] or r['memory_capacity_proven']:raise RuntimeError('Invalid FAIL')


def decode(log):
    hashes=re.findall(r'M352_RESULT_SHA256=([0-9a-f]{64})',log)
    codes=re.findall(r'M352_SAVED_GATE_RC=([01])',log)
    chunks=re.findall(r'M352_RESULT_CHUNK=(\d+)/(\d+):([A-Za-z0-9+/=]+)',log)
    if len(hashes)!=1 or len(codes)!=1 or not chunks or len(chunks)!=int(chunks[0][1]):raise RuntimeError('Incomplete/duplicate export')
    parts=[]
    for i,(index,total,data) in enumerate(chunks):
        if int(index)!=i or int(total)!=len(chunks):raise RuntimeError('Unordered chunk')
        p=base64.b64decode(data,validate=True)
        if not 0<len(p)<=1800:raise RuntimeError('Chunk length rejected')
        parts.append(p)
    raw=b''.join(parts);import hashlib
    digest=hashlib.sha256(raw).hexdigest()
    if digest!=hashes[0]:raise RuntimeError('Raw SHA mismatch')
    r=json.loads(raw);validate(r)
    if r['gate_return_code']!=int(codes[0]):raise RuntimeError('Saved rc differs')
    done=re.findall(r'M352_DONE gate_rc=(\d+) export_rc=(\d+)',log)
    if done and (len(done)!=1 or done[0]!=(codes[0],'0')):raise RuntimeError('Original/export rc differs')
    return digest,raw,r


def selftest():
    import hashlib
    def export(r):
        raw=w.encoded(r);chunks=[raw[i:i+1800] for i in range(0,len(raw),1800)]
        return 'M352_RESULT_SHA256='+hashlib.sha256(raw).hexdigest()+'\nM352_SAVED_GATE_RC='+str(r['gate_return_code'])+'\n'+''.join('M352_RESULT_CHUNK='+str(i)+'/'+str(len(chunks))+':'+base64.b64encode(c).decode('ascii')+'\n' for i,c in enumerate(chunks))+'M352_DONE gate_rc=1 export_rc=0\n'
    fail=dict(build_id='0x4D395832',gate_level='load-only-memory-diagnostic',prior_board_sha256=PRIOR,gate_return_code=1,
              status='FAIL_LOAD_ONLY_PS_SLOT_CAPACITY',errors=['injected \u4e2d\u6587 capacity failure'*1000],blocked_inference_attempts=[],memory_capacity_proven=False)
    for k in ('numerical_pass','performance_pass','formal_promotion_allowed','worker_started','model_forward_calls','fpga_transactions','serving_after_vision_capacity_proven'):fail[k]=False
    assert decode(export(fail))[2]==fail
    bads=[export(fail).replace('M352_RESULT_CHUNK=1/','M352_RESULT_CHUNK=0/'),export(fail).replace('M352_SAVED_GATE_RC=1','M352_SAVED_GATE_RC=0'),export(fail).replace('export_rc=0','export_rc=1'),export(fail)+'M352_RESULT_SHA256='+'0'*64,export(dict(fail,performance_pass=True)),export(dict(fail,worker_started=True)),export(dict(fail,memory_capacity_proven=True))]
    for b in bads:
        try:decode(b)
        except (RuntimeError,ValueError):pass
        else:raise AssertionError('Invalid evidence accepted')
    return len(bads)


def prepare():
    if PKG.exists() or PREP.exists():raise RuntimeError('Immutable preparation exists')
    recovery={}
    for n in ('CURRENT_STATE.md','docsMILESTONES.md','DEPLOYMENT_OPERATION_MISTAKES_REVIEW.md','deployment/mage_vl4b/BOARD_GATE_RESULT.json'):
        p=ROOT/n;t=p.read_text(encoding='utf-8-sig');recovery[n]=dict(bytes=p.stat().st_size,lines=len(t.splitlines()),sha256=w.sha(p))
    b=json.loads((ROOT/'deployment/mage_vl4b/BOARD_GATE_RESULT.json').read_text(encoding='utf-8'))
    prior=ROOT/b['latest_m351_ps_component_board']['result']
    assert w.sha(prior)==PRIOR and b['latest_m351_ps_component_board']['sha256']==PRIOR
    assert all(PRIOR in (ROOT/n).read_text(encoding='utf-8-sig') for n in ('CURRENT_STATE.md','docsMILESTONES.md'))
    previous=BASE/'candidates/M346-load-memory-01'
    old_manifest=json.loads((previous/'PACKAGE_MANIFEST.json').read_text(encoding='utf-8'))
    for row in old_manifest['files']:assert w.sha(previous/row['path'])==row['sha256']
    audit_path=BASE/'runs/M348-loading-path-audit-01/RESULT.json'
    assert w.sha(audit_path)==AUDIT
    audited=json.loads(audit_path.read_text(encoding='utf-8'))['verified_source_files']
    assert len(audited)==49
    for row in audited:assert w.sha(ROOT/row['local_source'])==row['sha256']
    hardware=json.loads((previous/'HARDWARE_CLOSURE.json').read_text(encoding='utf-8'))
    assert len(hardware['checked'])==47 and not hardware['errors']
    source=(HERE/'m352_load_ps_slot_probe.py').read_text(encoding='utf-8');tree=ast.parse(source,feature_version=(3,10))
    forbidden={'stream','prefill','decode','forward','_execute','_launch_once','_launch_prepacked','_stage','language_family_many','lm_head','transfer','glibc_trim','collect','posix_fadvise','madvise'}
    bad=[n.func.attr for n in ast.walk(tree) if isinstance(n,ast.Call) and isinstance(n.func,ast.Attribute) and n.func.attr in forbidden]
    assert not bad,bad
    # Test the exact guard function without importing PYNQ or constructing runtime.
    ns={};fn=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='forbid')
    exec(ast.get_source_segment(source,fn),ns);blocked=[]
    guard_names=['_execute','_launch_once','_launch_prepacked','_stage','language_family_many','language_family','lm_head','engine.stream','vision.__call__','vision.tower.forward','language.prefill','language.decode','language._family']
    for name in guard_names:
        try:ns['forbid'](name,blocked)()
        except RuntimeError:pass
        else:raise AssertionError('Guard bypass')
    assert blocked==guard_names
    for name in ('ps_slot_capacity.py','m352_export_result.py'):ast.parse((HERE/name).read_text(encoding='utf-8'),feature_version=(3,10))
    tests=subprocess.run([sys.executable,'-B',str(HERE/'test_ps_slot_capacity.py')],capture_output=True,text=True,encoding='utf-8')
    assert tests.returncode==0 and 'Ran 6 tests' in tests.stderr,tests.stderr
    negatives=selftest()
    control=subprocess.run([r'C:\Users\30429\.cache\codex-runtimes\codex-primary-runtime\dependencies\native\powershell\pwsh.exe','-NoProfile','-File',str(HERE/'m352_control.ps1'),'-Mode','SelfTest'],capture_output=True,text=True,encoding='utf-8')
    assert control.returncode==0,control.stderr
    names=('m341_build_id_gate.py','measurement.py','board_safety.py','m120_board_common.py','m120_board_env_preflight.py','HARDWARE_CLOSURE.json','frozen_video_identity.py','SOURCE_CLOSURE.json','memory_lifecycle.py')
    files={n:(previous/n).read_bytes() for n in names}
    files.update({n:(HERE/n).read_bytes() for n in ('ps_slot_capacity.py','m352_load_ps_slot_probe.py','m352_export_result.py')})
    files['M351_BOARD_PREREQUISITE.json']=prior.read_bytes()
    files['M348_SOURCE_IDENTITIES.json']=w.encoded(dict(audit_raw_sha256=AUDIT,files=[{k:r[k] for k in ('path','bytes','sha256')} for r in audited]))
    files['run_m352_load_slot.sh']='\n'.join(['#!/usr/bin/env bash','set -euo pipefail','cd "$(dirname "${BASH_SOURCE[0]}")"','manifest_sha=${1:?exact manifest SHA required}',
        '[[ "${2:-}" == "--enable-load-only" ]] || { echo M352_DISABLED_BY_DEFAULT; exit 2; }',
        "printf '%s  PACKAGE_MANIFEST.json\\n' \"$manifest_sha\" | sha256sum -c -",'sha256sum -c SHA256SUMS','sudo -n true',
        '[[ ! -e /home/ubuntu/m352_load_memory_evidence_01 ]] || { echo M352_RESULT_EXISTS_COLLECT_ONLY; exit 2; }','set +e',
        'sudo -n env XILINX_XRT=/usr TMPDIR=/dev/shm PATH=/usr/local/share/pynq-venv/bin:/usr/local/bin:/usr/bin:/bin PYTHONDONTWRITEBYTECODE=1 TRANSFORMERS_OFFLINE=1 HF_HUB_OFFLINE=1 /usr/local/share/pynq-venv/bin/python3 -B ./m352_load_ps_slot_probe.py "$manifest_sha" --enable-load-only',
        'gate_rc=$?','sudo -n /usr/local/share/pynq-venv/bin/python3 -B ./m352_export_result.py','export_rc=$?','set -e',
        "printf 'M352_DONE gate_rc=%s export_rc=%s\\n' \"$gate_rc\" \"$export_rc\"",'if [[ "$gate_rc" -ne 0 ]]; then exit "$gate_rc"; fi','exit "$export_rc"','']).encode('utf-8')
    PKG.mkdir(parents=True);PREP.mkdir(parents=True)
    for n,raw in files.items():w.atomic(PKG/n,raw)
    rows=[dict(path=n,bytes=len(raw),sha256=w.sha(PKG/n)) for n,raw in sorted(files.items())]
    w.atomic(PKG/'SHA256SUMS',''.join(r['sha256']+'  '+r['path']+'\n' for r in rows).encode('ascii'))
    rows.append(dict(path='SHA256SUMS',bytes=(PKG/'SHA256SUMS').stat().st_size,sha256=w.sha(PKG/'SHA256SUMS')))
    w.atomic(PKG/'PACKAGE_MANIFEST.json',w.encoded(dict(schema='m352-complete-runtime-ps-slot-load-only-v1',files=rows,file_count=len(rows),total_bytes=sum(r['bytes'] for r in rows))))
    assert {p.name for p in PKG.iterdir()}=={r['path'] for r in rows}|{'PACKAGE_MANIFEST.json'}
    w.atomic(PREP/'TEST_OUTPUT.txt',(tests.stdout+tests.stderr).encode('utf-8'));w.atomic(PREP/'CONTROL_OUTPUT.txt',(control.stdout+control.stderr).encode('utf-8'))
    r=dict(status='PASS_OFFLINE_LOAD_PS_SLOT_PREPARATION',build_id='0x4D395832',recovery_read=recovery,prior_raw_sha256=PRIOR,
        evidence_level='L0_PACKAGE_AND_GUARDS_ONLY',board_run=False,model_forward_calls=0,fpga_transactions=0,
        memory_capacity_proven=False,numerical_pass=False,performance_pass=False,formal_promotion_allowed=False,
        helper_checks=6,collector_negative_checks=negatives,blocked_entrypoints=guard_names,python310_syntax=True,controller_failure_collect_selftest=True,
        source_files_same_sha=49,hardware_evidence_same_sha_items=47,unchanged_m346_package_sha256=w.sha(previous/'PACKAGE_MANIFEST.json'),
        manifest_sha256=w.sha(PKG/'PACKAGE_MANIFEST.json'),package_files=len(rows),package_bytes=sum(r['bytes'] for r in rows),
        ps_slot_bytes=27852800,cma_reserve_bytes=67108864,ps_reserve_bytes=67108864,extra_pynq_allocation_calls=0,
        capacity_scope='Actual complete runtime + touched PS slot only; after-vision capacity and video numerical/performance remain unproven',
        rejected_attempts=['Recovery read stdout default GBK rejected Unicode output; no board access. Explicit UTF-8 file reads retained; avoid locale-dependent stdout in new scripts.'],
        next_step='Only one COM3 load-only diagnostic after explicit Run, same-terminal sudo, manifest-first 900B upload, bash-n and fixed environment; collect saved bytes on failure, no full baseline')
    w.atomic(PREP/'RESULT.json',w.encoded(r),immutable=True);digest=w.sha(PREP/'RESULT.json')
    note=('## M352 完整runtime＋普通PS slot容量门禁包准备通过（2026-10-01）\n\n'
        '稳定Build0x4D395832；复用49份冻结源码同SHA、47项同SHA稳定硬件证据和原M346对象加载路径，13个推理/事务入口封锁。'
        f'6项容量/最大触页/失败保留检查、{negatives}项回收负例、控制故意失败自测与Python3.10语法通过。'
        f'白名单{len(rows)}载荷/{r["package_bytes"]}B，manifest `{r["manifest_sha256"]}`。'
        '规划实际完整runtime保留＋26.5625MiB普通PS bytearray每页触写读回；分配前保留slot外64MiB普通可用内存、前后64MiB CMA，0额外PYNQ调用，禁止GC/trim/forward/预读worker/PL事务。'
        '原7块DMA逐次安全释放检查及地址/字节回收计数；DMASR0仅从未提交生命周期，不是已完成idle。默认关闭、600s诊断预算，超时/异常活动保留过程与缓冲不kill。'
        f'证据 `{(PREP/"RESULT.json").relative_to(ROOT).as_posix()}` SHA `{digest}`。'
        '仅L0离线准备，未上传/执行/加载Overlay，无真实容量、视频数值/性能或晋级。下一步一次同COM3授权、900B分块完整SHA、bash-n及固定环境后只加载容量诊断，失败只回收；不自动启动视频。原90.5625MiB双bank门槛、服务/稳定源/回滚/boot/DTB/CMA保持。\n\n')
    w.sync('latest_m352_load_ps_slot_preparation',dict(status=r['status'],result=(PREP/'RESULT.json').relative_to(ROOT).as_posix(),sha256=digest,manifest_sha256=r['manifest_sha256'],board_run=False,memory_capacity_proven=False,performance_pass=False),note)
    w.atomic(PREP/'REPORT.md',('# M352 容量门禁准备\n\n'+note).encode('utf-8'))
    print(json.dumps(dict(status=r['status'],sha256=digest,manifest_sha256=r['manifest_sha256'],files=len(rows),bytes=r['package_bytes'])))


def collect(logpath):
    digest,raw,r=decode((ROOT/logpath).read_text(encoding='utf-8-sig'))
    if r['manifest_sha256']!=w.sha(PKG/'PACKAGE_MANIFEST.json'):raise RuntimeError('Package mismatch')
    w.atomic(RUN/'BOARD_RESULT.json',raw,immutable=True)
    note=('## M352 板端只加载PS slot容量结果 '+r['status']+'（2026-10-01）\n\n'
          f'稳定Build0x4D395832；原始证据 `{(RUN/"BOARD_RESULT.json").relative_to(ROOT).as_posix()}` SHA `{digest}`。'
          f'原rc{r["gate_return_code"]}，错误 `{json.dumps(r["errors"],ensure_ascii=False)}`。'
          '仅完整runtime保留＋普通PSslot只加载容量观察，0模型forward/预读worker/FPGA事务；没有视觉后容量/视频数值/性能或晋级。失败不得重跑完整模型，先独立裁决并同步；保持稳定源/服务/回滚/boot/DTB/CMA。\n\n')
    w.sync('latest_m352_load_ps_slot_board',dict(status=r['status'],result=(RUN/'BOARD_RESULT.json').relative_to(ROOT).as_posix(),sha256=digest,
           load_only_capacity_pass=r['memory_capacity_proven'],serving_after_vision_capacity_proven=False,numerical_pass=False,performance_pass=False,unsafe_buffers_retained=r['unsafe_buffers_retained']),note)
    w.atomic(RUN/'REPORT.md',('# M352 板端只加载容量\n\n'+note).encode('utf-8'))
    print(json.dumps(dict(status='M352_RESULT_SYNCHRONIZED',raw_sha256=digest,board_status=r['status'])))

if __name__=='__main__':
    if sys.argv[1:]==['prepare']:prepare()
    elif len(sys.argv)==3 and sys.argv[1]=='collect':collect(sys.argv[2])
    else:raise SystemExit('prepare | collect logpath')
