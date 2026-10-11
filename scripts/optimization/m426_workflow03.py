"""Strict saved range result recovery. Task/performance remain locked."""
import base64,hashlib,json,math,re
from pathlib import Path
from m351_workflow import ROOT,BASE,HERE,atomic,encoded,sha,sync
PKG=BASE/'candidates/M426-all-FP32-MLP-software-02'
OUT=BASE/'runs/M426-range-software-board-02/BOARD_RESULT.json'
def check(r):
    plan=json.loads((PKG/'PLAN.json').read_bytes());expected=json.loads((PKG/'EXPECTED_VISUAL.json').read_bytes())
    if r['gate_level']!='CPU-only-cumulative-visual-MLP-range-screen' or r['manifest_sha256']!=sha(PKG/'PACKAGE_MANIFEST.json') or type(r['gate_return_code']) is not int or r['selected_layers']!=list(range(2,24)):raise ValueError('Scope/identity/rc differs')
    for key in ('overlay_loaded','dma_allocations','fpga_transactions','language_forward_calls','temperature_measurement_enabled','performance_pass','formal_promotion_allowed','task_screen_pass','task_screen_recorded','numerical_hardware_proven'):
        if r.get(key) not in (False,0) or key not in r:raise ValueError('Wrong scope '+key)
    if r['status'] in ('PASS_M426_FEATURE_SCREEN_TASK_PENDING','REJECT_M426_ALL22_FEATURE_RANGE'):
        if r['gate_return_code'] or r['errors'] or r['visual_forward_calls']!=2 or r['logical_reference_calls']!=572 or r['peak_live_layer_scopes']!=1:raise ValueError('Incomplete software screen')
        for k in ('software_screen_completed','bindings_restored','visual_owner_closed','no_pynq_import','boot_unchanged','cmdline_unchanged','original_reference_pass'):
            if r.get(k) is not True:raise ValueError('Incomplete lifecycle/reference '+k)
        if r['preprocessed']!=expected['preprocessed'] or r['original_visual']!=expected['visual'] or r['source_identities_verified']!=49:raise ValueError('Frozen original/source differs')
        if r['backend_before']!=r['backend_after'] or r['CPU_store_after']['cache_within_budget'] is not True or r['release_preflight']['status']!='READY_FOR_BOARD_PREFLIGHT':raise ValueError('Backend/store/assets differ')
        if r['weight_windows']!=plan['windows'] or set(r['targets'])!=set(map(str,range(2,24))) or set(r['reference_batches'])!=set(map(str,range(2,24))):raise ValueError('Complete selection/weights differ')
        if set(r['prefix_topology'])!={'0','1'} or any(x['conversion_wrapper'] is not False or x['encoder']!='MageVLVisionEncoderLayer' or x['target_dtype']!='torch.bfloat16' or x['output_dtype']!='torch.bfloat16' for x in r['prefix_topology'].values()):raise ValueError('Native BF16 prefix evidence differs')
        for i in range(2,24):
            target=r['targets'][str(i)]
            if target['target_dtype']!='torch.float32' or target['output_dtype']!='torch.bfloat16' or set(target['matrices'])!={'fc1','fc2'}:raise ValueError('Frozen selected precision differs')
            for part,shape in (('fc1',[1024,4096]),('fc2',[4096,1024])):
                matrix=target['matrices'][part]
                if matrix['name']!=f'encoder.layers.{i}.mlp.{part}' or matrix['shape']!=shape or not re.fullmatch('[0-9a-f]{64}',matrix['bias_sha256']):raise ValueError('Actual selected matrix/bias identity differs')
            if set(r['reference_batches'][str(i)])!={'fc1','fc2'}:raise ValueError('Two Linear batches required')
            for part,rows in r['reference_batches'][str(i)].items():
                chain=plan['chains'][str(i)][part]
                if len(rows)!=13:raise ValueError('Complete13 batches required')
                for n,b in enumerate(rows):
                    if b['start']!=32*n or b['rows']!=(32 if n<12 else 8) or b['input_bytes']!=chain['input_bytes'] or b['output_bytes']!=chain['output_bytes'] or b['logical_calls']!=1:raise ValueError('Frozen T32 geometry differs')
                    first,last=b['initial_shift'],b['selected_shift']
                    if type(first) is not int or type(last) is not int or not 0<=last<=first<=6 or b['attempted_shifts']!=list(range(first,last-1,-1)) or b['physical_reference_attempts']!=len(b['attempted_shifts']):raise ValueError('Retry policy/count differs')
                    for key in ('packet_sha256','raw_sha256'):
                        if not re.fullmatch('[0-9a-f]{64}',b[key]):raise ValueError('Reference SHA invalid')
        attempts=sum(b['physical_reference_attempts'] for parts in r['reference_batches'].values() for rows in parts.values() for b in rows)
        if attempts!=r['physical_reference_attempts'] or attempts<572:raise ValueError('Reference retry accounting differs')
        if [x['layer'] for x in r['boundary_comparison']]!=list(range(24)):raise ValueError('All24 cumulative boundary errors required')
        for row in r['boundary_comparison']:
            if row['metrics']['shape']!=[392,1024] or any(not math.isfinite(row['metrics'][k]) for k in ('cosine','relative_l2','RMSE','max_abs','min_token_cosine')):raise ValueError('Finite complete boundary metrics required')
        quality=r['full_visual_quality'];m=quality['metrics'];thresholds=plan['feature_thresholds']
        tensor=r['candidate_visual']
        if tensor['shape']!=[98,2560] or tensor['dtype']!='float32' or tensor['bytes']!=1003520 or not re.fullmatch('[0-9a-f]{64}',tensor['sha256']):raise ValueError('Complete candidate feature identity required')
        if m['shape']!=[98,2560] or quality['thresholds']!=thresholds or quality['semantic_accuracy_proven']:raise ValueError('Feature/semantic scope differs')
        if any(not math.isfinite(m[k]) for k in ('cosine','relative_l2','RMSE','max_abs','min_token_cosine')):raise ValueError('Finite final metrics required')
        passed=m['relative_l2']<=.02 and m['cosine']>=.999 and m['min_token_cosine']>=.995
        if type(r['feature_screen_pass']) is not bool or r['feature_screen_pass']!=passed or quality['feature_screen_pass']!=passed or (r['status']=='PASS_M426_FEATURE_SCREEN_TASK_PENDING')!=passed:raise ValueError('Original feature verdict differs')
        if [x['path'] for x in r['retained_features']]!=['original_visual.npy','candidate_visual.npy'] or any(x['bytes']!=1003648 or not re.fullmatch('[0-9a-f]{64}',x['sha256']) for x in r['retained_features']):raise ValueError('Bounded complete saved features required')
        if r['elapsed_s_diagnostic_not_performance']>plan['budget_seconds']+60:raise ValueError('Bounded software run exceeded')
    elif r['status']=='FAIL_M426_SOFTWARE_RANGE':
        if r['gate_return_code']!=1 or not r['errors']:raise ValueError('Original failure missing')
    else:raise ValueError('Unknown saved status')
    return r
