"""Strict immutable saved recovery; performance verdict is separate from raw gate."""
import base64,hashlib,json,math,re
from pathlib import Path
from m351_workflow import ROOT,BASE,HERE,atomic,encoded,sha,sync
from board_safety import safe_to_release
PKG=BASE/'candidates/M425-visual-MLP-warm-performance-02'
OUT=BASE/'runs/M425-warm-performance-board-01/BOARD_RESULT.json'

def check(r):
    if r['manifest_sha256']!=sha(PKG/'PACKAGE_MANIFEST.json') or r['gate_level']!='controlled-warm-complete-request-performance' or r['build_id']!='0x4D333537' or type(r['gate_return_code']) is not int:raise ValueError('Identity/rc differs')
    if r.get('performance_pass') is not False or r.get('formal_promotion_allowed') is not False or r.get('expanded_24_layers',False):raise ValueError('Raw measurements cannot promote')
    if r.get('temperature_measurement_enabled') is not False:raise ValueError('Temperature measurement must be disabled')
    if r['status']=='PASS_M425_CONTROLLED_WARM_MEASUREMENTS_COLLECTED':
        for k in ('all12_requests_completed','performance_measurements_collected','numerical_pass','warm_conditions_established','features_verified_before_overlay','head_AST_checked_before_overlay','request_tokenizer_restored_before_prefill','safe_buffers_released','stable_overlay_reloaded','boot_unchanged','cmdline_unchanged','integrated_sources_checked_before_overlay','visual_provider_disposed','borrowed_buffer_identity_preserved','visual_static_cache_invalidated','full_hashes_after_timers'):
            if r.get(k) is not True:raise ValueError('PASS missing '+k)
        if r['gate_return_code'] or r['errors'] or r['unsafe_buffers_retained'] or r.get('borrowed_extra_DMA')!=0 or r.get('additional_cma_requests_allowed') is not False:raise ValueError('Completion/ownership differs')
        plan=json.loads((PKG/'PLAN.json').read_bytes())
        if r['allocated_buffers']!=list(reversed(r['released_buffers'])) or [x['bytes'] for x in r['allocated_buffers']]!=plan['DMA_sizes'] or r['original_buffer_release_count']!=7:raise ValueError('Seven DMA ownership differs')
        if r['vision_forward_calls']!=12 or r['model_forward_calls']!=12 or r['decode_calls'] or r['output_budget']!=1 or r['selected_layers']!=[12,13] or r['selected_frame_indices']!=[3] or r['views']!=2:raise ValueError('Request scope differs')
        if r['fpga_transactions']!=9685 or r['host_calls']!=9372 or r['logical_calls']!=9336 or r['completed_language_physical']!=9372 or r['completed_visual_physical']!=312 or r.get('transactions') or r.get('visual_transactions'):raise ValueError('Cumulative physical accounting differs')
        from m425_warm import ORDER,WarmSequence
        protocol_sha=json.loads((PKG/'PERFORMANCE_PLAN.json').read_bytes())['protocol_sha256']
        if r['warm_protocol_sha256']!=protocol_sha:raise ValueError('Protocol differs')
        samples=r['samples']
        if len(samples)!=12 or ''.join(s['variant'] for s in samples)!=ORDER or r['warmup_samples']!=samples[:4] or r['formal_samples']!=samples[4:]:raise ValueError('Fixed sequence differs')
        board=json.loads((ROOT/'deployment/mage_vl4b/BOARD_GATE_RESULT.json').read_bytes())
        src=board['latest_m421_saved_language_board'];assert sha(ROOT/src['result'])==src['sha256']
        references=json.loads((ROOT/src['result']).read_bytes())['samples']
        sequence=WarmSequence({},r['warm_environment_reference'],clock=lambda:0,protocol_sha=protocol_sha)
        for i,s in enumerate(samples):
            index=0 if s['variant']=='A' else 1;expected=references[index]
            sequence.before(i);sequence.record(s)
            if s['numerical_SHA_after_timer']!={k:expected[k] for k in ('input','visual','token','logits','keys','values')} or not all(s['exact_saved_reference'].values()):raise ValueError('Complete endpoint differs')
            if s['counts']!=expected['counts'] or s['language_physical_observed']!=781 or s['visual_physical_observed']!=(52 if index else 0):raise ValueError('Per-request retry/count differs')
            if index and [(x['layer'],x['part'],x['bytes']) for x in s['visual_staging']]!=[(a,p,2228224) for a in (12,13) for p in ('fc1','fc2')]:raise ValueError('Candidate four stages differ')
            if not index and s['visual_staging']:raise ValueError('Original unexpectedly uses PL visual')
            for k in ('all_four_bindings_restored','original_seven_DMA_still_resident'):
                if s.get(k) is not True:raise ValueError('Request lifecycle differs')
            if not safe_to_release(s['final_snapshot']) or s['final_snapshot']['ap_return']!=0x4d333537 or s['sampled_memory']['observer_stopped'] is not True or s['sampled_memory']['stop_reason'] is not None:raise ValueError('Request DMA/observer unsafe')
            if set(s['timing']['stages_ms'])!={'preprocess','vision','prefill','head'} or any(not math.isfinite(t) or t<0 for t in s['timing']['stages_ms'].values()):raise ValueError('Stage timer missing/invalid')
            token=s['semantic']['token'];decision=expected['decision']
            if any(token[a]!=decision[b] for a,b in [('token_id','token_id'),('text','text'),('knife_verdict','verdict'),('knife_score','knife_score')]):raise ValueError('Constrained decision differs')
            for k in ('physical_record_SHA_after_timer','visual_record_SHA_after_timer'):
                if not re.fullmatch('[0-9a-f]{64}',s[k]):raise ValueError('Transaction record digest missing')
        proof=r['same_overlay_minimal_proof']
        if proof['full_output_exact'] is not True or not safe_to_release(proof['snapshot']) or proof['snapshot']['ap_return']!=0x4d333537:raise ValueError('Legal minimal missing')
        if not safe_to_release(r['final_snapshot']) or r['final_snapshot']['ap_return']!=0x4d333537 or r['stable_restore_transaction_submitted'] is not False:raise ValueError('Final/reload lifecycle differs')
        if r['head_observer_proof']['removed_observation_calls_ast_equals_original'] is not True or r['head_observer_proof']['exact_frozen_head_chains']!=8 or r['release_preflight']['status']!='READY_FOR_BOARD_PREFLIGHT':raise ValueError('Head/assets differ')
    elif r['status'] in ('FAIL','FAIL_COMPLETE_RUNTIME_CAPACITY','FAIL_UNSAFE_RETAINED','FAIL_BUDGET'):
        if r['gate_return_code']!=1 or not r['errors']:raise ValueError('Original failure not preserved')
    else:raise ValueError('Unknown saved status')
    return r

