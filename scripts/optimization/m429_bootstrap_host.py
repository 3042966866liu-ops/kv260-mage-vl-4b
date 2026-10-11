"""Strict CPU-only receipts; existing attempts are collection only."""
import ast,base64,copy,hashlib,importlib.util,io,json,re,tempfile
from unittest.mock import patch
from m351_workflow import ROOT,BASE,HERE,atomic,encoded,sha,sync
PKG=BASE/'candidates/M429-isolated-bootstrap-03'
FOLDER=ROOT/'tmp/m429bootstrap01'
OUT=BASE/'runs/M429-isolated-bootstrap-board-01/BOARD_RESULT.json'
def check(r):
    if r['manifest_sha256']!=sha(PKG/'PACKAGE_MANIFEST.json') or type(r['gate_return_code']) is not int or r['gate_return_code'] not in (0,1):raise ValueError('Manifest/rc differs')
    for k in ('overlay_loads','DMA_allocations','real_model_forward_calls','FPGA_transactions','temperature_measurement_enabled','performance_pass'):
        if r[k] not in (0,False):raise ValueError('Forbidden CPU scope')
    for key in ('original_child_files',):
        for row in r.get(key,[]):file_check(row)
    for key in ('child_stdout','child_stderr'):
        if key in r:file_check(r[key])
    if r['status']=='FAIL_M429_ISOLATED_CPU_BOOTSTRAP':
        if r['gate_return_code']!=1 or not r['errors']:raise ValueError('Original failure incomplete')
        return r
    if r['status']!='PASS_M429_ISOLATED_CPU_BOOTSTRAP_ONLY' or r['gate_return_code'] or r['errors'] or r['child_return_code'] or r['source_identities_verified']!=49:raise ValueError('Complete CPU receipt required')
    b=r['bootstrap'];c=r['component']
    if not b['isolated'] or b['release']!='/home/ubuntu/tellme_release_install_20260926' or b['threads']!=1 or not b['torch_path'].startswith(b['release']+'/runtime_site/torch/'):raise ValueError('Isolated installed backend differs')
    if b['module_paths'][0]!=b['release']+'/runtime_site':raise ValueError('Frozen runtime bootstrap differs')
    if c['complete_wire_batches']!=286 or len(c['negative_checks'])!=20 or not c['restored'] or not c['fake_PL_submit'] or not c['no_DMA_or_Overlay'] or r['elapsed_s']>210:raise ValueError('Bounded actual CPU fixture incomplete')
    rows=r['original_child_files']
    if [x['path'] for x in rows]!=['/home/ubuntu/m429_late11_visual_numeric_01/component_stdout.bin','/home/ubuntu/m429_late11_visual_numeric_01/component_stderr.bin']:raise ValueError('Original child paths differ')
    stderr=base64.b64decode(rows[1]['base64'],validate=True)
    if b"ModuleNotFoundError: No module named 'torch'" not in stderr:raise ValueError('Original diagnosis not established')
    return r
def file_check(row):
    b=base64.b64decode(row['base64'],validate=True)
    if len(b)!=row['bytes'] or len(b)>32768 or hashlib.sha256(b).hexdigest()!=row['sha256'] or len(row['identity'])!=7:raise ValueError('Exact child file bytes differ')
    return b
