"""Local preparation/collection only; never connects to a board."""
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
sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
BASE = ROOT/'deployment/mage_vl4b/optimization_v1'
PKG = BASE/'candidates/M349-direct-hash-fixtures-01'
PREP = BASE/'runs/M349-direct-hash-preparation-01'
RUN = BASE/'runs/M349-direct-hash-board-01'
PRIOR = 'e4ed4b37bfa2122e0d9dd5998665767dfd47bf3e346cd312bbd7080d3437ff8e'
SIZES = (0,1,4095,4096,4097,(4<<20)-1,4<<20,(4<<20)+1)
NEXT = ('仅准备在COM3确认shell、同终端sudo、包SHA和bash-n通过后执行一次无Overlay小文件组件门禁；'
        '实际kernel/fs/statx对齐、自有fixture完整SHA、权限有效mincore及普通读取对照必须全部成立。'
        '缺失对齐字段/初始驻留/尾块或身份错误/无回退证据不充分即UNPROVEN拒绝，不猜测、不清缓存、不读真实模型资产。'
        '失败只回收同一结果并同步三记录，不重跑组件或模型；完整runtime90.5625MiB容量仍未通过，视频数值/性能未解锁。')


def sha(path): return hashlib.sha256(path.read_bytes()).hexdigest()
def encoded(obj): return (json.dumps(obj,ensure_ascii=False,indent=2)+'\n').encode('utf-8')


def atomic(path, raw, immutable=False):
    path.parent.mkdir(parents=True,exist_ok=True)
    if immutable and path.exists():
        if path.read_bytes()!=raw: raise RuntimeError('Immutable evidence differs')
        return
    part=path.with_name(path.name+'.m349-part')
    with part.open('wb') as f: f.write(raw); f.flush(); os.fsync(f.fileno())
    os.replace(part,path)


