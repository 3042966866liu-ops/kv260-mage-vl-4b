"""Strict saved-only final visual-feature quality and lifecycle collection."""
import base64,hashlib,json,math,re
from pathlib import Path
from m351_workflow import ROOT,BASE,HERE,atomic,encoded,sha,sync
from m414_quality import THRESHOLDS
from m414_policy import POLICY,MAIN_SIZES,MINIMAL_SIZES
from board_safety import safe_to_release
PKG=BASE/'candidates/M414-layer12-full-visual-01'

def transfer(folder=ROOT/'tmp/m41401',save=True):
    m=json.loads((PKG/'PACKAGE_MANIFEST.json').read_bytes());receipts=[]
    for name in ['PACKAGE_MANIFEST.json']+[x['path'] for x in m['files']]:
        prefix='upload_'+name.replace('.','_');size=(PKG/name).stat().st_size;count=(size+899)//900
        text=(folder/(prefix+'_final.log')).read_text(encoding='utf-8-sig')
        if 'M212_CHUNKED_FILE_PASS' not in text or sha(PKG/name) not in text:raise ValueError('Final SHA receipt missing')
        chunks=sorted(folder.glob(prefix+'_chunk_*.log'))
        if len(chunks)!=count:raise ValueError('Chunk receipt count differs')
        for i,p in enumerate(chunks,1):
            if not re.search(r'M212_CHUNK_PASS\s+'+str(i)+r'\s+'+str(count)+r'\s+'+str(min(i*900,size))+r'\s',p.read_text(encoding='utf-8-sig')):raise ValueError('Incomplete chunk receipt')
        receipts.append(dict(path=name,sha256=sha(PKG/name),chunks=count))
    if '__M414_SYNTAX_RC_0__' not in (folder/'syntax.log').read_text(encoding='utf-8-sig'):raise ValueError('Bash syntax receipt missing')
    v=dict(status='PASS_M414_MANIFEST_FIRST_TRANSFER',manifest_sha256=sha(PKG/'PACKAGE_MANIFEST.json'),files=receipts,hardware_gate_started=False)
    if save:
        p=BASE/'runs/M414-layer12-visual-transfer-01/RESULT.json';atomic(p,encoded(v),immutable=True)
        sync('latest_m414_layer12_visual_transfer',dict(status=v['status'],result=p.relative_to(ROOT).as_posix(),sha256=sha(p),manifest_sha256=v['manifest_sha256']),f'## M414 第12层完整视觉质量包传输（2026-10-06）\n\nSHA {sha(p)}；manifest-first全部900B回执、逐SHA及bash-n通过；仅准备一次原版/候选视觉前向，尚未执行，无语言或扩层。')
    return v

