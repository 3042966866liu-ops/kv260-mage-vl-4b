"""Supplement missing UART blocks from one immutable saved result; no FPGA."""
import base64
import hashlib
import json
from pathlib import Path
import re
import sys
import m351_workflow as w
import m36803_collect
ROOT=w.ROOT/'tmp/m368_saved_recovery_01'
RAW_SHA='dbd3325e8152bf24402ce616b7fad4fe0584a4e7972aae573fb245a4eb52abaf'

def valid_rows(log):
    rows=re.findall(r'(?m)^M368_RESULT_CHUNK=(\d+)/(\d+):([A-Za-z0-9+/=]+)\s*$',log)
    valid=[];invalid=[]
    for i,n,b in rows:
        try:
            raw=base64.b64decode(b,validate=True)
            if not 0<len(raw)<=900 or (int(i)<2974 and len(raw)!=900):raise ValueError('Truncated block')
        except ValueError:invalid.append(int(i));continue
        valid.append((i,n,b))
    return valid,invalid

def prepare():
    log=(w.ROOT/'tmp/m36803/run.log').read_text(encoding='utf-8-sig')
    rows,invalid=valid_rows(log)
    have={int(i) for i,n,b in rows}
    missing=[i for i in range(2975) if i not in have]
    if len(have)!=len(rows) or not missing:raise RuntimeError('Unexpected original recovery shape')
    source='''import base64,hashlib,os,time
from pathlib import Path
if os.geteuid()!=0:raise RuntimeError('Root required')
raw=Path('/home/ubuntu/m368_staged_video_02/B1/load-memory.json').read_bytes()
if hashlib.sha256(raw).hexdigest()!=RAW_SHA:raise RuntimeError('Original saved SHA differs')
parts=[raw[i:i+900] for i in range(0,len(raw),900)]
if len(parts)!=2975:raise RuntimeError('Original chunk count differs')
print('M368_RECOVERY_SHA='+RAW_SHA,flush=True)
for i in MISSING:
    print(f'M368_RECOVERY_CHUNK={i}/2975:'+base64.b64encode(parts[i]).decode(),flush=True)
    time.sleep(.12)
print('M368_RECOVERY_DONE_NO_GATE',flush=True)
'''
    source='RAW_SHA='+repr(RAW_SHA)+'\nMISSING='+repr(missing)+'\n'+source
    w.atomic(ROOT/'export_saved.py',source.encode(),immutable=True)
    w.atomic(ROOT/'REQUEST.json',w.encoded(dict(raw_sha256=RAW_SHA,missing=missing,invalid_original_blocks=invalid,original_log_sha256=w.sha(w.ROOT/'tmp/m36803/run.log'),export_sha256=w.sha(ROOT/'export_saved.py'),hardware_rerun=False)),immutable=True)
    print(json.dumps(dict(missing=len(missing),export_sha256=w.sha(ROOT/'export_saved.py'))))