def decode(text):
    hashes=re.findall(r'(?m)^M425_RESULT_SHA256=([0-9a-f]{64})\s*$',text);codes=re.findall(r'(?m)^M425_SAVED_GATE_RC=([01])\s*$',text)
    chunks=re.findall(r'(?m)^M425_RESULT_CHUNK=(\d+)/(\d+):([A-Za-z0-9+/=]+)\s*$',text)
    if len(hashes)!=1 or len(codes)!=1 or not chunks or len(chunks)!=int(chunks[0][1]):raise ValueError('Incomplete/duplicate result')
    parts=[]
    for i,(n,total,b64) in enumerate(chunks):
        p=base64.b64decode(b64,validate=True)
        if int(n)!=i or int(total)!=len(chunks) or not 0<len(p)<=900:raise ValueError('Chunk order/size differs')
        parts.append(p)
    raw=b''.join(parts);digest=hashlib.sha256(raw).hexdigest();r=check(json.loads(raw))
    if len(raw)>4<<20 or digest!=hashes[0] or r['gate_return_code']!=int(codes[0]):raise ValueError('Full raw SHA/rc differs')
    done=re.findall(r'M425_DONE gate_rc=(\d+) export_rc=(\d+)',text)
    if done and done!=[(codes[0],'0')]:raise ValueError('Runner rc differs')
    return digest,raw,r,len(chunks)

