"""Exact late11 numerical evidence and UART collection, no gate execution."""
import base64,collections,hashlib,json,math,re
from pathlib import Path
from m351_workflow import ROOT,BASE,atomic,encoded,sha,sync
PKG=BASE/'candidates/M429-late11-visual-PL-numeric-03'
OUT=BASE/'runs/M429-late11-visual-PL-board-02/BOARD_RESULT.json'

def check(r):
    plan=json.loads((PKG/'PLAN.json').read_bytes());software=json.loads((BASE/'runs/M427-half-software-board-01/BOARD_RESULT.json').read_bytes())
    accepted=next(x for x in software['ranges'] if x['name']=='late_13_23')
    if r['gate_level']!='late11-complete-visual-PL-numerical' or r['manifest_sha256']!=sha(PKG/'PACKAGE_MANIFEST.json') or type(r['gate_return_code']) is not int or r['gate_return_code'] not in (0,1) or r['selected_layers']!=list(range(13,24)):raise ValueError('Scope/manifest/rc differs')
    for k in ('temperature_measurement_enabled','performance_pass','formal_promotion_allowed','language_forward_calls','original_visual_forward_calls'):
        if r.get(k) not in (False,0):raise ValueError('Forbidden gate scope '+k)
    if r['status'] in ('FAIL_M429_LATE11_VISUAL_NUMERICAL','FAIL_UNSAFE_RETAINED'):
        if r['gate_return_code']!=1 or not r['errors'] or r['numerical_hardware_proven']:raise ValueError('Failure evidence incomplete')
        return r
    if r['status']!='PASS_M429_LATE11_COMPLETE_VISUAL_PL_NUMERICAL' or r['gate_return_code'] or r['errors'] or r['build_id']!='0x4D333537':raise ValueError('Completed numerical status differs')
    bootstrap=r['component_bootstrap']
    prior=json.loads((BASE/'runs/M429-isolated-bootstrap-board-01/BOARD_RESULT.json').read_bytes())
    if r['isolated_bootstrap_source_sha256']!=plan['isolated_bootstrap_source_sha256'] or bootstrap!=prior['bootstrap']:raise ValueError('Passed isolated bootstrap identity differs')
    for k in ('overlay_loaded','numerical_hardware_proven','bindings_restored','visual_owner_closed','safe_buffers_released','stable_restored','DMA_allocator_restored','DMA_sealed_after_main','original_reference_pass','saved_original_all24_boundaries_verified','CPU_component_before_Overlay','feature_screen_pass','boot_unchanged','cmdline_unchanged'):
        if r.get(k) is not True:raise ValueError('Missing full numerical/lifecycle '+k)
    if r['unsafe_dma_buffers_retained'] or r['unexpected_DMA_requests'] or r['visual_forward_calls']!=1 or r['matched_wire_batches']!=286 or r['peak_live_layer_scopes']!=1:raise ValueError('Numerical scope/lifecycle count differs')
    if r['source_identities_verified']!=49 or r['targets']!=software['targets'] or r['prefix_topology']!=software['prefix_topology'] or r['preprocessed']!=software['preprocessed']:raise ValueError('Frozen source/input/topology differs')
    if r['software_reference_source_sha256']!=plan['M427_raw_sha256'] or r['task_source_sha256']!=plan['M428_raw_sha256'] or r['baseline_source_sha256']!=plan['M426_raw_sha256'] or r['hardware_closure_sha256']!=plan['hardware_closure_sha256']:raise ValueError('Saved references/hardware identity differs')
    if r['original_visual']!=software['original_visual'] or r['candidate_visual']!=accepted['candidate_visual'] or r['full_visual_quality']!=accepted['full_visual_quality']:raise ValueError('Complete saved feature/criteria differs')
    if r['boundary_comparison']!=accepted['boundary_comparison']:raise ValueError('All24 complete boundary hashes/metrics differ')
    if r['backend_before']!=r['backend_after'] or not r['CPU_store_after']['cache_within_budget'] or r['release_preflight']['status']!='READY_FOR_BOARD_PREFLIGHT':raise ValueError('Original backend/cache/assets drift')
    if r['weight_windows']!=plan['windows'] or len(r['staging'])!=22:raise ValueError('All selected original W4 windows required')
    if [(x['layer'],x['part'],x['bytes']) for x in r['staging']]!=[(i,p,4*557056) for i in range(13,24) for p in ('fc1','fc2')]:raise ValueError('Staging order/byte counts differ')
    if len(r['PL_rows'])!=286 or set(r['PL_batches'])!=set(map(str,range(13,24))):raise ValueError('Complete PL batches required')
    position=0
    from board_safety import safe_to_release
    def complete(s,build):
        return (safe_to_release(s) and type(s.get('ap_return')) is int and s['ap_return']==build
                and all(s.get(k) is False for k in ('mm2s_error','s2mm_error'))
                and all(s.get(k)=='' for k in ('kernel_read_error','return_read_error','dma_read_error')))
    for i in range(13,24):
        if set(r['PL_batches'][str(i)])!={'fc1','fc2'}:raise ValueError('Both full Linear calls required')
        for p in ('fc1','fc2'):
            batches=r['PL_batches'][str(i)][p]
            if len(batches)!=13:raise ValueError('Full original T32 partition required')
            for n,(batch,ref) in enumerate(zip(batches,accepted['reference_batches'][str(i)][p])):
                if batch!={k:ref[k] for k in ('start','rows','initial_shift','attempted_shifts','selected_shift')}|{'physical_calls':1}:raise ValueError('Actual adaptive shift/row accounting differs')
                row=r['PL_rows'][position];position+=1
                wanted=dict(layer=i,part=p,start=32*n,shift=ref['selected_shift'],input_bytes=ref['input_bytes'],output_bytes=ref['output_bytes'],packet_sha256=ref['packet_sha256'],raw_sha256=ref['raw_sha256'])
                if {k:row[k] for k in wanted}!=wanted or type(row['wait_ns']) is not int or row['wait_ns']<0 or not complete(row['completed_snapshot'],0x4D333537):raise ValueError('Complete PL wire/return/DMA completion differs')
    if r['physical_transactions_started']!=288 or r['fpga_transactions']!=288 or len(r['transactions'])!=2:raise ValueError('Minimal/MLP physical count differs')
    for tx,label,build in zip(r['transactions'],('candidate-legal-build-id','stable-restored-build-id'),(0x4D333537,0x4D395832)):
        if tx['label']!=label or tx['build_id']!=hex(build) or tx['full_output_exact'] is not True or not complete(tx['completed_snapshot'],build):raise ValueError('Legal sameOverlay/restore transaction incomplete')
    groups=r['DMA_admission_groups']
    sizes=([144]*4+[2576,4096],plan['main_DMA_sizes'],[144]*4+[2576,4096])
    if len(groups)!=3:raise ValueError('Three planned owner groups required')
    for group,label,size in zip(groups,('candidate-legal-build-id','completeMLP-seven','stable-restored-build-id'),sizes):
        if group!={'label':label,'sizes':size,'attempted':len(size),'returned':len(size),'complete':True}:raise ValueError('Exact allocator admission groups incomplete')
    if r['dma_allocations']!=19 or len(r['allocations'])!=19 or len(r['releases'])!=19:raise ValueError('All nineteen planned allocations/releases required')
    if [x['bytes'] for x in r['allocations']]!=sum((list(x) for x in sizes),[]):raise ValueError('Actual original DMA byte geometry differs')
    identity=lambda rows:collections.Counter((x['label'],x['bytes'],x['address']) for x in rows)
    if identity(r['allocations'])!=identity(r['releases']):raise ValueError('Owner release identities differ')
    if not complete(r['final_snapshot'],0x4D395832):raise ValueError('Final stable legal completion unproven')
    expected=dict(accepted['saved_feature'],path='late_13_23_PL_visual.npy')
    if r['retained_features']!=[expected]:raise ValueError('Complete saved PL feature file identity differs')
    component=r['component']
    if component['complete_wire_batches']!=286 or not component['restored'] or len(component['negative_checks'])!=20 or not component['fake_PL_submit'] or not component['no_DMA_or_Overlay']:raise ValueError('Actual CPU-only scope fixture incomplete')
    if r['elapsed_s_diagnostic_not_performance']>plan['budget_seconds']+60:raise ValueError('Bounded numerical budget exceeded')
    return r