def decode(text):
    hashes=re.findall(r'(?m)^M414_RESULT_SHA256=([0-9a-f]{64})\s*$',text);codes=re.findall(r'(?m)^M414_SAVED_GATE_RC=([01])\s*$',text)
    chunks=re.findall(r'(?m)^M414_RESULT_CHUNK=(\d+)/(\d+):([A-Za-z0-9+/=]+)\s*$',text)
    if len(hashes)!=1 or len(codes)!=1 or not chunks or len(chunks)!=int(chunks[0][1]):raise ValueError('Incomplete/duplicate result')
    pieces=[]
    for i,(index,total,value) in enumerate(chunks):
        p=base64.b64decode(value,validate=True)
        if int(index)!=i or int(total)!=len(chunks) or not 0<len(p)<=900:raise ValueError('Chunk order/size differs')
        pieces.append(p)
    raw=b''.join(pieces);digest=hashlib.sha256(raw).hexdigest();r=json.loads(raw);rc=int(codes[0]);plan=json.loads((PKG/'PLAN.json').read_bytes())
    if digest!=hashes[0] or r['manifest_sha256']!=sha(PKG/'PACKAGE_MANIFEST.json') or r['gate_level']!='layer12-full-visual-feature-quality' or r['build_id']!='0x4D333537' or type(r['gate_return_code']) is not int or r['gate_return_code']!=rc:raise ValueError('Raw gate identity/rc differs')
    if any(r[k] is not False for k in ('full_model','video','promoted','expanded_24_layers','performance_pass','semantic_quality_proven')) or r['selected_layers']!=[12] or r['language_forward_calls']!=0 or r['samples'] or r['warmups'] or r['local_mlp_calls']!=0:raise ValueError('Scope expanded')
    done=re.findall(r'M414_DONE gate_rc=(\d+) export_rc=(\d+)',text)
    if done and done!=[(str(rc),'0')]:raise ValueError('Gate/export rc differs')
    if r['status']=='PASS_M414_LAYER12_FULL_VISUAL_FEATURE_QUALITY':
        process=r['component_process']
        if r['original_reference_before_overlay'] is not True or process['separate_process'] is not True or process['parent_state_unchanged'] is not True or process['return_code']!=0 or process['before']!=process['after'] or process['timeout_seconds']!=90:raise ValueError('Original boundary/component isolation not established')
        if set(process['before'])!={'rng_sha256','intraop','interop','dtype','inference'} or not re.fullmatch('[0-9a-f]{64}',process['before']['rng_sha256']) or any(not re.fullmatch('[0-9a-f]{64}',process[k]) for k in ('stdout_sha256','stderr_sha256')):raise ValueError('Actual parent-state or child output identity missing')
        if rc or r['errors'] or r['visual_forward_calls']!=2 or not all(r[k] is True for k in ('package_verified','numerical_pass','original_reference_pass','feature_quality_pass','bindings_restored','PS_owner_closed','safe_buffers_released','stable_restored','boot_unchanged','cmdline_unchanged','DMA_allocator_restored','DMA_sealed_after_main')) or r['unsafe_dma_buffers_retained'] or r['unexpected_DMA_requests']:raise ValueError('Incomplete quality/lifecycle PASS')
        if r['prior_chain_sha256']!=plan['chain_raw_sha256'] or r['prior_complete_MLP_sha256']!=plan['previous_local_raw_sha256'] or r['source_identities_verified']!=49 or r['full_wire_reference_batches_exact']!=26:raise ValueError('Prerequisites differ')
        reference=json.loads((ROOT/plan['reference_result']).read_bytes())
        expected=json.loads((PKG/'EXPECTED_VISUAL.json').read_bytes())
        if r['original_visual']!=expected['visual'] or r['preprocessed']!=expected['preprocessed'] or r['original_layer12_capture']!=reference['capture_tensors']:raise ValueError('Original full input/reference differs')
        want=dict(reference['candidate_tensors'],residual=reference['capture_tensors']['residual'])
        if r['candidate_layer12_capture']!=want or r['quality_metrics']!=reference['quality_metrics'] or r['target_matrices']!=reference['target_matrices'] or r['target_resolution']!=reference['target_resolution']:raise ValueError('Selected layer original/PL reference differs')
        if r['backend_before']!=r['backend_after'] or r['release_preflight']['status']!='READY_FOR_BOARD_PREFLIGHT':raise ValueError('Backend or35 assets changed')
        component=r['component']
        if not all(component[k] is True for k in ('actual_frozen24_wrappers_encoder_and_M207','first2_BF16_preserved','selected_layer12_only','real_Torch392_row_software_reference_equal','complete26_packets_raw_exact','all96_boundary_points','restored_hooks_and_binding','attention_weights_submit_and_memory_explicit_fixtures')) or component['negative_checks']!=9 or component['board_quality_capacity_or_performance'] is not False:raise ValueError('Actual target Torch integration checks incomplete')
        identities=json.loads((BASE/'candidates/M409-saved-MLP-reference-01/M348_SOURCE_IDENTITIES.json').read_bytes());ids={x['path']:x['sha256'] for x in identities['files']}
        modules=r['resolved_modules']
        if set(modules)!=set(plan['resolved_module_names']) or any(ids[x['path']]!=x['sha256'] for x in modules.values()):raise ValueError('Actual resolved source differs')
        if any(ids[k]!=v for k,v in component['source_sha256'].items()):raise ValueError('Target component frozen source differs')
        quality=r['full_visual_quality'];metrics=quality['metrics']
        if quality['thresholds']!=THRESHOLDS or quality['feature_screen_pass'] is not True or quality['semantic_accuracy_proven'] is not False or metrics['shape']!=[98,2560]:raise ValueError('Quality scope or predeclared thresholds differ')
        if any(type(metrics[k]) not in (float,int) or not math.isfinite(metrics[k]) for k in ('relative_l2','cosine','min_token_cosine','RMSE','max_abs')) or not 0<=metrics['relative_l2']<=.02 or not .999<=metrics['cosine']<=1.000000000001 or not .995<=metrics['min_token_cosine']<=1.000000000001 or metrics['RMSE']<0 or metrics['max_abs']<0:raise ValueError('Final complete feature screen rejected')
        if {k:r['candidate_visual'][k] for k in ('shape','dtype','bytes')}!={k:expected['visual'][k] for k in ('shape','dtype','bytes')} or not re.fullmatch('[0-9a-f]{64}',r['candidate_visual']['sha256']):raise ValueError('Complete candidate feature identity invalid')
        artifacts=r['retained_visual_features']
        if [x['path'] for x in artifacts]!=['original_visual.npy','candidate_visual.npy'] or any(x['file_bytes']!=1003648 or not re.fullmatch('[0-9a-f]{64}',x['file_sha256']) for x in artifacts) or [x['tensor'] for x in artifacts]!=[r['original_visual'],r['candidate_visual']]:raise ValueError('Two bounded retained feature identities differ')
        if r['CPU_store_after']['uncached_decode_calls']-r['CPU_store_before']['uncached_decode_calls']!=142 or r['CPU_store_after']['cache_entries']!=26 or r['CPU_store_after']['cache_bytes']!=66699264 or r['CPU_store_after']['cache_within_budget'] is not True:raise ValueError('Original full visual store restores/cache differ')
        if len(r['PL_rows'])!=26 or r['physical_transactions_started']!=28 or len(r['transactions'])!=2 or len(r['staging'])!=2 or sum(x['bytes'] for x in r['staging'])!=4456448:raise ValueError('Integrated PL physical/staging count differs')
        ordered=[(part,b) for part in ('fc1','fc2') for b in reference['reference_batches'][part]]
        for row,(part,b) in zip(r['PL_rows'],ordered):
            if (row['part'],row['start'],row['shift'],row['input_bytes'],row['output_bytes'],row['packet_sha256'],row['raw_sha256'])!=(part,b['start'],b['selected_shift'],b['input_bytes'],b['output_bytes'],b['packet_sha256'],b['raw_sha256']) or not safe_to_release(row['completed_snapshot']) or row['completed_snapshot']['ap_return']!=0x4d333537:raise ValueError('Full ordered wire/DMA completion differs')
        for part in ('fc1','fc2'):
            want=[{k:b[k] for k in ('start','rows','initial_shift','attempted_shifts','selected_shift')}|{'physical_calls':b['physical_reference_attempts']} for b in reference['reference_batches'][part]]
            if r['numerical_batches'][part]!=want:raise ValueError('Integrated26 batch/retry contract differs')
        allocations=r['allocations'];releases=[];start=0
        if len(allocations)!=19:raise ValueError('Allocation count differs')
        for count in (6,7,6):releases.extend(reversed(allocations[start:start+count]));start+=count
        if releases!=r['releases'] or sum(x['bytes'] for x in allocations[6:13])!=3440656 or r['admission_policy']!=POLICY:raise ValueError('Sealed DMA payload/release/policy differs')
        groups=[dict(label=label,sizes=list(sizes),attempted=len(sizes),returned=len(sizes),complete=True) for label,sizes in zip(['candidate-legal-build-id','completeMLP-seven','stable-restored-build-id'],[MINIMAL_SIZES,MAIN_SIZES,MINIMAL_SIZES])]
        if r['DMA_admission_groups']!=groups:raise ValueError('Exact three owner allocation groups differ')
        memory_labels=['allocated:candidate-legal-build-id','before-submit:candidate-legal-build-id','allocated:completeMLP-seven']+['MLP-before-submit']*26+['allocated:stable-restored-build-id','before-submit:stable-restored-build-id']
        ps_labels=['after-constructor']
        for phase in ('original-full-visual','layer12-PL-full-visual'):
            ps_labels.append('before-'+phase)
            ps_labels.extend(phase+':layer'+str(i)+':'+edge for i in range(24) for edge in ('before','after'))
            ps_labels.append('after-'+phase)
        if [x['label'] for x in r['memory']]!=memory_labels or [x['label'] for x in r['PS_checkpoints']]!=ps_labels or [x['recovery'] for x in r['memory']]!=[False]*29+[True]*2 or any(x['recovery'] for x in r['PS_checkpoints']):raise ValueError('Actual complete visual memory coverage differs')
        for x in r['memory']+r['PS_checkpoints']:
            growth=max(0,x['VmRSS']-r['memory_after_constructor']['VmRSS']);required=(64<<20)+(0 if x['recovery'] else max(0,(768<<20)-growth))
            if x['admission_policy']!=POLICY['name'] or x['required_cma_free_bytes'] is not None or type(x['CmaFree']) is not int or x['CmaFree']<0 or x['RSS_growth_bytes']!=growth or x['required_MemAvailable_bytes']!=required or x['MemAvailable']<required or (not x['recovery'] and growth>768<<20):raise ValueError('Actual ordinary memory budget invalid')
        if not safe_to_release(r['final_snapshot']) or r['final_snapshot']['ap_return']!=0x4d395832 or not 0<r['elapsed_s_diagnostic_not_performance']<=840:raise ValueError('Stable completion or bounded duration differs')
        if any(type(r[k]) is not int or r[k]<=0 for k in ('original_visual_elapsed_ns_diagnostic','candidate_visual_elapsed_ns_diagnostic')):raise ValueError('Visual diagnostic duration missing')
    elif r['status'].startswith('FAIL_'):
        if rc!=1 or not r['errors']:raise ValueError('Failure without original error')
    else:raise ValueError('Unknown result status')
    return digest,raw,r,len(chunks)

