"""Package and recover one read-only kernel metadata observation."""
import ast
import base64
import hashlib
import json
from pathlib import Path
import re
import shutil
import struct
import sys
import m351_workflow as w
import m364_cma_metadata as probe

PKG=w.BASE/'candidates/M364-cma-metadata-01'
PREP=w.BASE/'runs/M364-kernel-metadata-preparation-01'
RUN=w.BASE/'runs/M364-kernel-metadata-board-01'
SYSFS=bool(sys.argv[1:] and sys.argv[1].startswith('sysfs-'))
if SYSFS:
    PKG=w.BASE/'candidates/M364-cma-sysfs-01'
    PREP=w.BASE/'runs/M364-cma-sysfs-preparation-01'
    RUN=w.BASE/'runs/M364-cma-sysfs-board-01'
REMOTE='/home/ubuntu/m364_cma_sysfs_01' if SYSFS else '/home/ubuntu/m364_cma_metadata_01'
EVIDENCE='/home/ubuntu/m364_cma_sysfs_evidence_01' if SYSFS else '/home/ubuntu/m364_cma_metadata_evidence_01'
ENTRY='m364_sysfs_metadata.py' if SYSFS else 'm364_cma_metadata.py'
TAG='cma-sysfs' if SYSFS else 'kernel-metadata'

def decode(log):
    hashes=re.findall(r'M364_RESULT_SHA256=([0-9a-f]{64})',log)
    codes=re.findall(r'M364_SAVED_GATE_RC=([01])',log)
    chunks=re.findall(r'M364_RESULT_CHUNK=(\d+)/(\d+):([A-Za-z0-9+/=]+)',log)
    if len(hashes)!=1 or len(codes)!=1 or not chunks or len(chunks)!=int(chunks[0][1]):raise ValueError('Missing/duplicate evidence')
    parts=[]
    for i,(index,total,data) in enumerate(chunks):
        part=base64.b64decode(data,validate=True)
        if int(index)!=i or int(total)!=len(chunks) or not 0<len(part)<=900:raise ValueError('Chunk order/size differs')
        parts.append(part)
    raw=b''.join(parts);digest=hashlib.sha256(raw).hexdigest()
    if digest!=hashes[0]:raise ValueError('Raw SHA differs')
    r=json.loads(raw)
    if r['gate_return_code']!=int(codes[0]) or r['scope']!='read-only-kernel-metadata-no-runtime' or r['reserve_bytes']!=64<<20:raise ValueError('Scope/rc differs')
    for k in ('overlay_loads','model_forward_calls','fpga_transactions','real_asset_data_reads','cache_eviction','capacity_proven','file_page_ownership_proven'):
        if r[k]:raise ValueError('Scope widened')
    done=re.findall(r'M364_DONE gate_rc=(\d+) export_rc=(\d+)',log)
    if done and done!=[(codes[0],'0')]:raise ValueError('Export/original rc differs')
    return raw,r,digest

def selftest():
    assert probe.summarize(struct.pack('=QQQ',(1<<5),(1<<5)|(1<<12),(1<<10)))['flags_nonexclusive']['file_lru_candidate']==1
    assert probe.summarize(struct.pack('=Q',1<<23))['flags_nonexclusive']['OFFLINE']==1
    try:probe.summarize(b'x')
    except ValueError:pass
    else:raise AssertionError('Short word accepted')
    r=dict(gate_return_code=1,scope='read-only-kernel-metadata-no-runtime',reserve_bytes=64<<20)
    for k in ('overlay_loads','model_forward_calls','fpga_transactions','real_asset_data_reads','cache_eviction','capacity_proven','file_page_ownership_proven'):r[k]=False
    def log(r):
        b=w.encoded(r);parts=[b[i:i+900] for i in range(0,len(b),900)]
        return 'M364_RESULT_SHA256='+hashlib.sha256(b).hexdigest()+'\nM364_SAVED_GATE_RC='+str(r['gate_return_code'])+'\n'+''.join(f'M364_RESULT_CHUNK={i}/{len(parts)}:'+base64.b64encode(p).decode()+'\n' for i,p in enumerate(parts))+f'M364_DONE gate_rc={r["gate_return_code"]} export_rc=0\n'
    good=log(r);assert decode(good)[1]==r
    bad=[good.replace('export_rc=0','export_rc=1'),good+good,good.replace('CHUNK=0/','CHUNK=1/'),good.replace('SHA256=','SHA256=0'),log(dict(r,capacity_proven=True)),log(dict(r,reserve_bytes=1))]
    for value in bad:
        try:decode(value)
        except (ValueError,KeyError):pass
        else:raise AssertionError('Corrupted export accepted')
    tree=ast.parse((w.HERE/'m364_cma_metadata.py').read_text(encoding='utf-8'),feature_version=(3,10))
    imports={a.name.split('.')[0] for n in ast.walk(tree) if isinstance(n,ast.Import) for a in n.names}
    assert not imports.intersection({'pynq','torch','numpy','mmap','subprocess','ctypes'})
    return dict(summary_checks=3,collector_negative_checks=len(bad),python310_syntax=True,no_model_or_faulting_imports=True)