def decode(log):
    hashes=re.findall(r'(?m)^M426_RESULT_SHA256=([0-9a-f]{64})\s*$',log);codes=re.findall(r'(?m)^M426_SAVED_GATE_RC=([01])\s*$',log)
    chunks=re.findall(r'(?m)^M426_RESULT_CHUNK=(\d+)/(\d+):([A-Za-z0-9+/=]+)\s*$',log)
    if len(hashes)!=1 or len(codes)!=1 or not chunks or len(chunks)!=int(chunks[0][1]):raise ValueError('Incomplete/duplicate export')
    parts=[]
    for i,(index,total,b64) in enumerate(chunks):
        p=base64.b64decode(b64,validate=True)
        if int(index)!=i or int(total)!=len(chunks) or not 0<len(p)<=900:raise ValueError('Chunk order/size differs')
        parts.append(p)
    raw=b''.join(parts);digest=hashlib.sha256(raw).hexdigest()
    if len(raw)>2<<20 or digest!=hashes[0]:raise ValueError('Whole raw SHA/budget differs')
    result=check(json.loads(raw))
    if result['gate_return_code']!=int(codes[0]):raise ValueError('Original rc differs')
    done=re.findall(r'M426_DONE gate_rc=(\d+) export_rc=(\d+)',log)
    if done and done!=[(codes[0],'0')]:raise ValueError('Gate/export rc differs')
    return digest,raw,result,len(chunks)
