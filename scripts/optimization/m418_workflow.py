"""Strict transfer/collection for two unchanged-kernel visual lower gates."""
import base64,hashlib,json,re
from pathlib import Path
from m351_workflow import ROOT,BASE,HERE,atomic,encoded,sha,sync
from board_safety import safe_to_release
PKG=BASE/'candidates/M418-visual-linear-01'
MODES=('Descriptor','Chain')
def transfer(folder=ROOT/'tmp/m41801',save=True):
    manifest=json.loads((PKG/'PACKAGE_MANIFEST.json').read_bytes());receipts=[]
    for name in ['PACKAGE_MANIFEST.json']+[r['path'] for r in manifest['files']]:
        prefix='upload_'+name.replace('.','_');final=folder/(prefix+'_final.log');t=final.read_text(encoding='utf-8-sig')
        if 'M212_CHUNKED_FILE_PASS' not in t or sha(PKG/name) not in t:raise RuntimeError('Final file receipt differs')
        size=(PKG/name).stat().st_size;count=(size+899)//900;chunks=sorted(folder.glob(prefix+'_chunk_*.log'))
        if len(chunks)!=count:raise RuntimeError('Transfer count differs')
        for i,p in enumerate(chunks,1):
            if not re.search(r'M212_CHUNK_PASS\s+'+str(i)+r'\s+'+str(count)+r'\s+'+str(min(i*900,size))+r'\s',p.read_text(encoding='utf-8-sig')):raise RuntimeError('Chunk receipt differs')
        receipts.append(dict(path=name,sha256=sha(PKG/name),chunks=count,receipt_sha256=sha(final)))
    syntax=folder/'syntax.log'
    if '__M418_SYNTAX_RC_0__' not in syntax.read_text(encoding='utf-8-sig'):raise RuntimeError('Runner syntax missing')
    value=dict(status='PASS_M418_MANIFEST_FIRST_TRANSFER',manifest_sha256=sha(PKG/'PACKAGE_MANIFEST.json'),files=receipts,syntax_sha256=sha(syntax),hardware_gate_started=False)
    if save:
        out=BASE/'runs/M418-visual-linear-transfer-01/RESULT.json';atomic(out,encoded(value),immutable=True)
        sync('latest_m418_visual_linear_transfer',dict(status=value['status'],result=out.relative_to(ROOT).as_posix(),sha256=sha(out),manifest_sha256=value['manifest_sha256']),
            f'## M418 视觉最小硬件门禁传输（2026-10-06）\n\nSHA {sha(out)}；全部manifest-first/900B回执、完整SHA和bash-n通过。只准备同保存输入单descriptor→双descriptor chain，尚未执行，无完整MLP或性能。')
    return value
