"""Strict saved-only combination evidence, original A and dynamic oracle kept distinct."""
import base64,hashlib,json,math,re
from pathlib import Path
from m351_workflow import ROOT,BASE,HERE,atomic,encoded,sha,sync
from m414_policy import POLICY,MAIN_SIZES,MINIMAL_SIZES
from m414_quality import THRESHOLDS
from board_safety import safe_to_release
PKG=BASE/'candidates/M420-layers12-13-full-visual-02'

def transfer(folder=ROOT/'tmp/m42001',save=True):
    m=json.loads((PKG/'PACKAGE_MANIFEST.json').read_bytes());receipts=[]
    for name in ['PACKAGE_MANIFEST.json']+[x['path'] for x in m['files']]:
        prefix='upload_'+name.replace('.','_');size=(PKG/name).stat().st_size;count=(size+899)//900
        t=(folder/(prefix+'_final.log')).read_text(encoding='utf-8-sig')
        if 'M212_CHUNKED_FILE_PASS' not in t or sha(PKG/name) not in t:raise ValueError('Final SHA missing')
        chunks=sorted(folder.glob(prefix+'_chunk_*.log'))
        if len(chunks)!=count:raise ValueError('Missing chunk receipt')
        for i,p in enumerate(chunks,1):
            if not re.search(r'M212_CHUNK_PASS\s+'+str(i)+r'\s+'+str(count)+r'\s+'+str(min(i*900,size))+r'\s',p.read_text(encoding='utf-8-sig')):raise ValueError('Chunk receipt differs')
        receipts.append(dict(path=name,sha256=sha(PKG/name),chunks=count))
    if '__M420_SYNTAX_RC_0__' not in (folder/'syntax.log').read_text(encoding='utf-8-sig'):raise ValueError('Bash syntax receipt missing')
    v=dict(status='PASS_M420_TRANSFER',manifest_sha256=sha(PKG/'PACKAGE_MANIFEST.json'),files=receipts,board_run=False)
    if save:
        out=BASE/'runs/M420-combination-transfer-01/RESULT.json';atomic(out,encoded(v),immutable=True)
        sync('latest_m420_combination_transfer',dict(status=v['status'],result=out.relative_to(ROOT).as_posix(),sha256=sha(out),manifest_sha256=v['manifest_sha256']),f'## M420 双层视觉包传输（2026-10-06）\n\nSHA {sha(out)}；manifest-first/900B全部回执、逐SHA和bash-n通过，尚未执行；仅12＋13组合三视觉/0语言/0性能。')
    return v

