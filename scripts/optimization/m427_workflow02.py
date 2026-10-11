"""Strict two-half saved software result; no performance or hardware advancement."""
import base64,hashlib,json,math,re
from pathlib import Path
from m351_workflow import ROOT,BASE,atomic,encoded,sha,sync
PKG=BASE/'candidates/M427-half-ranges-software-01'
OUT=BASE/'runs/M427-half-software-board-01/BOARD_RESULT.json'

def check(r):
    plan=json.loads((PKG/'PLAN.json').read_bytes())
    baseline=json.loads((BASE/'runs/M426-range-software-board-02/BOARD_RESULT.json').read_bytes())
    if r['gate_level']!='CPU-only-two-half-visual-MLP-screen' or r['manifest_sha256']!=sha(PKG/'PACKAGE_MANIFEST.json') or type(r['gate_return_code']) is not int or r['selected_layers']!=list(range(2,24)):raise ValueError('Scope/identity/rc differs')
    for key in ('overlay_loaded','dma_allocations','fpga_transactions','language_forward_calls','temperature_measurement_enabled','performance_pass','formal_promotion_allowed','task_screen_pass','task_screen_recorded','numerical_hardware_proven'):
        if key not in r or r[key] not in (False,0):raise ValueError('Forbidden scope '+key)
    if r['status']=='FAIL_M427_HALF_RANGE_SCREEN':
        if r['gate_return_code']!=1 or not r['errors']:raise ValueError('Original failure absent')
        return r
    if r['status'] not in ('PASS_M427_HALF_FEATURES_TASK_PENDING','REJECT_M427_BOTH_HALF_RANGES') or r['gate_return_code'] or r['errors']:raise ValueError('Unknown/inconsistent completed verdict')
    if r['visual_forward_calls']!=2 or r['original_visual_forward_calls']!=0 or r['source_identities_verified']!=49 or r['targets']!=baseline['targets'] or r['prefix_topology']!=baseline['prefix_topology']:raise ValueError('Original objects/topology differs')
    for key in ('saved_original_all24_boundaries_verified','original_reference_pass','software_screen_completed','bindings_restored','visual_owner_closed','no_pynq_import','boot_unchanged','cmdline_unchanged'):
        if r.get(key) is not True:raise ValueError('Incomplete lifecycle/reference '+key)
    if r['baseline_source_sha256']!=plan['baseline_raw_sha256'] or r['original_visual']!=baseline['original_visual'] or r['preprocessed']!=baseline['preprocessed']:raise ValueError('Saved original baseline differs')
    if r['backend_before']!=r['backend_after'] or not r['CPU_store_after']['cache_within_budget'] or r['release_preflight']['status']!='READY_FOR_BOARD_PREFLIGHT':raise ValueError('Backend/cache/assets differ')
    if r['weight_windows']!=plan['windows'] or len(r['ranges'])!=2 or len(r['retained_features'])!=2:raise ValueError('Two complete halves/weight windows required')
    passes=[]
    for number,(row,spec) in enumerate(zip(r['ranges'],plan['candidate_ranges'])):
        if row['name']!=spec['name'] or row['selected_layers']!=spec['selected_layers'] or row['logical_reference_calls']!=286 or row['peak_live_layer_scopes']!=1:raise ValueError('Frozen half order/geometry differs')
        if set(row['reference_batches'])!=set(map(str,spec['selected_layers'])):raise ValueError('All11 selected layers required')
        attempts=0
        for index in spec['selected_layers']:
            parts=row['reference_batches'][str(index)]
            if set(parts)!={'fc1','fc2'}:raise ValueError('Both MLP Linears required')
            for part,batches in parts.items():
                c=plan['chains'][str(index)][part]
                if len(batches)!=13:raise ValueError('Complete13 T32 batches required')
                for n,b in enumerate(batches):
                    if b['start']!=32*n or b['rows']!=(32 if n<12 else 8) or b['input_bytes']!=c['input_bytes'] or b['output_bytes']!=c['output_bytes'] or b['logical_calls']!=1:raise ValueError('Frozen T32 partition differs')
                    first,last=b['initial_shift'],b['selected_shift']
                    if type(first) is not int or type(last) is not int or not 0<=last<=first<=6 or b['attempted_shifts']!=list(range(first,last-1,-1)) or b['physical_reference_attempts']!=len(b['attempted_shifts']):raise ValueError('Adaptive retry policy differs')
                    attempts+=b['physical_reference_attempts']
                    if any(not re.fullmatch('[0-9a-f]{64}',b[k]) for k in ('packet_sha256','raw_sha256')):raise ValueError('Full reference wire identities absent')
        if attempts!=row['physical_reference_attempts'] or attempts<286:raise ValueError('Physical reference accounting differs')
        if [x['layer'] for x in row['boundary_comparison']]!=list(range(24)):raise ValueError('Complete24 boundary observations required')
        for index,boundary in enumerate(row['boundary_comparison']):
            if boundary['original']!=baseline['boundary_comparison'][index]['original']:raise ValueError('Fixed original boundary tensor differs')
            if boundary['candidate']['shape']!=[392,1024] or boundary['candidate']['dtype']!='float32' or boundary['candidate']['bytes']!=1605632 or not re.fullmatch('[0-9a-f]{64}',boundary['candidate']['sha256']):raise ValueError('Full finite boundary geometry differs')
            m=boundary['metrics']
            if m['shape']!=[392,1024] or any(not math.isfinite(m[k]) for k in ('relative_l2','cosine','min_token_cosine','RMSE','max_abs')):raise ValueError('Finite cumulative boundary metrics absent')
            if index<spec['selected_layers'][0] and boundary['candidate']!=boundary['original']:raise ValueError('Untouched prefix changed')
        tensor=row['candidate_visual']
        if tensor['shape']!=[98,2560] or tensor['dtype']!='float32' or tensor['bytes']!=1003520 or not re.fullmatch('[0-9a-f]{64}',tensor['sha256']):raise ValueError('Full candidate feature identity absent')
        saved=row['saved_feature']
        if saved!=r['retained_features'][number] or saved['path']!=spec['name']+'_candidate_visual.npy' or saved['bytes']!=1003648 or not re.fullmatch('[0-9a-f]{64}',saved['sha256']):raise ValueError('Saved candidate feature file differs')
        q=row['full_visual_quality'];m=q['metrics']
        if q['thresholds']!=plan['feature_thresholds'] or q['semantic_accuracy_proven'] or m['shape']!=[98,2560] or any(not math.isfinite(m[k]) for k in ('relative_l2','cosine','min_token_cosine','RMSE','max_abs')):raise ValueError('Unchanged finite final feature criteria required')
        passed=m['relative_l2']<=.02 and m['cosine']>=.999 and m['min_token_cosine']>=.995
        if type(row['feature_screen_pass']) is not bool or row['feature_screen_pass']!=passed or q['feature_screen_pass']!=passed:raise ValueError('Frozen half feature verdict differs')
        if passed:passes.append(row['name'])
    if r['feature_pass_ranges']!=passes or type(r['feature_screen_pass']) is not bool or r['feature_screen_pass']!=bool(passes) or (r['status']=='PASS_M427_HALF_FEATURES_TASK_PENDING')!=bool(passes):raise ValueError('Whole screen verdict differs')
    if r['elapsed_s_diagnostic_not_performance']>plan['budget_seconds']+60:raise ValueError('Frozen diagnostic budget exceeded')
    return r