def decode(t,mode,prior=None):
    if mode not in MODES:raise ValueError('Invalid mode')
    hashes=re.findall(r'(?m)^M418_RESULT_SHA256=([0-9a-f]{64})\s*$',t);codes=re.findall(r'(?m)^M418_SAVED_GATE_RC=([01])\s*$',t)
    chunks=re.findall(r'(?m)^M418_RESULT_CHUNK=(\d+)/(\d+):([A-Za-z0-9+/=]+)\s*$',t)
    if len(hashes)!=1 or len(codes)!=1 or not chunks or len(chunks)!=int(chunks[0][1]):raise ValueError('Incomplete/duplicate saved result')
    parts=[]
    for i,(index,total,data) in enumerate(chunks):
        p=base64.b64decode(data,validate=True)
        if int(index)!=i or int(total)!=len(chunks) or not 0<len(p)<=900:raise ValueError('Chunk order/size differs')
        parts.append(p)
    raw=b''.join(parts);digest=hashlib.sha256(raw).hexdigest()
    if digest!=hashes[0]:raise ValueError('Original byte SHA differs')
    r=json.loads(raw);rc=int(codes[0]);spec=json.loads((PKG/'BOARD_CASES.json').read_bytes())
    if r['gate_level']!=mode or r['build_id']!='0x4D333537' or r['manifest_sha256']!=sha(PKG/'PACKAGE_MANIFEST.json') or type(r['gate_return_code']) is not int or r['gate_return_code']!=rc:raise ValueError('Gate identity/rc differs')
    if any(r[k] is not False for k in ('performance_pass','full_model','video','promoted')):raise ValueError('Evidence scope changed')
    if mode=='Chain' and r.get('prior_raw_sha256')!=prior:raise ValueError('Previous descriptor identity differs')
    done=re.findall(r'M418_DONE gate_rc=(\d+) export_rc=(\d+)',t)
    if done and done!=[(str(rc),'0')]:raise ValueError('Gate/export rc differs')
    if r['status']=='PASS_M418_'+mode.upper():
        if rc or r['errors'] or not all(r[k] is True for k in ('package_verified','numerical_pass','safe_buffers_released','stable_restored','boot_unchanged','cmdline_unchanged')) or r['unsafe_dma_buffers_retained']:raise ValueError('Incomplete PASS/lifecycle')
        if r['stable_sources_verified']!=len(spec['stable_sources']) or r['hardware_closure_sha256']!=sha(PKG/'HARDWARE_CLOSURE.json'):raise ValueError('Source/circuit closure differs')
        rows=r['transactions'];case=spec['cases'][mode];gold=case['saved_batch'];chain=case['chain']
        if len(rows)!=3 or r['physical_transactions_started']!=3 or [x['label'] for x in rows]!=['candidate-legal-build-id','visual-'+mode.lower(),'stable-restored-build-id']:raise ValueError('Same Overlay minimal/visual/restore order differs')
        for i,x in enumerate(rows):
            expected=0x4d395832 if i==2 else 0x4d333537
            if not x['full_output_exact'] or x['expected_sha256']!=x['output_sha256'] or not safe_to_release(x['completed_snapshot']) or x['completed_snapshot']['ap_return']!=expected or type(x['wait_ns']) is not int or x['wait_ns']<=0 or int(x['build_id'],16)!=expected:raise ValueError('Complete output/completion/Build differs')
            p=gold if i==1 else spec['build_bytes']
            if x['packet_sha256']!=p['packet_sha256'] or x['expected_sha256']!=p['raw_sha256'] or x['input_bytes']!=p['input_bytes'] or x['output_bytes']!=p['output_bytes'] or int(x['config'],16)!=int(chain['config'] if i==1 else spec['build_config'],16):raise ValueError('Saved packet/raw/config differs')
        if r['saved_reference']!=dict(reference_raw_sha256=spec['reference_raw_sha256'],part=case['part'],selected_shift=case['shift'],packet_sha256=gold['packet_sha256'],raw_sha256=gold['raw_sha256']):raise ValueError('Actual saved source differs')
        allocations=r['allocations'];expected=[]
        if len(allocations)!=18:raise ValueError('Allocation count differs')
        for i in range(0,18,6):expected.extend(reversed(allocations[i:i+6]))
        if expected!=r['releases']:raise ValueError('Owner release sequence differs')
        if len(r['memory'])!=6 or any(x['required_cma_free_bytes']!=0 or x['CmaFree']<0 or x['MemAvailable']<128<<20 for x in r['memory']):raise ValueError('Actual reserve rejected')
        if [x['build_id'] for x in r['overlay_loads']]!=['0x4d333537','0x4d395832'] or not safe_to_release(r['final_snapshot']) or r['final_snapshot']['ap_return']!=0x4d395832:raise ValueError('Same Overlay/rollback completion differs')
    elif r['status'].startswith('FAIL_'):
        if rc!=1 or not r['errors']:raise ValueError('Failure lacks original error')
    else:raise ValueError('Unknown status')
    return digest,raw,r,len(chunks)
def collect(log,mode,prior=None,out=None,sync_function=sync):
    digest,raw,r,count=decode(Path(log).read_text(encoding='utf-8-sig'),mode,prior)
    out=out or BASE/f'runs/M418-visual-{mode.lower()}-board-01/BOARD_RESULT.json';atomic(out,raw,immutable=True)
    report=f'# M418 视觉{mode}最小用例\n\n{r["status"]}，原rc {r["gate_return_code"]}，原SHA {digest}。\n\n同M417保存第13层输入和完整FP16/FTZ wire输出；原并行Build0x4D333537，每次先同Overlay合法最小事务再视觉事务，末态稳定Build0x4D395832。仅本级数值，不是完整MLP、语义质量或净耗时结论。\n\n'+json.dumps(r.get('transactions',r['errors']),ensure_ascii=False,indent=2)+'\n'
    atomic(out.with_name('REPORT.md'),report.encode('utf-8'),immutable=True)
    sync_function('latest_m418_visual_'+mode.lower(),dict(status=r['status'],result=out.relative_to(ROOT).as_posix(),sha256=digest,manifest_sha256=r['manifest_sha256'],build_id=r['build_id'],numerical_pass=r.get('numerical_pass',False),performance_pass=False),
        f'## M418 视觉{mode}最小硬件门禁（2026-10-06）\n\n原SHA {digest}，{count}个≤900B严格回收，rc{r["gate_return_code"]}；{r["status"]}。只本级完整原FTZ wire数值及受控生命周期，无模型前向/性能或24层晋级；同步后才解锁下一级，失败只停本级。')
    print('M418_RESULT_SYNC',mode,digest,count);return r
if __name__=='__main__':
    import sys
    if sys.argv[1:]==['transfer']:transfer()
    elif len(sys.argv) in (4,5) and sys.argv[1]=='collect':collect(sys.argv[3],sys.argv[2],sys.argv[4] if len(sys.argv)==5 else None)
    else:raise SystemExit('transfer | collect MODE LOG [PRIOR_SHA]')