def validate(r):
    plan=json.loads((PKG/'PLAN.json').read_bytes())
    if r['manifest_sha256']!=sha(PKG/'PACKAGE_MANIFEST.json') or r['gate_level']!='layers12-13-full-visual-feature-quality' or r['build_id']!='0x4D333537' or type(r['gate_return_code']) is not int or r['gate_return_code'] not in (0,1):raise ValueError('Gate identity differs')
    if r['selected_layers']!=[12,13] or r['language_forward_calls']!=0 or any(r[k] is not False for k in ('full_model','video','promoted','expanded_24_layers','performance_pass','semantic_quality_proven')):raise ValueError('Scope expanded')
    if r['status'].startswith('FAIL_'):
        if r['gate_return_code']!=1 or not r['errors']:raise ValueError('Incomplete failure')
        return
    if r['status']!='PASS_M420_LAYERS12_13_FULL_VISUAL_FEATURE_QUALITY' or r['gate_return_code'] or r['errors'] or r['visual_forward_calls']!=3:raise ValueError('Unknown/incomplete PASS')
    for k in ('package_verified','original_reference_before_overlay','original_reference_pass','numerical_pass','feature_quality_pass','bindings_restored','PS_owner_closed','safe_buffers_released','stable_restored','DMA_allocator_restored','DMA_sealed_after_main','software_PL_complete_features_exact','boot_unchanged','cmdline_unchanged'):
        if r[k] is not True:raise ValueError('Required PASS missing:'+k)
    if r['unsafe_dma_buffers_retained'] or r['unexpected_DMA_requests'] or r['source_identities_verified']!=49 or r['prerequisites_verified']!=plan['board_prerequisites']:raise ValueError('Unsafe/prerequisite scope differs')
    component=r['component'];process=r['component_process']
    cp=json.loads((ROOT/'tmp/m42002/component/RESULT.json').read_bytes())
    if component!=cp['component'] or not process['separate_process'] or not process['parent_state_unchanged'] or process['return_code'] or process['before']!=process['after']:raise ValueError('Component isolation differs')
    expected=json.loads((PKG/'EXPECTED_VISUAL.json').read_bytes())
    if r['preprocessed']!=expected['preprocessed'] or r['original_visual']!=expected['visual'] or r['candidate_visual']!=r['software_visual'] or r['candidate_captures']!=r['software_captures']:raise ValueError('Original/dynamic full features differ')
    for i in ('12','13'):
        refpath=ROOT/plan['reference_results'][i];ref=json.loads(refpath.read_bytes())
        if r['original_captures'][i]!=ref['capture_tensors'] or r['target_resolution'][i]!=ref['target_resolution'] or r['target_matrices'][i]!=ref['target_matrices']:raise ValueError('Original target/input differs')
    if r['layer13_input_changed'] is not (r['software_captures']['13']['input']!=r['original_captures']['13']['input']):raise ValueError('Changed input observation differs')
    ids=json.loads((BASE/'candidates/M417-layer13-saved-reference-02/M348_SOURCE_IDENTITIES.json').read_bytes());identities={x['path']:x['sha256'] for x in ids['files']}
    if set(r['resolved_modules'])!=set(plan['resolved_module_names']) or any(identities[x['path']]!=x['sha256'] for x in r['resolved_modules'].values()):raise ValueError('Resolved frozen source differs')
    if r['backend_before']!=r['backend_after'] or r['release_preflight']['status']!='READY_FOR_BOARD_PREFLIGHT' or r['CPU_store_after']['uncached_decode_calls']-r['CPU_store_before']['uncached_decode_calls']!=208 or r['CPU_store_after']['cache_entries']!=26 or r['CPU_store_after']['cache_bytes']!=66699264 or not r['CPU_store_after']['cache_within_budget']:raise ValueError('Backend/cache/CPU restore differs')
    quality=r['full_visual_quality'];metrics=quality['metrics']
    if quality['thresholds']!=THRESHOLDS or not quality['feature_screen_pass'] or quality['semantic_accuracy_proven'] or metrics['shape']!=[98,2560] or not all(type(metrics[k]) in (float,int) and math.isfinite(metrics[k]) for k in ('relative_l2','cosine','min_token_cosine','RMSE','max_abs')):raise ValueError('Invalid final screen')
    if not 0<=metrics['relative_l2']<=.02 or not .999<=metrics['cosine']<=1.000000000001 or not .995<=metrics['min_token_cosine']<=1.000000000001 or metrics['RMSE']<0 or metrics['max_abs']<0:raise ValueError('Final screen rejected')
    from m407_mlp_contract import local_screen
    if set(r['local_quality'])!={'12','13'} or any(not local_screen(m) for q in r['local_quality'].values() for m in q.values()):raise ValueError('Local screen rejected')
    artifacts=r['retained_visual_features']
    if [x['path'] for x in artifacts]!=['original_visual.npy','candidate_visual.npy'] or [x['tensor'] for x in artifacts]!=[r['original_visual'],r['candidate_visual']] or any(x['file_bytes']!=1003648 or not re.fullmatch('[0-9a-f]{64}',x['file_sha256']) for x in artifacts):raise ValueError('Saved feature identities differ')
    if r['full_wire_reference_batches_exact']!=52 or len(r['PL_rows'])!=52 or r['physical_transactions_started']!=54 or len(r['transactions'])!=2:raise ValueError('Full transaction count differs')
    ordered=[]
    for index in (12,13):
        identities=r['software_wire_identities'][str(index)];ordered.extend(dict(x,layer=index) for x in identities)
        if len(identities)!=26:raise ValueError('Per-layer wire count differs')
        for part in ('fc1','fc2'):
            software=r['software_batches'][str(index)][part];pl=r['PL_batches'][str(index)][part]
            if len(software)!=13 or [x['start'] for x in software]!=list(range(0,392,32)) or [x['rows'] for x in software]!=[32]*12+[8] or any(x['physical_reference_attempts']!=1 for x in software):raise ValueError('OriginalT32 or pre-resource retry stop differs')
            if pl!=[{k:x[k] for k in ('start','rows','initial_shift','attempted_shifts','selected_shift')}|{'physical_calls':1} for x in software]:raise ValueError('Dynamic batching/retry differs')
    keys=('layer','part','start','shift','input_bytes','output_bytes','packet_sha256','raw_sha256')
    for row,want in zip(r['PL_rows'],ordered):
        if any(row[k]!=want[k] for k in keys) or not safe_to_release(row['completed_snapshot']) or row['completed_snapshot']['ap_return']!=0x4d333537:raise ValueError('Full dynamic wire/completion differs')
    if [(x['layer'],x['part']) for x in r['staging']]!=[(12,'fc1'),(12,'fc2'),(13,'fc1'),(13,'fc2')] or sum(x['bytes'] for x in r['staging'])!=8912896:raise ValueError('Shared seven-buffer staging differs')
    allocations=r['allocations'];releases=[];start=0
    if len(allocations)!=19:raise ValueError('Exact planned allocation count differs')
    for count in (6,7,6):releases.extend(reversed(allocations[start:start+count]));start+=count
    if r['releases']!=releases or sum(x['bytes'] for x in allocations[6:13])!=3440656 or r['admission_policy']!=POLICY:raise ValueError('Owner release/payload differs')
    groups=[dict(label=label,sizes=list(sizes),attempted=len(sizes),returned=len(sizes),complete=True) for label,sizes in zip(['candidate-legal-build-id','completeMLP-seven','stable-restored-build-id'],[MINIMAL_SIZES,MAIN_SIZES,MINIMAL_SIZES])]
    if r['DMA_admission_groups']!=groups:raise ValueError('DMA seal group differs')
    memory_labels=['allocated:candidate-legal-build-id','before-submit:candidate-legal-build-id','allocated:completeMLP-seven']+['MLP-before-submit']*52+['allocated:stable-restored-build-id','before-submit:stable-restored-build-id']
    ps_labels=['after-constructor']
    for phase in ('original-full-visual','software-full-visual','PL-full-visual'):
        ps_labels+=['before-'+phase]+[phase+':layer'+str(i)+':'+edge for i in range(24) for edge in ('before','after')]+['after-'+phase]
    if [x['label'] for x in r['memory']]!=memory_labels or [x['label'] for x in r['PS_checkpoints']]!=ps_labels or [x['recovery'] for x in r['memory']]!=[False]*55+[True]*2 or any(x['recovery'] for x in r['PS_checkpoints']):raise ValueError('Complete phase memory coverage differs')
    for x in r['memory']+r['PS_checkpoints']:
        growth=max(0,x['VmRSS']-r['memory_after_constructor']['VmRSS']);required=(64<<20)+(0 if x['recovery'] else max(0,(768<<20)-growth))
        if x['admission_policy']!=POLICY['name'] or x['required_cma_free_bytes'] is not None or type(x['CmaFree']) is not int or x['CmaFree']<0 or x['RSS_growth_bytes']!=growth or x['required_MemAvailable_bytes']!=required or x['MemAvailable']<required or (not x['recovery'] and growth>768<<20):raise ValueError('Actual ordinary memory budget differs')
    if not safe_to_release(r['final_snapshot']) or r['final_snapshot']['ap_return']!=0x4d395832 or not 0<r['elapsed_s_diagnostic_not_performance']<=840:raise ValueError('Stable restoration/budget differs')