def prepare():
    if PKG.exists() or PREP.exists():raise RuntimeError('Immutable package exists')
    tests=selftest()
    prior=w.BASE/'runs/M364-reserve-and-cache-audit-01/RESULT.json';digest=w.sha(prior)
    for name in ('CURRENT_STATE.md','docsMILESTONES.md','deployment/mage_vl4b/BOARD_GATE_RESULT.json'):assert digest in (w.ROOT/name).read_text(encoding='utf-8-sig')
    PKG.mkdir(parents=True)
    shutil.copyfile(w.HERE/'m364_cma_metadata.py',PKG/'m364_cma_metadata.py')
    if SYSFS:
        ast.parse((w.HERE/ENTRY).read_text(encoding='utf-8'),feature_version=(3,10))
        shutil.copyfile(w.HERE/ENTRY,PKG/ENTRY)
    runner='\n'.join(['#!/usr/bin/env bash','set -euo pipefail','cd "$(dirname "${BASH_SOURCE[0]}")"','manifest_sha=${1:?exact SHA required}','mode=${2:?Run or Collect required}','[[ "$EUID" == 0 ]] || exit 2',
        '[[ "$mode" == Run || "$mode" == Collect ]] || exit 2',"printf '%s  PACKAGE_MANIFEST.json\\n' \"$manifest_sha\" | sha256sum -c -",'sha256sum -c SHA256SUMS',
        'if [[ "$mode" == Run ]]; then',' [[ "${M364_ENABLE_METADATA:-0}" == 1 ]] || exit 2',' [[ ! -e /home/ubuntu/m364_cma_metadata_evidence_01 ]] || { echo M364_COLLECT_ONLY; exit 2; }',' set +e',
        ' PYTHONDONTWRITEBYTECODE=1 /usr/local/share/pynq-venv/bin/python -B ./m364_cma_metadata.py Run "$manifest_sha"',' gate_rc=$?',' set -e','else',' gate_rc=0','fi','set +e',
        'PYTHONDONTWRITEBYTECODE=1 /usr/local/share/pynq-venv/bin/python -B ./m364_cma_metadata.py Collect','export_rc=$?','set -e',
        'if [[ "$mode" == Run ]]; then'," printf 'M364_DONE gate_rc=%s export_rc=%s\\n' \"$gate_rc\" \"$export_rc\"",'fi','[[ "$gate_rc" == 0 ]] || exit "$gate_rc"','exit "$export_rc"',''])
    if SYSFS:runner=runner.replace('/home/ubuntu/m364_cma_metadata_evidence_01',EVIDENCE).replace('./m364_cma_metadata.py','./'+ENTRY)
    w.atomic(PKG/'run_m364_metadata.sh',runner.encode())
    rows=[dict(path=p.name,bytes=p.stat().st_size,sha256=w.sha(p)) for p in sorted(PKG.iterdir())]
    w.atomic(PKG/'SHA256SUMS',''.join(x['sha256']+'  '+x['path']+'\n' for x in rows).encode('ascii'))
    rows.append(dict(path='SHA256SUMS',bytes=(PKG/'SHA256SUMS').stat().st_size,sha256=w.sha(PKG/'SHA256SUMS')))
    w.atomic(PKG/'PACKAGE_MANIFEST.json',w.encoded(dict(schema='m364-existing-kernel-metadata-v1',files=rows,file_count=len(rows),total_bytes=sum(x['bytes'] for x in rows))))
    r=dict(status='PASS_OFFLINE_READ_ONLY_METADATA_PREPARATION',tests=tests,manifest_sha256=w.sha(PKG/'PACKAGE_MANIFEST.json'),prior_audit_sha256=digest,files=len(rows),bytes=sum(x['bytes'] for x in rows),default_disabled=True,board_executed=False,capacity_proven=False)
    w.atomic(PREP/'RESULT.json',w.encoded(r),immutable=True);sha=w.sha(PREP/'RESULT.json')
    w.sync('latest_m364_'+TAG+'_preparation',dict(status=r['status'],result=(PREP/'RESULT.json').relative_to(w.ROOT).as_posix(),sha256=sha,manifest_sha256=r['manifest_sha256']),f'## M364 只读内核元数据包准备 {TAG}\n\n默认关闭，只有既有内核只读统计；sysfs后续包只读已存在CMA分配/释放计数。无资产数据读取/缺页/分配试验/Overlay/forward/FPGA/清缓存，64MiB保持。位分类/短读及回收负例、Python3.10核查通过，证据SHA `{sha}`。下一步COM3逐SHA/root bash-n后仅一次统计读取；无法获得PFN时记录不可证明，不修改内核接口。')
    print(json.dumps(r))