def finish():
    request=json.loads((ROOT/'REQUEST.json').read_text(encoding='utf-8'))
    original=w.ROOT/'tmp/m36803/run.log';assert w.sha(original)==request['original_log_sha256']
    source=original.read_text(encoding='utf-8-sig');saved=(ROOT/'recover.log').read_text(encoding='utf-8-sig')
    if 'M368_RECOVERY_SHA='+RAW_SHA not in saved or 'M368_RECOVERY_DONE_NO_GATE' not in saved:raise RuntimeError('Recovery incomplete')
    old,invalid=valid_rows(source)
    assert invalid==request['invalid_original_blocks']
    extra=re.findall(r'(?m)^M368_RECOVERY_CHUNK=(\d+)/(\d+):([A-Za-z0-9+/=]+)\s*$',saved)
    if [int(i) for i,n,b in extra]!=request['missing']:raise RuntimeError('Supplement set/order differs')
    rows={int(i):(n,b) for i,n,b in old}
    for i,n,b in extra:
        if int(i) in rows:raise RuntimeError('Supplement overlaps')
        rows[int(i)]=(n,b)
    if set(rows)!=set(range(2975)):raise RuntimeError('Full sequence missing')
    merged='M368_RESULT_SHA256='+RAW_SHA+'\nM368_SAVED_GATE_RC=0\n'+''.join(f'M368_RESULT_CHUNK={i}/{rows[i][0]}:{rows[i][1]}\n' for i in range(2975))+'M368_DONE case=B1 gate_rc=0 export_rc=0\n'
    m36803_collect.decode(merged)
    w.atomic(ROOT/'merged.log',merged.encode(),immutable=True)
    m36803_collect.collect(ROOT/'merged.log')
    out=w.BASE/'runs/M368-result-recovery-01'
    r=dict(status='PASS_ORIGINAL_RAW_RECOVERED_NO_GATE',raw_sha256=RAW_SHA,original_run_log_sha256=w.sha(original),request_sha256=w.sha(ROOT/'REQUEST.json'),export_sha256=w.sha(ROOT/'export_saved.py'),recovery_log_sha256=w.sha(ROOT/'recover.log'),merged_log_sha256=w.sha(ROOT/'merged.log'),supplemented_chunks=request['missing'],all_chunks=2975,gate_return_code=0,export_return_code=0,hardware_rerun=False)
    w.atomic(out/'RESULT.json',w.encoded(r),immutable=True);digest=w.sha(out/'RESULT.json')
    w.sync('latest_m368_saved_result_recovery',dict(status=r['status'],sha256=digest,result=(out/'RESULT.json').relative_to(w.ROOT).as_posix(),raw_sha256=RAW_SHA),f'## M368 串口原字节回收修复\n\n首次2975块回收缺失或损坏{len(request["missing"])}块；只从已保存结果补取900B块，不重新执行门禁。原日志冻结SHA，补块顺序/集合严格核对，最终原SHA `{RAW_SHA}` 完全一致，原rc0/export0保持。回收证据SHA `{digest}`。')

def package():
    prepare()
    pkg=w.BASE/'candidates/M368-saved-byte-recovery-01'
    source=(ROOT/'export_saved.py').read_text(encoding='utf-8')
    check='''import hashlib,json,sys
from pathlib import Path
task_root=Path(__file__).resolve().parent
task_manifest=task_root/'PACKAGE_MANIFEST.json'
if len(sys.argv)!=2 or hashlib.sha256(task_manifest.read_bytes()).hexdigest()!=sys.argv[1]:raise RuntimeError('Recovery manifest differs')
task_rows=json.loads(task_manifest.read_text(encoding='utf-8'))['files']
if [r['path'] for r in task_rows]!=['export_saved.py','SHA256SUMS']:raise RuntimeError('Recovery whitelist differs')
for task_row in task_rows:
    task_file=task_root/task_row['path']
    if task_file.stat().st_size!=task_row['bytes'] or hashlib.sha256(task_file.read_bytes()).hexdigest()!=task_row['sha256']:raise RuntimeError('Recovery payload differs')
if {p.name for p in task_root.iterdir()}!={'PACKAGE_MANIFEST.json','export_saved.py','SHA256SUMS'}:raise RuntimeError('Recovery directory differs')
'''
    w.atomic(pkg/'export_saved.py',(check+source).encode(),immutable=True)
    w.atomic(pkg/'SHA256SUMS',(w.sha(pkg/'export_saved.py')+'  export_saved.py\n').encode(),immutable=True)
    rows=[dict(path=n,sha256=w.sha(pkg/n),bytes=(pkg/n).stat().st_size) for n in ('export_saved.py','SHA256SUMS')]
    w.atomic(pkg/'PACKAGE_MANIFEST.json',w.encoded(dict(schema='saved-byte-export-only-v1',files=rows,file_count=2,total_bytes=sum(r['bytes'] for r in rows),hardware_rerun=False)),immutable=True)
    print('RECOVERY_MANIFEST_SHA='+w.sha(pkg/'PACKAGE_MANIFEST.json'))

if __name__=='__main__':package() if sys.argv[1]=='Package' else prepare() if sys.argv[1]=='Prepare' else finish()