def decode(t):
    hashes=re.findall(r'(?m)^M420_RESULT_SHA256=([0-9a-f]{64})\s*$',t);codes=re.findall(r'(?m)^M420_SAVED_GATE_RC=([01])\s*$',t);chunks=re.findall(r'(?m)^M420_RESULT_CHUNK=(\d+)/(\d+):([A-Za-z0-9+/=]+)\s*$',t)
    if len(hashes)!=1 or len(codes)!=1 or not chunks or len(chunks)!=int(chunks[0][1]):raise ValueError('Incomplete/duplicate result')
    pieces=[]
    for i,(index,total,data) in enumerate(chunks):
        p=base64.b64decode(data,validate=True)
        if int(index)!=i or int(total)!=len(chunks) or not 0<len(p)<=900:raise ValueError('Chunk order/size differs')
        pieces.append(p)
    raw=b''.join(pieces);digest=hashlib.sha256(raw).hexdigest();r=json.loads(raw);rc=int(codes[0]);validate(r)
    if digest!=hashes[0] or r['gate_return_code']!=rc:raise ValueError('SHA/original rc differs')
    done=re.findall(r'M420_DONE gate_rc=(\d+) export_rc=(\d+)',t)
    if done and done!=[(str(rc),'0')]:raise ValueError('Gate/export rc differs')
    return digest,raw,r,len(chunks)
def collect(log,out=None,sync_function=sync):
    digest,raw,r,count=decode(Path(log).read_text(encoding='utf-8-sig'));out=out or BASE/'runs/M420-combination-board-01/BOARD_RESULT.json';atomic(out,raw,immutable=True)
    report=f'# M420 第12＋13层完整视觉组合\n\n{r["status"]}，原rc {r["gate_return_code"]}，SHA {digest}。\n\n固定原版A→两层动态软件参考→PL组合，实际视觉{r["visual_forward_calls"]}次、语言0次；只选择两层MLP，其他路径保持。时间含诊断/软件参考，不是性能。特征筛选不是语义准确率。\n\n```json\n'+json.dumps(r.get('full_visual_quality',r['errors']),ensure_ascii=False,indent=2)+'\n```\n'
    atomic(out.with_name('REPORT.md'),report.encode('utf-8'),immutable=True)
    sync_function('latest_m420_combination_board',dict(status=r['status'],result=out.relative_to(ROOT).as_posix(),sha256=digest,manifest_sha256=r['manifest_sha256'],build_id=r['build_id'],feature_quality_pass=r['feature_quality_pass'],semantic_quality_proven=False,performance_pass=False,expanded_24_layers=False),f'## M420 两层完整视觉组合门禁（2026-10-06）\n\n原SHA {digest}，{count}个≤900B严格回收，rc{r["gate_return_code"]}；{r["status"]}。固定原版A及12＋13动态软件参考/PL完整特征、全部52 wire和受控七DMA，0语言/性能/24层。失败只本级闭合；收集失败只补原字节，不重跑视觉。')
    print('M420_RESULT_SYNC',digest,count);return r
if __name__=='__main__':
    import sys
    if sys.argv[1:]==['transfer']:transfer()
    elif len(sys.argv)==3 and sys.argv[1]=='collect':collect(sys.argv[2])
    else:raise SystemExit('transfer | collect LOG')