def collect(path):
    digest,raw,r,chunks=decode(Path(path).read_text(encoding='utf-8-sig'));atomic(OUT,raw,immutable=True)
    note=f'## M426 22层视觉MLP精确软件范围结果（2026-10-06）\n\n原SHA {digest}，{chunks}块≤900B严格回收；{r["status"]}，rc{r["gate_return_code"]}。0Overlay/DMA/语言/FPGA/测温；原版完整SHA先对齐、24层累计边界与完整feature判据不改。feature通过{r["feature_screen_pass"]}，任务判断尚未执行，不能解锁视觉PL计时或生产晋级。失败只收集不自动重跑。'
    sync('latest_m426_range_software_board',dict(status=r['status'],result=OUT.relative_to(ROOT).as_posix(),sha256=digest,manifest_sha256=r['manifest_sha256'],feature_screen_pass=r['feature_screen_pass'],task_screen_pass=False,hardware_visual_timing_unlocked=False,performance_pass=False),note)
    atomic(OUT.with_name('REPORT.md'),('# M426 软件范围筛查\n\n'+note+'\n\n```json\n'+json.dumps(r.get('full_visual_quality',r['errors']),ensure_ascii=False,indent=2)+'\n```\n').encode('utf-8'),immutable=True)
    print('M426_RESULT_SYNC',digest,r['status']);return r
def transfer():
    m=json.loads((PKG/'PACKAGE_MANIFEST.json').read_bytes());folder=ROOT/'tmp/m42603';receipts=[]
    for name in ['PACKAGE_MANIFEST.json']+[x['path'] for x in m['files']]:
        size=(PKG/name).stat().st_size;count=(size+899)//900;prefix='upload_'+name.replace('.','_')
        final=(folder/(prefix+'_final.log')).read_text(encoding='utf-8-sig')
        if 'M212_CHUNKED_FILE_PASS' not in final or sha(PKG/name) not in final:raise ValueError('Whole transfer SHA missing')
        logs=sorted(folder.glob(prefix+'_chunk_*.log'))
        if len(logs)!=count:raise ValueError('Transfer receipt count differs')
        for i,p in enumerate(logs,1):
            if not re.search(r'M212_CHUNK_PASS\s+'+str(i)+r'\s+'+str(count)+r'\s+'+str(min(i*900,size))+r'\s',p.read_text(encoding='utf-8-sig')):raise ValueError('Transfer order/byte receipt differs')
        receipts.append(dict(path=name,sha256=sha(PKG/name),chunks=count))
    if '__M426_SYNTAX_RC_0__' not in (folder/'syntax.log').read_text(encoding='utf-8-sig'):raise ValueError('Board bash-n receipt missing')
    r=dict(status='PASS_M426_MANIFEST_FIRST_HASHED_TRANSFER',manifest_sha256=sha(PKG/'PACKAGE_MANIFEST.json'),receipts=receipts,software_gate_started=False)
    p=BASE/'runs/M426-range-transfer-02/RESULT.json';atomic(p,encoded(r),immutable=True)
    sync('latest_m426_range_transfer',dict(status=r['status'],result=p.relative_to(ROOT).as_posix(),sha256=sha(p),manifest_sha256=r['manifest_sha256']),f'## M426 软件范围包传输（2026-10-06）\n\nSHA {sha(p)}；manifest-first900B全部回执/逐文件SHA及bash-n通过，未执行。下一步固定原版视觉→22层精确软件视觉，无Overlay/DMA/语言/测温。')
    print('M426_TRANSFER_SYNC',sha(p))
if __name__=='__main__':
    import sys
    if sys.argv[1:]==['transfer']:transfer()
    elif len(sys.argv)==3 and sys.argv[1]=='collect':collect(sys.argv[2])
    else:raise SystemExit('collect LOG')