def decode(log):
    hashes=re.findall(r'(?m)^M427_RESULT_SHA256=([0-9a-f]{64})\s*$',log);codes=re.findall(r'(?m)^M427_SAVED_GATE_RC=([01])\s*$',log)
    chunks=re.findall(r'(?m)^M427_RESULT_CHUNK=(\d+)/(\d+):([A-Za-z0-9+/=]+)\s*$',log)
    if len(hashes)!=1 or len(codes)!=1 or not chunks or len(chunks)!=int(chunks[0][1]):raise ValueError('Incomplete/duplicate export')
    parts=[]
    for i,(index,total,b64) in enumerate(chunks):
        p=base64.b64decode(b64,validate=True)
        if int(index)!=i or int(total)!=len(chunks) or not 0<len(p)<=900:raise ValueError('Chunk order/size differs')
        parts.append(p)
    raw=b''.join(parts);digest=hashlib.sha256(raw).hexdigest()
    if len(raw)>2<<20 or digest!=hashes[0]:raise ValueError('Whole raw SHA/budget differs')
    r=check(json.loads(raw))
    if r['gate_return_code']!=int(codes[0]):raise ValueError('Original rc differs')
    done=re.findall(r'M427_DONE gate_rc=(\d+) export_rc=(\d+)',log)
    if done and done!=[(codes[0],'0')]:raise ValueError('Main/export rc differs')
    return digest,raw,r,len(chunks)