def collect(log):
    digest,raw,r,count=decode(Path(log).read_text(encoding='utf-8-sig'));atomic(OUT,raw,immutable=True)
    report='# M425 完整暖请求原始测量\n\n'+r['status']+'，原SHA '+digest+'。\n\n不测温度。原始门禁只证明预定测量/数值/释放；净收益另按冻结协议裁决，不扩层或晋级。\n'
    atomic(OUT.with_name('REPORT.md'),report.encode('utf-8'),immutable=True)
    sync('latest_m425_warm_board',dict(status=r['status'],result=OUT.relative_to(ROOT).as_posix(),sha256=digest,manifest_sha256=r['manifest_sha256'],build_id=r['build_id'],temperature_measurement_enabled=False,performance_pass=False),f'## M425 完整暖请求原字节回收（2026-10-06）\n\n原SHA {digest}，{count}块≤900B严格回收，rc{r["gate_return_code"]}，{r["status"]}。温度读取关闭，预定最多12请求及独立数值、DMA生命周期核对；失败不追加/不硬件重跑。三记录同步后才按预定八正式样本统计裁决，非生产晋级。')
    print('M425_RESULT_SYNC',digest,count);return r

def upload_names():
    old=json.loads((BASE/'candidates/M423-integrated-video-01/PACKAGE_MANIFEST.json').read_bytes());byname={x['path']:x for x in old['files']}
    m=json.loads((PKG/'PACKAGE_MANIFEST.json').read_bytes())
    return ['PACKAGE_MANIFEST.json']+[x['path'] for x in m['files'] if byname.get(x['path'])!=x]

def transfer():
    folder=ROOT/'tmp/m42502';m=json.loads((PKG/'PACKAGE_MANIFEST.json').read_bytes());receipts=[]
    for name in upload_names():
        size=(PKG/name).stat().st_size;count=(size+899)//900;prefix='upload_'+name.replace('.','_')
        final=(folder/(prefix+'_final.log')).read_text(encoding='utf-8-sig')
        if 'M212_CHUNKED_FILE_PASS' not in final or sha(PKG/name) not in final:raise ValueError('Transfer SHA missing')
        chunks=sorted(folder.glob(prefix+'_chunk_*.log'))
        if len(chunks)!=count:raise ValueError('Transfer receipt count differs')
        for i,p in enumerate(chunks,1):
            if not re.search(r'M212_CHUNK_PASS\s+'+str(i)+r'\s+'+str(count)+r'\s+'+str(min(i*900,size))+r'\s',p.read_text(encoding='utf-8-sig')):raise ValueError('Transfer sequence differs')
        receipts.append(dict(path=name,sha256=sha(PKG/name),chunks=count))
    marker=f'M425_ASSEMBLY_PASS {sha(PKG/"PACKAGE_MANIFEST.json")} {m["file_count"]} {m["total_bytes"]}'
    if marker not in (folder/'assembly.log').read_text(encoding='utf-8-sig') or '__M425_SYNTAX_RC_0__' not in (folder/'syntax.log').read_text(encoding='utf-8-sig'):raise ValueError('Assembly/bash receipt missing')
    r=dict(status='PASS_M425_MANIFEST_FIRST_HASHED_TRANSFER',manifest_sha256=sha(PKG/'PACKAGE_MANIFEST.json'),receipts=receipts,assembled_existing_assets_only=True,gate_started=False)
    p=BASE/'runs/M425-performance-transfer-01/RESULT.json';atomic(p,encoded(r),immutable=True)
    sync('latest_m425_performance_transfer',dict(status=r['status'],result=p.relative_to(ROOT).as_posix(),sha256=sha(p),manifest_sha256=r['manifest_sha256']),f'## M425 完整暖请求包传输（2026-10-06）\n\nSHA {sha(p)}；manifest-first900B全部回执/逐SHA及bash-n通过，尚未执行。温度不读；下一步一次固定四预热和八正式完整请求。')
    print('M425_TRANSFER_SYNC',sha(p))

if __name__=='__main__':
    import sys
    if sys.argv[1:]==['transfer']:transfer()
    elif len(sys.argv)==3 and sys.argv[1]=='collect':collect(sys.argv[2])
    else:raise SystemExit('transfer | collect LOG')
