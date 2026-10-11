"""Strict immutable saved recovery; performance verdict is separate from raw gate."""
import base64,hashlib,json,math,re
from pathlib import Path
from m351_workflow import ROOT,BASE,HERE,atomic,encoded,sha,sync
from board_safety import safe_to_release
PKG=BASE/'candidates/M436-weight-read-observation-03'
OUT=BASE/'runs/M436-IO-observation-board-02/BOARD_RESULT.json'

def check(r):
    if r['manifest_sha256']!=sha(PKG/'PACKAGE_MANIFEST.json') or r['gate_level']!='fixed-BB-file-IO-residency-diagnostic' or r['build_id']!='0x4D333537' or type(r['gate_return_code']) is not int:raise ValueError('Identity/rc differs')
    if r.get('performance_pass') is not False or r.get('formal_promotion_allowed') is not False or r.get('expanded_24_layers',False):raise ValueError('Raw measurements cannot promote')
    if r.get('temperature_measurement_enabled') is not False:raise ValueError('Temperature measurement must be disabled')
    if r['status']=='PASS_M435_BB_IO_DIAGNOSTIC':
        numerical=json.loads((PKG/'PERFORMANCE_PLAN.json').read_bytes())
        if r.get('complete_request_numerical_source_sha256')!=numerical['integrated_numerical_sha256'] or r.get('peak_live_visual_layer_scopes')!=1 or r.get('visual_bindings_restored') is not True:raise ValueError('Integrated numerical prerequisite or live scope differs')
        for k in ('all2_requests_completed','observer_checked_before_overlay','io_observer_hooks_restored','numerical_pass','features_verified_before_overlay','head_AST_checked_before_overlay','request_tokenizer_restored_before_prefill','safe_buffers_released','stable_overlay_reloaded','boot_unchanged','cmdline_unchanged','integrated_sources_checked_before_overlay','visual_provider_disposed','borrowed_buffer_identity_preserved','visual_static_cache_invalidated','full_hashes_after_timers'):
            if r.get(k) is not True:raise ValueError('PASS missing '+k)
        if r['gate_return_code'] or r['errors'] or r['unsafe_buffers_retained'] or r.get('borrowed_extra_DMA')!=0 or r.get('additional_cma_requests_allowed') is not False:raise ValueError('Completion/ownership differs')
        plan=json.loads((PKG/'PLAN.json').read_bytes())
        if r['allocated_buffers']!=list(reversed(r['released_buffers'])) or [x['bytes'] for x in r['allocated_buffers']]!=plan['DMA_sizes'] or r['original_buffer_release_count']!=7:raise ValueError('Seven DMA ownership differs')
        if r['vision_forward_calls']!=2 or r['model_forward_calls']!=2 or r['decode_calls'] or r['output_budget']!=1 or r['selected_layers']!=list(range(13,24)) or r['selected_frame_indices']!=[3] or r['views']!=2:raise ValueError('Request scope differs')
        if r['fpga_transactions']!=2135 or r['host_calls']!=1562 or r['logical_calls']!=1556 or r['completed_language_physical']!=1562 or r['completed_visual_physical']!=572 or r.get('transactions') or r.get('visual_transactions'):raise ValueError('Cumulative physical accounting differs')
        samples=r['samples']
        if len(samples)!=2 or ''.join(s['variant'] for s in samples)!='BB' or r['diagnostic_order']!='BB' or r['timings_not_performance'] is not True or r['performance_measurements_collected'] is not False:raise ValueError('Fixed diagnostic scope differs')
        board=json.loads((ROOT/'deployment/mage_vl4b/BOARD_GATE_RESULT.json').read_bytes())
        src=board['latest_m428_saved_language_board'];assert sha(ROOT/src['result'])==src['sha256']
        references=json.loads((ROOT/src['result']).read_bytes())['samples']
        for i,s in enumerate(samples):
            index=0 if s['variant']=='A' else 1;expected=references[index]
            if s['numerical_SHA_after_timer']!={k:expected[k] for k in ('input','visual','token','logits','keys','values')} or not all(s['exact_saved_reference'].values()):raise ValueError('Complete endpoint differs')
            if s['counts']!=expected['counts'] or s['language_physical_observed']!=781 or s['visual_physical_observed']!=(286 if index else 0):raise ValueError('Per-request retry/count differs')
            for side in ('before_cache','after_cache'):
                c=s.get(side,{})
                if type(c.get('cache_entries')) is not int or not 0<=c['cache_entries']<=26 or type(c.get('cache_bytes')) is not int or not 0<=c['cache_bytes']<=66699264 or c.get('cache_within_budget') is not True:raise ValueError('Candidate decoded-cache bound differs')
            if index and [(x['layer'],x['part'],x['bytes']) for x in s['visual_staging']]!=[(a,p,2228224) for a in range(13,24) for p in ('fc1','fc2')]:raise ValueError('Candidate twenty-two stages differ')
            if not index and s['visual_staging']:raise ValueError('Original unexpectedly uses PL visual')
            for k in ('all_visual_bindings_restored','original_seven_DMA_still_resident'):
                if s.get(k) is not True:raise ValueError('Request lifecycle differs')
            if not safe_to_release(s['final_snapshot']) or s['final_snapshot']['ap_return']!=0x4d333537 or s['sampled_memory']['observer_stopped'] is not True or s['sampled_memory']['stop_reason'] is not None:raise ValueError('Request DMA/observer unsafe')
            if set(s['timing']['stages_ms'])!={'preprocess','vision','prefill','head'} or any(not math.isfinite(t) or t<0 for t in s['timing']['stages_ms'].values()):raise ValueError('Stage timer missing/invalid')
            token=s['semantic']['token'];decision=expected['decision']
            if any(token[a]!=decision[b] for a,b in [('token_id','token_id'),('text','text'),('knife_verdict','verdict'),('knife_score','knife_score')]):raise ValueError('Constrained decision differs')
            expected_records=json.loads((ROOT/src['result']).read_bytes())['transactions'][index*781:(index+1)*781]
            if s['physical_record_SHA_after_timer']!=hashlib.sha256(json.dumps(expected_records,sort_keys=True,separators=(',',':')).encode()).hexdigest():raise ValueError('Complete post-timer language physical sequence differs')
            for k in ('physical_record_SHA_after_timer','visual_record_SHA_after_timer'):
                if not re.fullmatch('[0-9a-f]{64}',s[k]):raise ValueError('Transaction record digest missing')
        observation=json.loads((PKG/'OBSERVATION_PLAN.json').read_bytes())
        obs=r['read_observation']
        if obs['cache_eviction'] is not False or obs['additional_weight_cache'] is not False:raise ValueError('Unexpected cache manipulation')
        expected=[{k:x[k] for k in ('group','path','offset','bytes')} for x in observation['expected_reads']]
        for n in (1,2):
            rows=[x for x in obs['reads'] if x['request']==n]
            if [{k:x[k] for k in ('group','path','offset')}|dict(bytes=x['returned_bytes']) for x in rows]!=expected:raise ValueError('Actual file read contract differs')
            if any(x['requested_bytes']!=x['returned_bytes'] or x['elapsed_ns_diagnostic']<0 or x['io']['read_bytes']<0 for x in rows):raise ValueError('Read interval invalid')
        if len(obs['reads'])!=1472 or not obs['decodes'] or len(obs['snapshots'])!=6:raise ValueError('Narrow observation incomplete')
        from m435_io_observer import residency_change
        for n in (1,2):
            snapshots=[x for x in obs['snapshots'] if x['request']==n]
            if [x['label'] for x in snapshots]!=observation['mincore_boundaries']:raise ValueError('Residency boundaries differ')
            for a,b in zip(snapshots,snapshots[1:]):
                if len(a['files'])!=12 or len(b['files'])!=12 or [x['path'] for x in a['files']]!=sorted(x['path'] for x in observation['files']):raise ValueError('Residency file set differs')
                for x,y in zip(a['files'],b['files']):residency_change(x,y)
        probe=r['linux_residency_probe'];tests=r['observer_component_tests']
        if probe['sparse_initial_resident']!=0 or probe['buffered_write_resident']<=0 or not probe['fixture_removed'] or not probe['first_page_observed'] or not probe['maps_and_fds_closed']:raise ValueError('Linux probe unproven')
        if tests['run']!=15 or tests['skipped'] or tests['success'] is not True:raise ValueError('Board pre-resource observer tests failed')
        proof=r['same_overlay_minimal_proof']
        if proof['full_output_exact'] is not True or not safe_to_release(proof['snapshot']) or proof['snapshot']['ap_return']!=0x4d333537:raise ValueError('Legal minimal missing')
        if not safe_to_release(r['final_snapshot']) or r['final_snapshot']['ap_return']!=0x4d333537 or r['stable_restore_transaction_submitted'] is not False:raise ValueError('Final/reload lifecycle differs')
        if r['head_observer_proof']['removed_observation_calls_ast_equals_original'] is not True or r['head_observer_proof']['exact_frozen_head_chains']!=8 or r['release_preflight']['status']!='READY_FOR_BOARD_PREFLIGHT':raise ValueError('Head/assets differ')
    elif r['status'] in ('FAIL','FAIL_COMPLETE_RUNTIME_CAPACITY','FAIL_UNSAFE_RETAINED','FAIL_BUDGET'):
        if r['gate_return_code']!=1 or not r['errors']:raise ValueError('Original failure not preserved')
    else:raise ValueError('Unknown saved status')
    return r