def decode(log):
    hashes=re.findall(r'(?m)^M429_RESULT_SHA256=([0-9a-f]{64})\s*$',log);codes=re.findall(r'(?m)^M429_SAVED_GATE_RC=([01])\s*$',log)
    chunks=re.findall(r'(?m)^M429_RESULT_CHUNK=(\d+)/(\d+):([A-Za-z0-9+/=]+)\s*$',log)
    if len(hashes)!=1 or len(codes)!=1 or not chunks or len(chunks)!=int(chunks[0][1]):raise ValueError('Incomplete/duplicate export')
    parts=[]
    for i,(index,total,data) in enumerate(chunks):
        part=base64.b64decode(data,validate=True)
        if int(index)!=i or int(total)!=len(chunks) or not 0<len(part)<=900:raise ValueError('Chunk order/size differs')
        parts.append(part)
    raw=b''.join(parts);digest=hashlib.sha256(raw).hexdigest()
    if not 0<len(raw)<=2<<20 or digest!=hashes[0]:raise ValueError('Whole raw SHA/budget differs')
    r=check(json.loads(raw))
    if r['gate_return_code']!=int(codes[0]):raise ValueError('Original rc differs')
    done=re.findall(r'M429_DONE gate_rc=(\d+) export_rc=(\d+)',log)
    if done and done!=[(codes[0],'0')]:raise ValueError('Main/export rc differs')
    return digest,raw,r,len(chunks)

