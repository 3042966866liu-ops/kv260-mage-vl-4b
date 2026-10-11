"""Offline freeze or exact-byte collection, never connects to the board."""
import ast
import base64
import hashlib
import importlib.util
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
PKG=BASE/'candidates/M347-asset-memory-01'
PRIOR='cc04ea32daba54878a4ac0f63a7cd990db36e67d745c1e696adb806fd60e086a'
PREP=BASE/'runs/M347-asset-memory-preparation-01'
RUN=BASE/'runs/M347-asset-memory-board-01'


def sha(path): return hashlib.sha256(path.read_bytes()).hexdigest()


def atomic(path, data):
    path.parent.mkdir(parents=True,exist_ok=True); part=path.with_name(path.name+'.m347-part')
    with part.open('wb') as f: f.write(data); f.flush(); os.fsync(f.fileno())
    os.replace(part,path)


def decode(log):
    hashes=re.findall(r'M347_RESULT_SHA256=([0-9a-f]{64})',log)
    chunks=re.findall(r'M347_RESULT_CHUNK=(\d+)/(\d+):([A-Za-z0-9+/=]+)',log)
    if len(hashes)!=1 or not chunks or len(chunks)!=int(chunks[0][1]): raise RuntimeError('Missing/duplicate hash or incomplete chunks')
    parts=[]
    for i,(idx,count,b) in enumerate(chunks):
        if int(idx)!=i or int(count)!=len(chunks): raise RuntimeError('Duplicate/unordered chunks')
        part=base64.b64decode(b,validate=True)
        if len(part)>1800: raise RuntimeError('Oversize chunk')
        parts.append(part)
    raw=b''.join(parts)
    if hashlib.sha256(raw).hexdigest()!=hashes[0]: raise RuntimeError('Exact raw SHA differs')
    r=json.loads(raw)
    if r['gate_level']!='asset-hash-memory-diagnostic' or r['prior_raw_sha256']!=PRIOR: raise RuntimeError('Wrong prerequisite/diagnostic')
    if r['status']=='PASS_ASSET_HASH_MEMORY_DIAGNOSTIC':
        if 'M347_ASSET_DONE gate_rc=0' not in log or r['errors'] or r['overlay_loaded'] or r['model_forward_calls'] or r['fpga_transactions']:
            raise RuntimeError('Invalid transaction/exit PASS')
        if any(r[k] for k in ('numerical_pass','performance_pass','formal_promotion_allowed','memory_capacity_proven','forbidden_imports','device_fds')):
            raise RuntimeError('Unsupported scope/pass')
        if len(r['files'])!=r['planned_files'] or not r['boot_unchanged'] or not r['cmdline_unchanged']:
            raise RuntimeError('Incomplete identities')
        for i,item in enumerate(r['files']):
            if item['index']!=i or item['actual_sha256']!=item['expected_sha256']: raise RuntimeError('Invalid asset hash/order')
    return hashes[0],raw,r


def self_test():
    r=dict(status='PASS_ASSET_HASH_MEMORY_DIAGNOSTIC',gate_level='asset-hash-memory-diagnostic',prior_raw_sha256=PRIOR,
           errors=[],overlay_loaded=False,model_forward_calls=0,fpga_transactions=0,numerical_pass=False,performance_pass=False,
           formal_promotion_allowed=False,memory_capacity_proven=False,forbidden_imports=[],device_fds=[],planned_files=1,
           files=[dict(index=0,actual_sha256='a'*64,expected_sha256='a'*64)],boot_unchanged=True,cmdline_unchanged=True,chinese='逐资产诊断'*800)
    def encode(value):
        raw=json.dumps(value,ensure_ascii=False).encode('utf-8'); chunks=[raw[i:i+1800] for i in range(0,len(raw),1800)]
        return raw,'M347_RESULT_SHA256='+hashlib.sha256(raw).hexdigest()+'\n'+''.join('M347_RESULT_CHUNK='+str(i)+'/'+str(len(chunks))+':'+base64.b64encode(b).decode()+'\n' for i,b in enumerate(chunks))+'M347_ASSET_DONE gate_rc=0\n'
    raw,log=encode(r); assert decode(log)[1]==raw
    invalid=[log.replace('gate_rc=0','gate_rc=1'),log.replace('M347_RESULT_CHUNK=1/','M347_RESULT_CHUNK=0/'),log+'M347_RESULT_SHA256='+'b'*64]
    for key,val in [('overlay_loaded',True),('model_forward_calls',1),('performance_pass',True),('planned_files',2),('device_fds',['/dev/mem'])]:
        invalid.append(encode(dict(r,**{key:val}))[1])
    bad=json.loads(json.dumps(r)); bad['files'][0]['expected_sha256']='b'*64; invalid.append(encode(bad)[1])
    for log in invalid:
        try: decode(log)
        except RuntimeError: pass
        else: raise AssertionError('Invalid evidence accepted')
    print('M347_COLLECTOR_SELF_TEST_PASS UTF8/hash/chunks/exit/identity/inference/scope')