def decode(text):
    hashes=re.findall(r'(?m)^M435_RESULT_SHA256=([0-9a-f]{64})\s*$',text);codes=re.findall(r'(?m)^M435_SAVED_GATE_RC=([01])\s*$',text)
    chunks=re.findall(r'(?m)^M435_RESULT_CHUNK=(\d+)/(\d+):([A-Za-z0-9+/=]+)\s*$',text)
    if len(hashes)!=1 or len(codes)!=1 or not chunks or len(chunks)!=int(chunks[0][1]):raise ValueError('Incomplete/duplicate result')
    parts=[]
    for i,(n,total,b64) in enumerate(chunks):
        p=base64.b64decode(b64,validate=True)
        if int(n)!=i or int(total)!=len(chunks) or not 0<len(p)<=900:raise ValueError('Chunk order/size differs')
        parts.append(p)
    raw=b''.join(parts);digest=hashlib.sha256(raw).hexdigest();r=check(json.loads(raw))
    if len(raw)>4<<20 or digest!=hashes[0] or r['gate_return_code']!=int(codes[0]):raise ValueError('Full raw SHA/rc differs')
    done=re.findall(r'M435_DONE gate_rc=(\d+) export_rc=(\d+)',text)
    if done and done!=[(codes[0],'0')]:raise ValueError('Runner rc differs')
    return digest,raw,r,len(chunks)