def collect(log,out=None,sync_function=sync):
    digest,raw,r,count=decode(Path(log).read_text(encoding='utf-8-sig'));out=out or BASE/'runs/M414-layer12-visual-board-01/BOARD_RESULT.json'
    atomic(out,raw,immutable=True)
    report='# M414 第12层接入完整视觉特征质量\n\n'+r['status']+'，原rc '+str(r['gate_return_code'])+'，原SHA '+digest+'。\n\n只第12层两个MLP Linear，原末帧两个224视图及其他路径保持；实际完整视觉 '+str(r['visual_forward_calls'])+' 次，PL批次 '+str(len(r['PL_rows']))+'，0语言/扩层/请求性能。特征阈值仅拒绝筛选，不是识别准确率证明。全部时间含诊断钩子，不能作为性能比较。\n\n```json\n'+json.dumps(r.get('full_visual_quality',r['errors']),ensure_ascii=False,indent=2)+'\n```\n'
    atomic(out.with_name('REPORT.md'),report.encode('utf-8'),immutable=True)
    sync_function('latest_m414_layer12_visual_board',dict(status=r['status'],result=out.relative_to(ROOT).as_posix(),sha256=digest,manifest_sha256=r['manifest_sha256'],build_id=r['build_id'],feature_quality_pass=r['feature_quality_pass'],semantic_quality_proven=False,expanded_24_layers=False),
        f'## M414 第12层完整视觉质量门禁（2026-10-06）\n\n原SHA {digest}；{count}个≤900B原字节严格回收，rc{r["gate_return_code"]}，{r["status"]}。仅原第12层MLP接入，两次完整视觉/0语言；全26 wire及最终98×2560特征筛选和原生命周期，非语义准确率/性能，不扩大24层。原CMA固定64门槛取消，实际七缓冲分配后封锁新增，普通PS768MiB增长预算。失败只停本级，不重跑以补回收；同步闭合后才决定后续。')
    print('M414_RESULT_SYNC',digest,count);return r

if __name__=='__main__':
    import sys
    if sys.argv[1:]==['transfer']:transfer()
    elif len(sys.argv)==3 and sys.argv[1]=='collect':collect(sys.argv[2])
    else:raise SystemExit('transfer | collect LOG')