def decode(text):
    hashes=re.findall(r'(?m)^M429_BOOT_RESULT_SHA256=([0-9a-f]{64})\s*$',text);codes=re.findall(r'(?m)^M429_BOOT_SAVED_GATE_RC=([01])\s*$',text)
    parts=re.findall(r'(?m)^M429_BOOT_RESULT_CHUNK=(\d+)/(\d+):([A-Za-z0-9+/=]+)\s*$',text)
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
    passed=r['status']=='PASS_M429_ISOLATED_CPU_BOOTSTRAP_ONLY'
    sync('latest_m429_isolated_bootstrap_board',dict(status=r['status'],result=OUT.relative_to(ROOT).as_posix(),sha256=digest,manifest_sha256=r['manifest_sha256'],CPU_bootstrap_pass=passed,hardware_visual_numerics_pass=False,hardware_visual_timing_unlocked=False),f'## M429 隔离CPU入口板端检查（2026-10-06）\n\nSHA {digest}，{count}块≤900B严格回收，rc{r["gate_return_code"]}，{r["status"]}。0真实模型前向/Overlay/DMA/PL/测温；原失败child字节独立SHA回收，新-I显式冻结runtime_site。通过仅允许新版本继续原视觉数值级，不是硬件/质量/性能PASS。')
    print('M429_BOOTSTRAP_BOARD_SYNC',digest,r['status'])
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
    if '__M429_BOOT_SYNTAX_RC_0__' not in (FOLDER/'syntax.log').read_text(encoding='utf-8-sig'):raise ValueError('bash-n absent')
    r=dict(status='PASS_M429_CPU_BOOTSTRAP_TRANSFER',manifest_sha256=sha(PKG/'PACKAGE_MANIFEST.json'),receipts=rows,CPU_gate_started=False)
    out=BASE/'runs/M429-isolated-bootstrap-transfer-01/RESULT.json';atomic(out,encoded(r),immutable=True)
    sync('latest_m429_isolated_bootstrap_transfer',dict(status=r['status'],result=out.relative_to(ROOT).as_posix(),sha256=sha(out),manifest_sha256=r['manifest_sha256']),f'## M429 CPU小包传输（2026-10-06）\n\nSHA {sha(out)}；manifest-first900B顺序/整文件SHA及bash-n通过。未执行模型、Overlay或PL。')
    print('M429_BOOTSTRAP_TRANSFER_SYNC',sha(out))