def expected_sha(size):
    page=bytes((i*73+19)%256 for i in range(256))*16; h=hashlib.sha256()
    for unused in range(size//len(page)): h.update(page)
    h.update(page[:size%len(page)])
    return h.hexdigest()


def decode(log):
    hashes=re.findall(r'M349_RESULT_SHA256=([0-9a-f]{64})',log)
    chunks=re.findall(r'M349_RESULT_CHUNK=(\d+)/(\d+):([A-Za-z0-9+/=]+)',log)
    codes=re.findall(r'M349_SAVED_GATE_RC=(\d+)',log)
    if len(hashes)!=1 or len(codes)!=1 or not chunks or len(chunks)!=int(chunks[0][1]): raise RuntimeError('Incomplete/duplicate hash/rc/chunks')
    pieces=[]
    for i,(index,total,data) in enumerate(chunks):
        if int(index)!=i or int(total)!=len(chunks): raise RuntimeError('Unordered/duplicate chunks')
        part=base64.b64decode(data,validate=True)
        if not part or len(part)>1800: raise RuntimeError('Invalid chunk size')
        pieces.append(part)
    raw=b''.join(pieces); digest=hashlib.sha256(raw).hexdigest()
    if digest!=hashes[0]: raise RuntimeError('Raw SHA differs')
    r=json.loads(raw); code=int(codes[0])
    if r['gate_level']!='small-direct-hash-fixtures-only' or r['prior_raw_sha256']!=PRIOR: raise RuntimeError('Wrong prerequisite/gate')
    if any(r[k] for k in ('overlay_loaded','model_forward_calls','fpga_transactions','real_assets_read','memory_capacity_proven','numerical_pass','performance_pass','formal_promotion_allowed','cache_eviction')): raise RuntimeError('Invalid scope/cache claim')
    if type(r['gate_return_code']) is not int or r['gate_return_code']!=code or code not in (0,1): raise RuntimeError('Saved rc differs')
    done=re.findall(r'M349_DONE gate_rc=(\d+) export_rc=(\d+)',log)
    if done and (len(done)!=1 or done[0]!=(str(code),'0')): raise RuntimeError('Original gate/export rc differs')
    if r['status']=='PASS_SMALL_DIRECT_HASH_COMPONENT_ONLY':
        if code or r['errors'] or not r['direct_mode_proven'] or len(r['fixtures'])!=8 or r['algorithm_checks']!=18: raise RuntimeError('Incomplete PASS')
        lc=r['lifecycle']
        if lc['live_aligned_buffers'] or lc['live_observation_maps'] or lc['remaining_fixture_fds']: raise RuntimeError('Lifecycle not closed')
        for i,(row,size) in enumerate(zip(r['fixtures'],SIZES)):
            if row['index']!=i or row['size']!=size or row['expected_sha256']!=expected_sha(size): raise RuntimeError('Fixture identity/expected SHA differs')
            h=row['hash']
            if len(row['created_identity'])!=9 or row['created_identity'][2]!=size: raise RuntimeError('Incomplete file identity')
            if h['sha256']!=row['expected_sha256'] or h['bytes_hashed']!=size or h['buffered_fallback'] or h['identity']!=row['created_identity']: raise RuntimeError('Full SHA/identity/fallback differs')
            if any(row[k]['resident'] or not row[k]['permission_valid'] for k in ('resident_before','resident_after')): raise RuntimeError('Residency proof invalid')
        c=r['residency_control']
        if c['before']['resident'] or not c['before']['permission_valid'] or not c['after']['permission_valid'] or not c['after']['resident'] or c['after']['resident']!=c['after']['pages']: raise RuntimeError('Positive residency control invalid')
        if r['elapsed_s']>60 or r['fixture_allocated_bytes']>16<<20: raise RuntimeError('Budget exceeded')
    elif r['status']=='FAIL_COMPONENT_UNPROVEN':
        if code!=1 or not r['errors'] or r['direct_mode_proven']: raise RuntimeError('Failed capability must remain rejected')
    else: raise RuntimeError('Unknown status')
    return digest,raw,r


def self_test():
    r=dict(status='FAIL_COMPONENT_UNPROVEN',gate_level='small-direct-hash-fixtures-only',prior_raw_sha256=PRIOR,
        gate_return_code=1,errors=['对齐信息不可用'*1000],direct_mode_proven=False,overlay_loaded=False,model_forward_calls=0,
        fpga_transactions=0,real_assets_read=False,memory_capacity_proven=False,numerical_pass=False,performance_pass=False,
        formal_promotion_allowed=False,cache_eviction=False)
    def export(value):
        raw=encoded(value); pieces=[raw[i:i+1800] for i in range(0,len(raw),1800)]
        log='M349_RESULT_SHA256='+hashlib.sha256(raw).hexdigest()+'\nM349_SAVED_GATE_RC='+str(value['gate_return_code'])+'\n'
        log+=''.join('M349_RESULT_CHUNK='+str(i)+'/'+str(len(pieces))+':'+base64.b64encode(p).decode('ascii')+'\n' for i,p in enumerate(pieces))
        return raw,log+'M349_DONE gate_rc='+str(value['gate_return_code'])+' export_rc=0\n'
    raw,log=export(r); assert decode(log)[1]==raw and decode(log[:log.index('M349_DONE')])[1]==raw
    good=dict(r,status='PASS_SMALL_DIRECT_HASH_COMPONENT_ONLY',gate_return_code=0,errors=[],direct_mode_proven=True,
        algorithm_checks=18,lifecycle=dict(live_aligned_buffers=0,live_observation_maps=0,remaining_fixture_fds=[]),
        elapsed_s=1,fixture_allocated_bytes=13<<20,fixtures=[],
        residency_control=dict(before=dict(resident=0,permission_valid=True),after=dict(resident=16,pages=16,permission_valid=True)))
    for i,size in enumerate(SIZES):
        ident=[1,i+1,size,3,4,0o100600,0,0,1]
        good['fixtures'].append(dict(index=i,size=size,expected_sha256=expected_sha(size),created_identity=ident,
            hash=dict(sha256=expected_sha(size),bytes_hashed=size,buffered_fallback=False,identity=ident),
            resident_before=dict(resident=0,permission_valid=True),resident_after=dict(resident=0,permission_valid=True)))
    good_raw,good_log=export(good); assert decode(good_log)[1]==good_raw
    invalid=[log.replace('M349_SAVED_GATE_RC=1','M349_SAVED_GATE_RC=0'),log.replace('M349_RESULT_CHUNK=1/','M349_RESULT_CHUNK=0/'),log+'M349_RESULT_SHA256='+'0'*64,log.replace('export_rc=0','export_rc=1')]
    for k,v in (('overlay_loaded',True),('real_assets_read',True),('performance_pass',True),('cache_eviction',True),('direct_mode_proven',True),('errors',[])):
        invalid.append(export(dict(r,**{k:v}))[1])
    for category in ('tail_sha','short_length','identity','residency','permission','control','lifecycle','deadline'):
        bad=json.loads(json.dumps(good))
        row=bad['fixtures'][-1]
        if category=='tail_sha': row['hash']['sha256']='0'*64
        elif category=='short_length': row['hash']['bytes_hashed']-=1
        elif category=='identity': row['hash']['identity'][1]+=1
        elif category=='residency': row['resident_after']['resident']=1
        elif category=='permission': row['resident_before']['permission_valid']=False
        elif category=='control': bad['residency_control']['after']['resident']=0
        elif category=='lifecycle': bad['lifecycle']['live_aligned_buffers']=1
        elif category=='deadline': bad['elapsed_s']=61
        invalid.append(export(bad)[1])
    for bad in invalid:
        try: decode(bad)
        except (RuntimeError,ValueError): pass
        else: raise AssertionError('Invalid result accepted')
    return len(invalid)


def sync(key,value,note):
    path=ROOT/'deployment/mage_vl4b/BOARD_GATE_RESULT.json'
    b=json.loads(path.read_text(encoding='utf-8')); b[key]=value; atomic(path,encoded(b))
    for name in ('CURRENT_STATE.md','docsMILESTONES.md'):
        p=ROOT/name; old=p.read_text(encoding='utf-8-sig')
        if value['sha256'] not in old:
            title,rest=old.split('\n',1); atomic(p,(title+'\n\n'+note+rest.lstrip('\n')).encode('utf-8'))
    assert json.loads(path.read_text(encoding='utf-8'))[key]['sha256']==value['sha256']
    assert all(value['sha256'] in (ROOT/n).read_text(encoding='utf-8') for n in ('CURRENT_STATE.md','docsMILESTONES.md'))


def prepare():
    if PKG.exists() or PREP.exists(): raise RuntimeError('Immutable preparation exists; inspect/recover only')
    recovery={}
    for name in ('CURRENT_STATE.md','DEPLOYMENT_OPERATION_MISTAKES_REVIEW.md','docsMILESTONES.md','deployment/mage_vl4b/BOARD_GATE_RESULT.json'):
        raw=(ROOT/name).read_bytes(); full=raw.decode('utf-8-sig')
        recovery[name]=dict(bytes=len(raw),lines=len(full.splitlines()),sha256=hashlib.sha256(raw).hexdigest())
    b=json.loads((ROOT/'deployment/mage_vl4b/BOARD_GATE_RESULT.json').read_text(encoding='utf-8'))
    assert b['latest_m348_loading_path_audit']['sha256']==PRIOR and sha(BASE/'runs/M348-loading-path-audit-01/RESULT.json')==PRIOR
    assert all(PRIOR in (ROOT/n).read_text(encoding='utf-8') for n in ('CURRENT_STATE.md','docsMILESTONES.md'))
    tested=subprocess.run([sys.executable,'-B',str(HERE/'test_direct_hash.py')],capture_output=True,text=True,encoding='utf-8')
    if tested.returncode or 'Ran 18 tests' not in tested.stderr: raise RuntimeError(tested.stderr)
    negatives=self_test()
    pwsh='C:/Users/30429/.cache/codex-runtimes/codex-primary-runtime/dependencies/native/powershell/pwsh.exe'
    tested_control=subprocess.run([pwsh,'-NoProfile','-File',str(HERE/'m349_control.ps1'),'-Mode','SelfTest'],capture_output=True,text=True,encoding='utf-8')
    if tested_control.returncode or 'M349_CONTROL_SELF_TEST_PASS' not in tested_control.stdout: raise RuntimeError(tested_control.stdout+tested_control.stderr)
    files=('direct_hash.py','test_direct_hash.py','m349_direct_hash_fixture_gate.py','m349_export_result.py')
    forbidden={'pynq','torch','board_runtime','video_server','m276_video_runtime'}
    for name in files:
        tree=ast.parse((HERE/name).read_text(encoding='utf-8'),filename=name,feature_version=(3,10))
        imports=[a.name.split('.')[0] for n in ast.walk(tree) if isinstance(n,ast.Import) for a in n.names]+[(n.module or '').split('.')[0] for n in ast.walk(tree) if isinstance(n,ast.ImportFrom)]
        calls={n.func.attr for n in ast.walk(tree) if isinstance(n,ast.Call) and isinstance(n.func,ast.Attribute)}
        if forbidden.intersection(imports) or calls.intersection({'Overlay','allocate','forward','prefill','posix_fadvise','madvise','malloc_trim'}): raise RuntimeError('Forbidden runtime/cache call')
    PKG.mkdir(parents=True); PREP.mkdir(parents=True)
    for name in files: shutil.copyfile(HERE/name,PKG/name)
    atomic(PKG/'M348_PREREQUISITE.json',encoded(dict(raw_sha256=PRIOR,evidence_level='L0_SOURCE_AUDIT_ONLY',original_asset_sha_checks_remain=35,real_assets_not_in_fixture_package=True)))
    runner='\n'.join(['#!/usr/bin/env bash','set -euo pipefail',
        'package_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"','cd "$package_dir"',
        'manifest_sha=${1:?manifest SHA required}','enable=${2:-}',
        'if [[ "$enable" != "--enable-fixture-gate" ]]; then printf "M349_DISABLED_BY_DEFAULT\\n"; exit 2; fi',
        "printf '%s  PACKAGE_MANIFEST.json\\n' \"$manifest_sha\" | sha256sum -c -",'sha256sum -c SHA256SUMS','sudo -n true','set +e',
        'sudo -n env PYTHONDONTWRITEBYTECODE=1 /usr/local/share/pynq-venv/bin/python3 -B "$package_dir/m349_direct_hash_fixture_gate.py" "$manifest_sha" --enable-fixture-gate',
        'gate_rc=$?','sudo -n env PYTHONDONTWRITEBYTECODE=1 /usr/local/share/pynq-venv/bin/python3 -B "$package_dir/m349_export_result.py"','export_rc=$?','set -e',
        "printf 'M349_DONE gate_rc=%s export_rc=%s\\n' \"$gate_rc\" \"$export_rc\"",'if [[ "$gate_rc" -ne 0 ]]; then exit "$gate_rc"; fi','exit "$export_rc"',''])
    atomic(PKG/'run_m349_fixture.sh',runner.encode('utf-8'))
    rows=[dict(path=p.name,bytes=p.stat().st_size,sha256=sha(p)) for p in sorted(PKG.iterdir())]
    atomic(PKG/'SHA256SUMS',''.join(r['sha256']+'  '+r['path']+'\n' for r in rows).encode('ascii'))
    rows.append(dict(path='SHA256SUMS',bytes=(PKG/'SHA256SUMS').stat().st_size,sha256=sha(PKG/'SHA256SUMS')))
    manifest=dict(schema='m349-opt-in-fixture-component-v1',files=rows,file_count=len(rows),total_bytes=sum(r['bytes'] for r in rows),board_run=False,model_assets_included=False,hardware_changed=False)
    atomic(PKG/'PACKAGE_MANIFEST.json',encoded(manifest))
    assert {p.name for p in PKG.iterdir()}=={r['path'] for r in rows}|{'PACKAGE_MANIFEST.json'}
    assert not list(PKG.rglob('__pycache__')) and not list(PKG.rglob('*.pyc'))
    atomic(PREP/'ALGORITHM_TESTS.txt',(tested.stdout+tested.stderr).encode('utf-8'))
    atomic(PREP/'CONTROL_TESTS.txt',(tested_control.stdout+tested_control.stderr).encode('utf-8'))
    r=dict(status='PASS_OFFLINE_DIRECT_HASH_COMPONENT_PREPARATION',evidence_level='L0_ALGORITHM_AND_PACKAGE_ONLY',build_id='0x4D395832',
        prior_raw_sha256=PRIOR,recovery_read=recovery,board_run=False,overlay_loaded=False,model_forward=False,real_assets_read=False,fpga_transactions=0,
        direct_mode_proven=False,memory_capacity_proven=False,numerical_pass=False,performance_pass=False,formal_promotion_allowed=False,
        component_default_disabled=True,algorithm_tests=18,collector_negative_checks=negatives,controller_failure_self_test=True,python310_syntax=True,
        package_files=len(rows),package_bytes=manifest['total_bytes'],manifest_sha256=sha(PKG/'PACKAGE_MANIFEST.json'),
        source_sha256={n:sha(HERE/n) for n in files},controller_sha256=sha(HERE/'m349_control.ps1'),workflow_sha256=sha(Path(__file__)),
        tested_scope='Windows algorithm and explicit fake API/lifecycle; not Linux/fs capability',
        linux_alignment_policy='STATX_DIOALIGN + MNT_ID required; missing/zero rejects without guessed fallback',
        rejected_attempts=['Local patch format error rejected before file edits; corrected locally, no package/board operation'],
        remaining_checks=['Actual board Python/API','Board bash-n','Kernel/fs/statx capability','Fresh nonresident fixtures','Complete tails/SHA + mincore positive control'],next_step=NEXT)
    raw=encoded(r); atomic(PREP/'RESULT.json',raw,immutable=True); digest=hashlib.sha256(raw).hexdigest()
    note=('## M349 只读哈希组件离线准备通过，尚未上板（2026-10-01）\n\n'
        '稳定Build `0x4D395832`；默认关闭的direct_hash.py已实现，18项算法/错误/尾块/身份/资源检查PASS，'
        f'{negatives}项收集负例、控制故意失败自测及Python3.10语法检查通过。'
        f'白名单小文件包{len(rows)}载荷/{manifest["total_bytes"]}B，manifest `{r["manifest_sha256"]}`。'
        '仅L0 Windows算法及明确fake API测试；实际kernel/fs、statx对齐、无buffered回退未证明，未上传/执行组件、未读真实资产。'
        'statx字段缺失或0直接UNPROVEN，不猜4096。90.5625MiB门槛/64MiB余量保持，双bank仍停视频CMA失败级，稳定源/服务/回滚/boot/DTB/CMA未改。'
        f'本地补丁格式拒绝已修正，无板端影响。证据 `{(PREP/"RESULT.json").relative_to(ROOT).as_posix()}` SHA `{digest}`。下一步：{NEXT}\n\n')
    sync('latest_m349_component_preparation',dict(status=r['status'],evidence_level=r['evidence_level'],result=(PREP/'RESULT.json').relative_to(ROOT).as_posix(),sha256=digest,manifest_sha256=r['manifest_sha256'],board_run=False,direct_mode_proven=False,performance_pass=False,next_step=NEXT),note)
    report='# M349 只读哈希组件准备\n\n'+note+'实现对齐缓冲、完整SHA、严格短读/尾块、有限EINTR、deadline、前后身份、默认关闭，无自动普通读回退。组件API仍返回direct_mode_proven=false，只有实际fixture/mincore对照才能证明本板支持。\n\n'
    report+='门禁fixture≤16MiB、预算60s，固定新目录和原结果不可重复执行；ftruncate尾块可能引入初始驻留，发生即UNPROVEN，不清缓存重试。\n\n'
    report+='[statx(2)](https://man7.org/linux/man-pages/man2/statx.2.html)明确DIOALIGN从Linux6.1起且依赖fs；[Linux UAPI](https://github.com/torvalds/linux/blob/master/include/uapi/linux/stat.h)用于核对ABI。尚未查本板内核。\n\n'
    report+='控制器SelfTest/Upload/Run/Collect均显式选择；Collect仅导出已有原字节，Run失败也收集并保留原rc。板端环境/API与bash-n尚未执行。\n'
    atomic(PREP/'REPORT.md',report.encode('utf-8'))
    print(json.dumps(dict(status='M349_PREPARATION_SYNCHRONIZED',sha256=digest,manifest_sha256=r['manifest_sha256'],files=len(rows),bytes=manifest['total_bytes'],board_run=False)))


def collect(log_path):
    digest,raw,r=decode((ROOT/log_path).read_text(encoding='utf-8-sig'))
    if r['manifest_sha256']!=sha(PKG/'PACKAGE_MANIFEST.json'): raise RuntimeError('Wrong package')
    atomic(RUN/'BOARD_RESULT.json',raw,immutable=True)
    note=('## M349 小文件组件结果 '+r['status']+'（2026-10-01）\n\n稳定Build `0x4D395832`；仅自有小文件，无Overlay/模型/真实资产/FPGA事务。'
        f'错误 `{json.dumps(r["errors"],ensure_ascii=False)}`。原始结果 `{(RUN/"BOARD_RESULT.json").relative_to(ROOT).as_posix()}` SHA `{digest}`。'
        '仅组件能力，不证明实际完整runtime容量/视频数值/性能/晋级，90.5625MiB门槛保持。失败只在组件级解释/回收；通过亦不自动解锁真实资产。\n\n')
    sync('latest_m349_component_board',dict(status=r['status'],sha256=digest,result=(RUN/'BOARD_RESULT.json').relative_to(ROOT).as_posix(),evidence_level='BOARD_PS_ONLY_COMPONENT',direct_mode_proven=r['direct_mode_proven'],real_assets_read=False,memory_capacity_proven=False,performance_pass=False,formal_promotion_allowed=False),note)
    atomic(RUN/'REPORT.md',('# M349 小文件组件结果\n\n'+note).encode('utf-8'))
    print(json.dumps(dict(status='M349_RESULT_SYNCHRONIZED',raw_sha256=digest,component_status=r['status'])))


if __name__=='__main__':
    if sys.argv[1:] == ['prepare']: prepare()
    elif sys.argv[1:] == ['selftest']: print('M349_COLLECTOR_SELF_TEST_PASS negatives='+str(self_test()))
    elif len(sys.argv)==3 and sys.argv[1]=='collect': collect(sys.argv[2])
    else: raise SystemExit('Usage: m349_workflow.py prepare | selftest | collect relative-log-path')