def collect(path):
    raw,r,digest=decode(Path(path).read_text(encoding='utf-8-sig'))
    assert r['manifest_sha256']==w.sha(PKG/'PACKAGE_MANIFEST.json')
    w.atomic(RUN/'BOARD_RESULT.json',raw,immutable=True)
    w.sync('latest_m364_'+TAG+'_board',dict(status=r['status'],result=(RUN/'BOARD_RESULT.json').relative_to(w.ROOT).as_posix(),sha256=digest,capacity_proven=False,file_page_ownership_proven=False),f'## M364 板端只读内核统计 {TAG}\n\n裁决{r["status"]}，原rc{r["gate_return_code"]}，CMA范围元数据可证={r.get("cma_range_metadata_proven",False)}。0资产数据读/Overlay/forward/FPGA，无清缓存/分配试验；64MiB保持。原字节SHA `{digest}`。当前快照不是运行时容量或原SHA事件页归属证明，下一步按实际接口与页类别裁决，不重跑模型。')
    print(json.dumps(dict(status='M364_RAW_SYNCHRONIZED',raw_sha256=digest,probe_status=r['status'],areas=r.get('areas'))))

def transfer(path):
    log=Path(path).read_text(encoding='utf-8-sig')
    manifest=json.loads((PKG/'PACKAGE_MANIFEST.json').read_text(encoding='utf-8'))
    expected={x['path']:x['sha256'] for x in manifest['files']}
    expected['PACKAGE_MANIFEST.json']=w.sha(PKG/'PACKAGE_MANIFEST.json')
    rows=re.findall(r'(?m)^\s*([0-9a-f]{64})  '+re.escape(REMOTE)+r'/([a-zA-Z0-9_.]+)\s*$',log)
    assert len(rows)==len(expected) and {name:digest for digest,name in rows}==expected
    syntax=(w.ROOT/('tmp/m364_sysfs/root_syntax.log' if SYSFS else 'tmp/m364/root_syntax.log')).read_text(encoding='utf-8-sig');assert '__M364_SYNTAX_RC_0__' in syntax
    r=dict(status='PASS_M364_METADATA_TRANSFER_ONLY',manifest_sha256=expected['PACKAGE_MANIFEST.json'],remote_files=len(expected),root_bash_n=True,overlay_loads=0,fpga_transactions=0)
    out=w.BASE/('runs/M364-'+TAG+'-transfer-01');w.atomic(out/'RESULT.json',w.encoded(r),immutable=True);digest=w.sha(out/'RESULT.json')
    w.sync('latest_m364_'+TAG+'_transfer',dict(status=r['status'],sha256=digest,result=(out/'RESULT.json').relative_to(w.ROOT).as_posix()),f'## M364 元数据探针传输核对 {TAG}\n\nCOM3 manifest-first 900B分块，全部文件SHA/root bash-n通过；仅传输，尚未读取内核统计，0Overlay/FPGA。证据SHA `{digest}`。下一步只执行一次元数据探针；原结果存在仅Collect。')
    print(r['status'],digest)

if __name__=='__main__':
    if sys.argv[1:] in (['prepare'],['sysfs-prepare']):prepare()
    elif sys.argv[1:]==['selftest']:print(selftest())
    elif len(sys.argv)==3 and sys.argv[1] in ('collect','sysfs-collect'):collect(sys.argv[2])
    elif len(sys.argv)==3 and sys.argv[1] in ('transfer','sysfs-transfer'):transfer(sys.argv[2])
    else:raise SystemExit('prepare | selftest | collect logfile')
