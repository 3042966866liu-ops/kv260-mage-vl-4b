"""Strict CPU-only receipts; existing attempts are collection only."""
import ast,base64,copy,hashlib,importlib.util,io,json,re,tempfile
from unittest.mock import patch
from m351_workflow import ROOT,BASE,HERE,atomic,encoded,sha,sync
PKG=BASE/'candidates/M431-borrowed-late11-CPU-02'
FOLDER=ROOT/'tmp/m431cpu02'
OUT=BASE/'runs/M431-borrowed-CPU-board-01/BOARD_RESULT.json'
def check(r):
    if r['manifest_sha256']!=sha(PKG/'PACKAGE_MANIFEST.json') or type(r['gate_return_code']) is not int or r['gate_return_code'] not in (0,1):raise ValueError('Manifest/rc differs')
    for k in ('overlay_loads','DMA_allocations','real_model_forward_calls','FPGA_transactions','temperature_measurement_enabled','performance_pass'):
        if r[k] not in (0,False):raise ValueError('Forbidden CPU scope')
    for key in ('original_child_files',):
        for row in r.get(key,[]):file_check(row)
    for key in ('child_stdout','child_stderr'):
        if key in r:file_check(r[key])
    if r['status']=='FAIL_M431_ISOLATED_CPU_BOOTSTRAP':
        if r['gate_return_code']!=1 or not r['errors']:raise ValueError('Original failure incomplete')
        return r
    if r['status']!='PASS_M431_ISOLATED_CPU_BOOTSTRAP_ONLY' or r['gate_return_code'] or r['errors'] or r['child_return_code'] or r['source_identities_verified']!=49:raise ValueError('Complete CPU receipt required')
    b=r['bootstrap'];c=r['component']
    if not b['isolated'] or b['release']!='/home/ubuntu/tellme_release_install_20260926' or b['threads']!=1 or not b['torch_path'].startswith(b['release']+'/runtime_site/torch/'):raise ValueError('Isolated installed backend differs')
    if b['module_paths'][0]!=b['release']+'/runtime_site':raise ValueError('Frozen runtime bootstrap differs')
    if r['elapsed_s']>210 or not all(k in r for k in ('child_stdout','child_stderr')):raise ValueError('Bounded child evidence absent')
    if not b['numpy_path'].startswith(b['release']+'/runtime_site/numpy/'):raise ValueError('Frozen NumPy path differs')
    w=c['window'];n=c['negative']
    required=dict(complete_batches=286,staged_windows=22,staged_bytes=49020928,fake_original_buffer_bytes=33484832,alternating_outputs=[143,143],extra_DMA_allocate_or_free_calls=0)
    if any(w.get(k)!=v for k,v in required.items()):raise ValueError('Complete geometry/ownership fixture differs')
    for k in ('full286_original_geometry_and_saved_shifts','fake_DMA_MMIO_policy_and_byte_content','original_buffer_identities_unchanged','static_cache_invalidated','all_fixture_files_released'):
        if w.get(k) is not True:raise ValueError('Window fixture scope differs')
    if w['actual_PL_numerics_or_complete_runtime_capacity_proven'] is not False or n['actual_PL_or_capacity_proven'] is not False or n['extra_allocate_or_free_calls']!=0 or n['real_array_geometry_bytes']!=33484832 or len(n['negative_checks'])!=15 or not n['fake_DMA_MMIO_memory'] or not n['timeout_preserves_original_owner'] or not n['static_cache_invalidated']:raise ValueError('Fake scope/negative ownership incomplete')
    return r
def file_check(row):
    b=base64.b64decode(row['base64'],validate=True)
    if len(b)!=row['bytes'] or len(b)>32768 or hashlib.sha256(b).hexdigest()!=row['sha256'] or len(row['identity'])!=7:raise ValueError('Exact child file bytes differ')
    return b
def decode(text):
    hashes=re.findall(r'(?m)^M431_BOOT_RESULT_SHA256=([0-9a-f]{64})\s*$',text);codes=re.findall(r'(?m)^M431_BOOT_SAVED_GATE_RC=([01])\s*$',text)
    parts=re.findall(r'(?m)^M431_BOOT_RESULT_CHUNK=(\d+)/(\d+):([A-Za-z0-9+/=]+)\s*$',text)
    if len(hashes)!=1 or len(codes)!=1 or not parts or len(parts)!=int(parts[0][1]):raise ValueError('Exact export receipt required')
    raw=[]
    for i,(index,total,data) in enumerate(parts):
        b=base64.b64decode(data,validate=True)
        if int(index)!=i or int(total)!=len(parts) or not 0<len(b)<=900:raise ValueError('Chunk order/size differs')
        raw.append(b)
    raw=b''.join(raw)
    if len(raw)>131072 or hashlib.sha256(raw).hexdigest()!=hashes[0]:raise ValueError('Whole SHA/budget differs')
    r=check(json.loads(raw))
    if r['gate_return_code']!=int(codes[0]):raise ValueError('Original gate rc differs')
    return hashes[0],raw,r,len(parts)