def prepare():
    old=BASE/'candidates/M429-isolated-bootstrap-02';PKG.mkdir(parents=True,exist_ok=False)
    for p in old.iterdir():
        if p.name not in ('PLAN.json','SHA256SUMS','PACKAGE_MANIFEST.json'):atomic(PKG/p.name,p.read_bytes(),immutable=True)
    plan=json.loads((old/'PLAN.json').read_bytes());plan={k:plan[k] for k in ('component_package','component_manifest_sha256','reused_packages','release')};atomic(PKG/'PLAN.json',encoded(plan),immutable=True)
    atomic(PKG/'SHA256SUMS',''.join(f'{sha(p)}  {p.name}\n' for p in sorted(PKG.iterdir())).encode(),immutable=True)
    files=sorted(PKG.iterdir());m=dict(file_count=len(files),total_bytes=sum(p.stat().st_size for p in files),files=[dict(path=p.name,bytes=p.stat().st_size,sha256=sha(p)) for p in files]);atomic(PKG/'PACKAGE_MANIFEST.json',encoded(m),immutable=True)
    for p in PKG.glob('*.py'):ast.parse(p.read_text(encoding='utf-8'),feature_version=(3,10))
    # Actual exporter to actual host decoder; explicit synthetic CPU receipt/root API.
    spec=importlib.util.spec_from_file_location('actual_cpu_export',PKG/'m429_bootstrap.py');export=importlib.util.module_from_spec(spec);spec.loader.exec_module(export)
    comp=json.loads((BASE/'runs/M429-streamed-scope-component-01/RESULT.json').read_bytes())['component']
    def file(name,b):return dict(path=name,bytes=len(b),sha256=hashlib.sha256(b).hexdigest(),base64=base64.b64encode(b).decode(),identity=[1,2,len(b),4,5,6,1])
    good=dict(status='PASS_M429_ISOLATED_CPU_BOOTSTRAP_ONLY',gate_return_code=0,manifest_sha256=sha(PKG/'PACKAGE_MANIFEST.json'),errors=[],overlay_loads=0,DMA_allocations=0,real_model_forward_calls=0,FPGA_transactions=0,temperature_measurement_enabled=False,performance_pass=False,source_identities_verified=49,child_return_code=0,elapsed_s=1.,component=comp,
        bootstrap=dict(isolated=True,release=plan['release'],threads=1,torch_path=plan['release']+'/runtime_site/torch/__init__.py',module_paths=[plan['release']+'/runtime_site']),
        original_child_files=[file('/home/ubuntu/m429_late11_visual_numeric_01/component_stdout.bin',b''),file('/home/ubuntu/m429_late11_visual_numeric_01/component_stderr.bin',b"ModuleNotFoundError: No module named 'torch'\n")],child_stdout=file('fixture',b'fixture'),child_stderr=file('fixture',b''))
    with tempfile.TemporaryDirectory(dir=ROOT/'tmp') as d:
        export.OUTPUT=__import__('pathlib').Path(d)/'BOARD_RESULT.json'
        def emit(r):
            raw=encoded(r);export.OUTPUT.write_bytes(raw);capture=io.StringIO()
            with patch.object(export.os,'geteuid',lambda:0,create=True),patch.object(export.time,'sleep',lambda x:None),__import__('contextlib').redirect_stdout(capture):export.emit()
            return capture.getvalue(),raw
        text,raw=emit(good);assert decode(text)[1]==raw
        failed=copy.deepcopy(good);failed.update(status='FAIL_M429_ISOLATED_CPU_BOOTSTRAP',gate_return_code=1,errors=['Explicit synthetic CPU failure']);assert decode(emit(failed)[0])[2]['gate_return_code']==1
        negatives=[]
        for name,edit in [('rc-bool',lambda x:x.__setitem__('gate_return_code',False)),('manifest',lambda x:x.__setitem__('manifest_sha256','0'*64)),('scope',lambda x:x.__setitem__('overlay_loads',1)),('thermal',lambda x:x.__setitem__('temperature_measurement_enabled',True)),('isolation',lambda x:x['bootstrap'].__setitem__('isolated',False)),('torch-root',lambda x:x['bootstrap'].__setitem__('torch_path','/usr/torch/__init__.py')),('fixture',lambda x:x['component'].__setitem__('complete_wire_batches',1)),('original-bytes',lambda x:x['original_child_files'][1].__setitem__('sha256','0'*64)),('source',lambda x:x.__setitem__('source_identities_verified',48))]:
            r=copy.deepcopy(good);edit(r)
            try:decode(emit(r)[0])
            except (ValueError,RuntimeError):negatives.append(name)
            else:raise AssertionError(name)
        for name,bad in [('missing',text.replace('M429_BOOT_RESULT_CHUNK=0/','M429_BOOT_REMOVED=0/')),('duplicate',text+text),('order',text.replace('M429_BOOT_RESULT_CHUNK=1/','M429_BOOT_RESULT_CHUNK=0/'))]:
            try:decode(bad)
            except ValueError:negatives.append(name)
            else:raise AssertionError(name)
    r=dict(status='PASS_M429_CPU_BOOTSTRAP_SUPPORT',manifest_sha256=sha(PKG/'PACKAGE_MANIFEST.json'),file_count=m['file_count'],total_bytes=m['total_bytes'],actual_export_decoder_PASS_FAIL=True,negative_checks=negatives,fixture_backend_and_root_explicitly_synthetic=True,source_sha256={n:sha(HERE/n) for n in ('m429_bootstrap_host.py','m429_bootstrap_control.ps1')},no_board_run=True)
    out=BASE/'runs/M429-isolated-bootstrap-support-01/RESULT.json';atomic(out,encoded(r),immutable=True)
    sync('latest_m429_isolated_bootstrap_support',dict(status=r['status'],result=out.relative_to(ROOT).as_posix(),sha256=sha(out),manifest_sha256=r['manifest_sha256']),f'## M429 CPU入口实际导出/回收支持（2026-10-06）\n\nSHA {sha(out)}；{len(negatives)}拒绝检查、实际exporter→hostdecode PASS/FAIL原字节，后端/root仅明确synthetic fixture。03小包只移除不用的大PLAN字段，{m["total_bytes"]}B；保留已冻结源码及组件，不复算旧算法。待COM3一次CPU检查，不加载Overlay。')
    print('M429_BOOTSTRAP_SUPPORT_SYNC',sha(out),r['manifest_sha256'],m['total_bytes'])
if __name__=='__main__':
    import sys
    if sys.argv[1:]==['prepare']:prepare()
    elif sys.argv[1:]==['transfer']:transfer()
    elif len(sys.argv)==3 and sys.argv[1]=='collect':collect(sys.argv[2])
    else:raise SystemExit('prepare | transfer | collect LOG')