def prepare():
    if PKG.exists() or PREP.exists(): raise RuntimeError('Immutable preparation exists')
    recovery={}
    for n in ('CURRENT_STATE.md','docsMILESTONES.md','DEPLOYMENT_OPERATION_MISTAKES_REVIEW.md','deployment/mage_vl4b/BOARD_GATE_RESULT.json'):
        b=(ROOT/n).read_bytes(); full=b.decode('utf-8-sig'); recovery[n]=dict(bytes=len(b),lines=len(full.splitlines()),sha256=hashlib.sha256(b).hexdigest())
    board=json.loads((ROOT/'deployment/mage_vl4b/BOARD_GATE_RESULT.json').read_text(encoding='utf-8'))
    prior=BASE/'runs/M346-load-memory-board-01/BOARD_RESULT.json'
    assert sha(prior)==PRIOR and board['latest_m346_load_memory']['sha256']==PRIOR
    assert all(PRIOR in (ROOT/n).read_text(encoding='utf-8') for n in ('CURRENT_STATE.md','docsMILESTONES.md'))
    interpreted=BASE/'runs/M346-load-memory-board-01/INTERPRETATION.json'
    assert sha(interpreted)=='980525283b4b790c994604682f6b6f17bfc848ac2557d8c0229b2edc4fec9ea5'
    stage=ROOT/'release_staging/kv260-mage-vl-4b-prebuilt-install-20260926-v7'
    source=stage/'scripts/preflight.py'; config=stage/'configs/deployment.example.json'
    assert sha(source)=='6d269adf431e8e505684f4d51b23e65112a7f5a9069561b1bf7de0d013f376fd'
    probe_source=(HERE/'m347_asset_memory_probe.py').read_text(encoding='utf-8'); tree=ast.parse(probe_source)
    namespace={'ast':ast}
    order_fn=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='original_order')
    exec(compile(ast.Module(body=[order_fn],type_ignores=[]),'m347-original-order','exec'),namespace)
    order=namespace['original_order'](source.read_text(encoding='utf-8'))
    spec=importlib.util.spec_from_file_location('m347_local_original_preflight',source)
    preflight=importlib.util.module_from_spec(spec); spec.loader.exec_module(preflight)
    cfg=json.loads(config.read_text(encoding='utf-8')); paths=preflight.required_paths(cfg)
    files=[dict(name=n,path=p.relative_to(stage).as_posix(),sha256=h) for n,h in order for p in (paths[n],)]
    assert len(files)==len({f['name'] for f in files}) and len(files)>30
    # Actual inspect call sequence with only asset I/O mocked: all original checks retained.
    with_original_hashes={str(paths[n]):h for n,h in order if h is not None}
    ready=json.loads(paths['candidate_ready'].read_text(encoding='utf-8'))
    with_original_hashes[str(paths['candidate_manifest'])]=ready['package_manifest_sha256']
    seen=[]
    def digest_mock(p): seen.append(str(p)); return with_original_hashes[str(p)]
    preflight.digest=digest_mock
    # All required installed assets must be present for this local call-sequence test.
    # Missing external assets are represented only by is_file override, never actual hashes.
    original_is_file=Path.is_file
    try:
        Path.is_file=lambda p: True if p in paths.values() else original_is_file(p)
        inspected=preflight.inspect(cfg,port_check=False)
    finally: Path.is_file=original_is_file
    assert inspected['status']=='READY_FOR_BOARD_PREFLIGHT' and seen==[str(paths[n]) for n,h in order]
    forbidden={'pynq','torch','board_runtime','video_server','subprocess'}
    imports=[(n.module or '').split('.')[0] for n in ast.walk(tree) if isinstance(n,ast.ImportFrom)]
    imports += [a.name.split('.')[0] for n in ast.walk(tree) if isinstance(n,ast.Import) for a in n.names]
    assert not forbidden.intersection(imports)
    calls={n.func.attr for n in ast.walk(tree) if isinstance(n,ast.Call) and isinstance(n.func,ast.Attribute)}
    assert not calls.intersection({'Overlay','allocate','forward','prefill','stream','transfer','malloc_trim','posix_fadvise','madvise'})
    assert sha(HERE/'memory_lifecycle.py')=='939fa2ca7cc1e438dd9b770b2aebab6424a69270c5ce605a72a27806ab125cc0'
    self_test()
    pwsh=r'C:\Users\30429\.cache\codex-runtimes\codex-primary-runtime\dependencies\native\powershell\pwsh.exe'
    check=subprocess.run([pwsh,'-NoProfile','-File',str(HERE/'m347_control.ps1'),'-Mode','SelfTest'],capture_output=True,text=True,encoding='utf-8')
    assert check.returncode==0,check.stdout+check.stderr
    PKG.mkdir(parents=True); PREP.mkdir(parents=True)
    plan=dict(schema='m347-original-asset-plan-v1',source_sha256=sha(source),config_sha256=sha(config),candidate_ready_sha256=sha(paths['candidate_ready']),
              prior_raw_sha256=PRIOR,files=files,read_algorithm='Unchanged original digest: 4MiB buffered reads, original inspect order')
    atomic(PKG/'ASSET_PLAN.json',(json.dumps(plan,indent=2)+'\n').encode('utf-8'))
    for name in ('m347_asset_memory_probe.py','memory_lifecycle.py'): shutil.copyfile(HERE/name,PKG/name)
    runner='''#!/usr/bin/env bash
set -euo pipefail
package_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$package_dir"
manifest_sha=${1:?manifest SHA required}
printf '%s  PACKAGE_MANIFEST.json\\n' "$manifest_sha" | sha256sum -c -
sha256sum -c SHA256SUMS
sudo -n true
set +e
sudo -n env PYTHONDONTWRITEBYTECODE=1 /usr/local/share/pynq-venv/bin/python3 -B "$package_dir/m347_asset_memory_probe.py" "$manifest_sha"
gate_rc=$?
set -e
printf 'M347_ASSET_DONE gate_rc=%s\\n' "$gate_rc"
exit "$gate_rc"
'''
    atomic(PKG/'run_m347_asset_memory.sh',runner.encode('utf-8'))
    items=[dict(path=p.name,bytes=p.stat().st_size,sha256=sha(p)) for p in sorted(PKG.iterdir())]
    atomic(PKG/'SHA256SUMS',''.join(i['sha256']+'  '+i['path']+'\n' for i in items).encode('utf-8'))
    items.append(dict(path='SHA256SUMS',bytes=(PKG/'SHA256SUMS').stat().st_size,sha256=sha(PKG/'SHA256SUMS')))
    manifest=dict(schema='m347-no-overlay-asset-memory-v1',files=items,file_count=len(items),total_bytes=sum(i['bytes'] for i in items),hardware_changed=False)
    atomic(PKG/'PACKAGE_MANIFEST.json',(json.dumps(manifest,indent=2)+'\n').encode('utf-8'))
    for n in recovery: shutil.copyfile(ROOT/n,PREP/(Path(n).name+'.before'))
    prep=dict(status='PASS_OFFLINE_ASSET_MEMORY_PREPARATION',evidence_level='L0',board_run=False,
              model_forward=False,overlay_loaded=False,numerical_pass=False,performance_pass=False,
              recovery_read=recovery,files=len(items),bytes=manifest['total_bytes'],asset_hash_calls=len(files),manifest_sha256=sha(PKG/'PACKAGE_MANIFEST.json'),
              checks=dict(original_inspect_mocked_io_order=True,original_source_sha=True,forbidden_imports=[],forbidden_device_or_cache_calls=[],
                          collector_negative_checks=9,controller_self_test=check.stdout.strip()),rejected_attempts=[])
    atomic(PREP/'RESULT.json',(json.dumps(prep,indent=2)+'\n').encode('utf-8')); print(json.dumps(prep))