def collect(path):
    digest,raw,r,count=decode((ROOT/path).read_text(encoding='utf-8-sig'));atomic(OUT,raw,immutable=True)
    for i,row in enumerate(r.get('original_child_files',[])):atomic(OUT.parent/('original_component_'+('stdout' if i==0 else 'stderr')+'.bin'),file_check(row),immutable=True)
    for name in ('child_stdout','child_stderr'):
        if name in r:atomic(OUT.parent/(name+'.bin'),file_check(r[name]),immutable=True)
    passed=r['status']=='PASS_M431_ISOLATED_CPU_BOOTSTRAP_ONLY'
    sync('latest_m431_borrowed_CPU_board',dict(status=r['status'],result=OUT.relative_to(ROOT).as_posix(),sha256=digest,manifest_sha256=r['manifest_sha256'],CPU_bootstrap_pass=passed,hardware_visual_numerics_pass=False,hardware_visual_timing_unlocked=False),f'## M431 隔离CPU入口板端检查（2026-10-06）\n\nSHA {digest}，{count}块≤900B严格回收，rc{r["gate_return_code"]}，{r["status"]}。0真实模型前向/Overlay/DMA/PL/测温；实际-I冻结runtime_site NumPy几何、286批/22暂存及15拒绝，DMA/MMIO明确fake；不是完整runtime容量、硬件数值或性能PASS。下一步隔离完整请求接入数值，不自动执行性能。')
    print('M431_BOOTSTRAP_BOARD_SYNC',digest,r['status'])
def transfer():
    m=json.loads((PKG/'PACKAGE_MANIFEST.json').read_bytes());rows=[]
    for name in ['PACKAGE_MANIFEST.json']+[x['path'] for x in m['files']]:
        p=PKG/name;prefix='upload_'+name.replace('.','_');count=(p.stat().st_size+899)//900
        text=(FOLDER/(prefix+'_final.log')).read_text(encoding='utf-8-sig')
        if 'M212_CHUNKED_FILE_PASS' not in text or sha(p) not in text:raise ValueError('Whole upload SHA receipt absent')
        logs=sorted(FOLDER.glob(prefix+'_chunk_*.log'))
        if len(logs)!=count:raise ValueError('Upload count differs')
        for i,log in enumerate(logs,1):
            if not re.search(r'M212_CHUNK_PASS\s+'+str(i)+r'\s+'+str(count)+r'\s+'+str(min(i*900,p.stat().st_size))+r'\s',log.read_text(encoding='utf-8-sig')):raise ValueError('Upload ordinal differs')
        rows.append(dict(path=name,sha256=sha(p),chunks=count))
    if '__M431_BOOT_SYNTAX_RC_0__' not in (FOLDER/'syntax.log').read_text(encoding='utf-8-sig'):raise ValueError('bash-n absent')
    r=dict(status='PASS_M431_CPU_BOOTSTRAP_TRANSFER',manifest_sha256=sha(PKG/'PACKAGE_MANIFEST.json'),receipts=rows,CPU_gate_started=False)
    out=BASE/'runs/M431-borrowed-CPU-transfer-01/RESULT.json';atomic(out,encoded(r),immutable=True)
    sync('latest_m431_borrowed_CPU_transfer',dict(status=r['status'],result=out.relative_to(ROOT).as_posix(),sha256=sha(out),manifest_sha256=r['manifest_sha256']),f'## M431 CPU小包传输（2026-10-06）\n\nSHA {sha(out)}；manifest-first900B顺序/整文件SHA及bash-n通过。未执行模型、Overlay或PL。')
    print('M431_BOOTSTRAP_TRANSFER_SYNC',sha(out))

if __name__=='__main__':
    import sys
    if sys.argv[1:]==['transfer']:transfer()
    elif len(sys.argv)==3 and sys.argv[1]=='collect':collect(sys.argv[2])
    else:raise SystemExit('transfer | collect LOG')