def collect(log):
    digest,raw,r,chunks=decode(Path(log).read_text(encoding='utf-8-sig'));atomic(OUT,raw,immutable=True)
    passed=r['status']=='PASS_M429_LATE11_COMPLETE_VISUAL_PL_NUMERICAL'
    note=f'## M429 后11层完整视觉PL数值（2026-10-06）\n\n原SHA {digest}，{chunks}×≤900B严格回收，{r["status"]}、rc{r["gate_return_code"]}。仅一次完整视觉，13–23的两个MLP Linear，其余路径不改；不重复原版/软件视觉，不运行语言，不测温。完整数值PASS {passed}，此结果不是性能。稳定恢复{r["stable_restored"]}、安全释放{r["safe_buffers_released"]}；失败仅同级调查。'
    sync('latest_m429_late11_visual_PL_board',dict(status=r['status'],result=OUT.relative_to(ROOT).as_posix(),sha256=digest,manifest_sha256=r['manifest_sha256'],hardware_visual_numerics_pass=passed,hardware_visual_timing_unlocked=passed,full_request_timing_unlocked=False,performance_pass=False),note)
    print('M429_RESULT_SYNC',digest,r['status'])

def transfer():
    manifest=json.loads((PKG/'PACKAGE_MANIFEST.json').read_bytes());folder=ROOT/'tmp/m42904';receipts=[]
    for name in ['PACKAGE_MANIFEST.json']+[x['path'] for x in manifest['files']]:
        size=(PKG/name).stat().st_size;count=(size+899)//900;prefix='upload_'+name.replace('.','_')
        final=(folder/(prefix+'_final.log')).read_text(encoding='utf-8-sig')
        if 'M212_CHUNKED_FILE_PASS' not in final or sha(PKG/name) not in final:raise ValueError('Transfer whole SHA missing')
        logs=sorted(folder.glob(prefix+'_chunk_*.log'))
        if len(logs)!=count:raise ValueError('Transfer count differs')
        for i,p in enumerate(logs,1):
            if not re.search(r'M212_CHUNK_PASS\s+'+str(i)+r'\s+'+str(count)+r'\s+'+str(min(i*900,size))+r'\s',p.read_text(encoding='utf-8-sig')):raise ValueError('Transfer order/bytes differs')
        receipts.append(dict(path=name,sha256=sha(PKG/name),chunks=count))
    if '__M429_SYNTAX_RC_0__' not in (folder/'syntax.log').read_text(encoding='utf-8-sig'):raise ValueError('Board bash-n receipt missing')
    r=dict(status='PASS_M429_MANIFEST_FIRST_HASHED_TRANSFER',manifest_sha256=sha(PKG/'PACKAGE_MANIFEST.json'),receipts=receipts,hardware_gate_started=False)
    out=BASE/'runs/M429-late11-visual-transfer-02/RESULT.json';atomic(out,encoded(r),immutable=True)
    sync('latest_m429_late11_visual_transfer',dict(status=r['status'],result=out.relative_to(ROOT).as_posix(),sha256=sha(out),manifest_sha256=r['manifest_sha256']),f'## M429 视觉PL数值包完整传输（2026-10-06）\n\nSHA {sha(out)}；manifest-first逐文件900B SHA/顺序回执及bash-n通过，未执行。下一步同COM3授权一次真实视觉PL数值；不启动性能。')
    print('M429_TRANSFER_SYNC',sha(out))

if __name__=='__main__':
    import sys
    if sys.argv[1:]==['transfer']:transfer()
    elif len(sys.argv)==3 and sys.argv[1]=='collect':collect(sys.argv[2])
    else:raise SystemExit('transfer | collect LOG')