def collect(log):
    digest,raw,r,chunks=decode(Path(log).read_text(encoding='utf-8-sig'));atomic(OUT,raw,immutable=True)
    note=f'## M427 固定两半区软件筛查（2026-10-06）\n\n原SHA {digest}，{chunks}×≤900B完整回收；{r["status"]}、rc{r["gate_return_code"]}。固定2–12/13–23各11层，0原版视觉重算/语言/Overlay/DMA/PL/测温；feature通过范围{r["feature_pass_ranges"]}，任务尚未执行，不解锁硬件性能。原M426全22层拒绝及两层M425性能关闭裁决不改。'
    atomic(OUT.with_name('REPORT.md'),('# M427 两半区软件筛查\n\n'+note+'\n\n~~~json\n'+json.dumps([dict(name=x['name'],selected_layers=x['selected_layers'],quality=x['full_visual_quality']) for x in r['ranges']],ensure_ascii=False,indent=2)+'\n~~~\n').encode('utf-8'),immutable=True)
    sync('latest_m427_half_software_board',dict(status=r['status'],result=OUT.relative_to(ROOT).as_posix(),sha256=digest,manifest_sha256=r['manifest_sha256'],feature_pass_ranges=r['feature_pass_ranges'],task_screen_pass=False,hardware_visual_timing_unlocked=False,performance_pass=False),note)
    print('M427_RESULT_SYNC',digest,r['status'])

def transfer():
    m=json.loads((PKG/'PACKAGE_MANIFEST.json').read_bytes());folder=ROOT/'tmp/m42702';receipts=[]
    for name in ['PACKAGE_MANIFEST.json']+[x['path'] for x in m['files']]:
        size=(PKG/name).stat().st_size;count=(size+899)//900;prefix='upload_'+name.replace('.','_')
        final=(folder/(prefix+'_final.log')).read_text(encoding='utf-8-sig')
        if 'M212_CHUNKED_FILE_PASS' not in final or sha(PKG/name) not in final:raise ValueError('Transfer whole SHA missing')
        logs=sorted(folder.glob(prefix+'_chunk_*.log'))
        if len(logs)!=count:raise ValueError('Transfer count differs')
        for i,p in enumerate(logs,1):
            if not re.search(r'M212_CHUNK_PASS\s+'+str(i)+r'\s+'+str(count)+r'\s+'+str(min(i*900,size))+r'\s',p.read_text(encoding='utf-8-sig')):raise ValueError('Transfer order/bytes differs')
        receipts.append(dict(path=name,sha256=sha(PKG/name),chunks=count))
    if '__M427_SYNTAX_RC_0__' not in (folder/'syntax.log').read_text(encoding='utf-8-sig'):raise ValueError('Board bash-n receipt missing')
    r=dict(status='PASS_M427_MANIFEST_FIRST_HASHED_TRANSFER',manifest_sha256=sha(PKG/'PACKAGE_MANIFEST.json'),receipts=receipts,software_gate_started=False)
    p=BASE/'runs/M427-half-transfer-01/RESULT.json';atomic(p,encoded(r),immutable=True)
    sync('latest_m427_half_transfer',dict(status=r['status'],result=p.relative_to(ROOT).as_posix(),sha256=sha(p),manifest_sha256=r['manifest_sha256']),f'## M427 两半区包完整传输（2026-10-06）\n\nSHA {sha(p)}；manifest-first900B逐文件完整SHA/回执及bash-n通过，未执行。下一步同终端sudo后一次执行两个固定半区，仅PS，不重复原版视觉。')
    print('M427_TRANSFER_SYNC',sha(p))
if __name__=='__main__':
    import sys
    if sys.argv[1:]==['transfer']:transfer()
    elif len(sys.argv)==3 and sys.argv[1]=='collect':collect(sys.argv[2])
    else:raise SystemExit('transfer | collect LOG')