def collect():
    digest,raw,r=decode((ROOT/'tmp/m347/asset_memory_uart.log').read_text(encoding='utf-8-sig'))
    if r['status']=='PASS_ASSET_HASH_MEMORY_DIAGNOSTIC':
        plan=json.loads((PKG/'ASSET_PLAN.json').read_text(encoding='utf-8'))
        assert r['manifest_sha256']==sha(PKG/'PACKAGE_MANIFEST.json')
        assert [{k:x[k] for k in ('name','path','sha256')} for x in r['files']]==plan['files']
    path=RUN/'BOARD_RESULT.json'; RUN.mkdir(parents=True,exist_ok=True)
    if path.exists() and path.read_bytes()!=raw: raise RuntimeError('Different immutable raw result exists')
    atomic(path,raw)
    for n in ('CURRENT_STATE.md','docsMILESTONES.md','deployment/mage_vl4b/BOARD_GATE_RESULT.json'):
        backup=RUN/(Path(n).name+'.before')
        if not backup.exists(): backup.write_bytes((ROOT/n).read_bytes())
    board_path=ROOT/'deployment/mage_vl4b/BOARD_GATE_RESULT.json'; board=json.loads(board_path.read_text(encoding='utf-8'))
    drops=sorted(r['files'],key=lambda item:item['cma_delta_bytes'])
    summary=dict(status=r['status'],sha256=digest,files=len(r['files']),errors=r['errors'],largest_cma_drops=[{k:x[k] for k in ('name','path','cma_delta_bytes','cached_delta_bytes','physical_read_bytes_delta')} for x in drops[:6]],
                 numerical_pass=False,performance_pass=False,formal_promotion_allowed=False,memory_capacity_proven=False,next_step=r['next_step'])
    board['latest_m347_asset_memory']=dict(**summary,build_id='0x4D395832',result=path.relative_to(ROOT).as_posix(),evidence_level='BOARD_PS_ONLY_ASSET_MEMORY_DIAGNOSTIC')
    atomic(board_path,(json.dumps(board,ensure_ascii=False,indent=2)+'\n').encode('utf-8'))
    atomic(RUN/'SUMMARY.json',(json.dumps(summary,indent=2)+'\n').encode('utf-8'))
    note=('## M347 逐资产哈希内存诊断 '+r['status']+'（2026-10-01）\n\n'
          '稳定Build `0x4D395832`；保留原preflight哈希算法与顺序，逐文件观测CMA/RSS/Cached和进程实际读取计数。'
          '无Overlay、模型forward或FPGA事务，缓存自然保留；不是冷启动或完整运行时容量证明。'
          '结果 `'+path.relative_to(ROOT).as_posix()+'` SHA `'+digest+'`；实际完成'+str(len(r['files']))+'次文件哈希。'
          '最大CMA下降记录 `'+json.dumps(summary['largest_cma_drops'],ensure_ascii=False)+'`。'
          '错误 `'+json.dumps(r['errors'],ensure_ascii=False)+'`。90.5625MiB门槛保持，双bank候选仍暂停，无视频数值/性能或晋级。'
          '稳定源/服务/回滚/boot/DTB/CMA配置未修改；无drop_caches、GC、trim、缓存建议或硬件门禁重跑。'
          '下一步 '+r['next_step']+'。\n\n')
    for n in ('CURRENT_STATE.md','docsMILESTONES.md'):
        p=ROOT/n; text=p.read_text(encoding='utf-8')
        if digest not in text:
            heading,rest=text.split('\n',1); atomic(p,(heading+'\n\n'+note+rest.lstrip('\n')).encode('utf-8'))
    table='| 资产（原顺序） | 大小 MiB | CMA变化 MiB | 文件缓存变化 MiB | 实际读取 MiB |\n| --- | ---: | ---: | ---: | ---: |\n'
    for x in r['files']:
        table+=f"| {x['index']} {x['name']} | {x['identity']['bytes']/1048576:.3f} | {x['cma_delta_bytes']/1048576:.3f} | {x['cached_delta_bytes']/1048576:.3f} | {x['physical_read_bytes_delta']/1048576:.3f} |\n"
    report='# M347 逐资产读取内存诊断\n\n'+note+table+'\n仅关联观测；系统CMA变化包含其他进程活动和自然回收，不能单凭相关变化证明页归属或碎片根因。\n'
    atomic(RUN/'REPORT.md',report.encode('utf-8'))
    assert all(digest in (ROOT/n).read_text(encoding='utf-8') for n in ('CURRENT_STATE.md','docsMILESTONES.md'))
    assert json.loads(board_path.read_text(encoding='utf-8'))['latest_m347_asset_memory']['sha256']==digest
    print(json.dumps(summary)); print('M347_THREE_RECORDS_SYNCHRONIZED')


if __name__=='__main__':
    {'prepare':prepare,'collect':collect,'self-test':self_test}[sys.argv[1]]()