def collect(log):
    digest,raw,r,count=decode(Path(log).read_text(encoding='utf-8-sig'));atomic(OUT,raw,immutable=True)
    report='# M435 固定两个B窄文件I/O观察\n\n'+r['status']+'，原SHA '+digest+'。\n\n不测温度。只用于读取与驻留归因；所有计时含观察器开销，不作性能裁决，不扩层或晋级。\n'
    atomic(OUT.with_name('REPORT.md'),report.encode('utf-8'),immutable=True)
    sync('latest_m436_IO_board',dict(status=r['status'],result=OUT.relative_to(ROOT).as_posix(),sha256=digest,manifest_sha256=r['manifest_sha256'],build_id=r['build_id'],temperature_measurement_enabled=False,performance_pass=False),f'## M436 双请求缓存修正后 I/O 观察（2026-10-07）\n\n原SHA {digest}，{count}块≤900B严格回收，rc{r["gate_return_code"]}，{r["status"]}。固定两个B诊断请求，文件窗口和12文件驻留快照；原数值/七DMA释放，失败只回收不重跑。不要求零I/O、不做性能或晋级、不测温。')
    print('M435_RESULT_SYNC',digest,count);return r

def upload_names():
    old=json.loads((BASE/'candidates/M435-weight-read-observation-02/PACKAGE_MANIFEST.json').read_bytes());byname={x['path']:x for x in old['files']}
    m=json.loads((PKG/'PACKAGE_MANIFEST.json').read_bytes())
    return ['PACKAGE_MANIFEST.json']+[x['path'] for x in m['files'] if byname.get(x['path'])!=x]

def transfer():
    folder=ROOT/'tmp/m43602/board';m=json.loads((PKG/'PACKAGE_MANIFEST.json').read_bytes());receipts=[]
    for name in upload_names():
        size=(PKG/name).stat().st_size;count=(size+899)//900;prefix='upload_'+name.replace('.','_')
        final=(folder/(prefix+'_final.log')).read_text(encoding='utf-8-sig')
        if 'M212_CHUNKED_FILE_PASS' not in final or sha(PKG/name) not in final:raise ValueError('Transfer SHA missing')
        chunks=sorted(folder.glob(prefix+'_chunk_*.log'))
        if len(chunks)!=count:raise ValueError('Transfer receipt count differs')
        for i,p in enumerate(chunks,1):
            if not re.search(r'M212_CHUNK_PASS\s+'+str(i)+r'\s+'+str(count)+r'\s+'+str(min(i*900,size))+r'\s',p.read_text(encoding='utf-8-sig')):raise ValueError('Transfer sequence differs')
        receipts.append(dict(path=name,sha256=sha(PKG/name),chunks=count))
    marker=f'M435_ASSEMBLY_PASS {sha(PKG/"PACKAGE_MANIFEST.json")} {m["file_count"]} {m["total_bytes"]}'
    if marker not in (folder/'assembly.log').read_text(encoding='utf-8-sig') or '__M435_SYNTAX_RC_0__' not in (folder/'syntax.log').read_text(encoding='utf-8-sig'):raise ValueError('Assembly/bash receipt missing')
    r=dict(status='PASS_M435_MANIFEST_FIRST_HASHED_TRANSFER',manifest_sha256=sha(PKG/'PACKAGE_MANIFEST.json'),receipts=receipts,assembled_existing_assets_only=True,gate_started=False)
    p=BASE/'runs/M436-route-transfer-01/RESULT.json';atomic(p,encoded(r),immutable=True)
    sync('latest_m436_route_transfer',dict(status=r['status'],result=p.relative_to(ROOT).as_posix(),sha256=sha(p),manifest_sha256=r['manifest_sha256']),f'## M436 修正包传输（2026-10-07）\n\nSHA {sha(p)}；manifest-first900B全部回执/逐SHA及bash-n通过，尚未执行。温度不读；下一步一次固定两个B诊断请求。')
    print('M435_TRANSFER_SYNC',sha(p))

if __name__=='__main__':
    import sys
    if sys.argv[1:]==['transfer']:transfer()
    elif len(sys.argv)==3 and sys.argv[1]=='collect':collect(sys.argv[2])
    else:raise SystemExit('transfer | collect LOG')
