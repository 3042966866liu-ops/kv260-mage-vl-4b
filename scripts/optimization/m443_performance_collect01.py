"""Strict immutable saved recovery; performance verdict is separate from raw gate."""
import base64,hashlib,json,math,re
from pathlib import Path
from m351_workflow import ROOT,BASE,HERE,atomic,encoded,sha,sync
from board_safety import safe_to_release
PKG=BASE/'candidates/M443-complete-request-performance-01'
OUT=BASE/'runs/M443-complete-request-performance-board-01/BOARD_RESULT.json'

from m443_performance_ledger01 import validate as validate_configuration01
from m443_configuration01 import validate_record
APPLICATION_SHA=sha(PKG/'CONFIGURATION_APPLICATION.json')
CANDIDATE_SHA='6b1942e566e78d229f0c62a69d3a1b05c00bce474fff314ecedfe014a65e50f8'
def validate_configuration(record):return validate_configuration01(record,APPLICATION_SHA,CANDIDATE_SHA)
def verify_ledger(r):
    expected=[(1,'A'),(2,'B'),(4,'A'),(6,'B'),(8,'A'),(9,'B'),(10,'A'),(12,'B')]
    rows=r['configuration_CMA_ledger'];assert len(rows)==8 and not r.get('configuration_CMA_rejected')
    assert r['M443_configuration_prerequisite']['sha256']=='403b8549a7ea6444b89cedd551ed553ba32b8d9c93caedde9c187fc7347a3599'
    assert r['M443_configuration_prerequisite']['application_sha256']==APPLICATION_SHA and r['M443_configuration_prerequisite']['manifest_sha256']==CANDIDATE_SHA
    assert r['M443_configuration_prerequisite']['actual_new_bit_application'] is True and r['M443_configuration_prerequisite']['configuration_credits_granted']==0
    baseline=rows[0]['before'];prior=baseline
    for j,(record,(index,variant)) in enumerate(zip(rows,expected),1):
        assert record['index']==index and record['variant']==variant
        assert record['bit_sha256']==('73350f615a5bc98d1d8aa2b5c69c4d6fd399aa1ef651f37411cbed21c0daed2e' if variant=='A' else '555ae52842ae901c863152a5a02b2dd4583ed95691255d98889a25ae579c27ae')
        assert record['before']==prior and record['original_baseline_unchanged']==baseline
        assert record['verified_released_configuration_pages']==validate_configuration(record)=={'reserved:alloc_pages_success':1904}
        assert record['cumulative_verified_credits']=={'reserved:alloc_pages_success':j*1904}
        assert record['after']=={k:v+record['cumulative_verified_credits'].get(k,0) for k,v in baseline.items()}
        prior=record['after']
    return True
def check(r):
    if r['manifest_sha256']!=sha(PKG/'PACKAGE_MANIFEST.json') or r['gate_level']!='same-visual-kernel-complete-request-performance' or r['build_id']!='0x4D343433' or type(r['gate_return_code']) is not int:raise ValueError('Identity/rc differs')
    if r.get('performance_pass') is not False or r.get('formal_promotion_allowed') is not False or r.get('expanded_24_layers',False):raise ValueError('Raw measurements cannot promote')
    if r.get('temperature_measurement_enabled') is not False:raise ValueError('Temperature measurement must be disabled')
    if r['status']=='PASS_M443P_NATURAL_IO_MEASUREMENTS_COLLECTED':
        verify_ledger(r)
        if r.get('configuration_application_accepted') is not True or r.get('unknown_configuration_ownership') is not False or r.get('source_compatibility_checked_before_overlay') is not True or r.get('configuration_driver_sources_checked_before_overlay') is not True:raise ValueError('Initial actual configuration admission differs')
        if r.get('configuration_application_build_raw_sha256')!=r['M443_configuration_prerequisite']['sha256']:raise ValueError('Configuration origin differs')
        validate_record(r['configuration_record'],APPLICATION_SHA,CANDIDATE_SHA)
        if any(x['pid']!=r['configuration_record']['pid'] for x in r['configuration_CMA_ledger']):raise ValueError('Resident switch trace must share initial process identity')
        for name,status in (('M443_BUILD_CONFIGURATION_PROOF.json','PASS_M443_BUILDID'),('M443_CHAIN_PREREQUISITE.json','PASS_M443_CHAIN'),('M443_VIDEO_PREREQUISITE.json','PASS_M443V_INTEGRATED_VIDEO_NUMERICAL')):
            proof=json.loads((PKG/name).read_bytes())
            if proof['status']!=status or proof['gate_return_code']!=0:raise ValueError('Original actual prerequisite differs')
            validate_record(proof['configuration_record'],APPLICATION_SHA,CANDIDATE_SHA)
        numerical=json.loads((PKG/'PERFORMANCE_PLAN.json').read_bytes())
        if r.get('complete_request_numerical_source_sha256')!=numerical['integrated_numerical_sha256'] or r.get('peak_live_visual_layer_scopes')!=1 or r.get('visual_bindings_restored') is not True:raise ValueError('Integrated numerical prerequisite or live scope differs')
        for k in ('all12_requests_completed','performance_measurements_collected','numerical_pass','preconditioning_completed','features_verified_before_overlay','head_AST_checked_before_overlay','request_tokenizer_restored_before_prefill','safe_buffers_released','stable_overlay_reloaded','boot_unchanged','cmdline_unchanged','integrated_sources_checked_before_overlay','visual_provider_disposed','borrowed_buffer_identity_preserved','visual_static_cache_invalidated','full_hashes_after_timers'):
            if r.get(k) is not True:raise ValueError('PASS missing '+k)
        if r['gate_return_code'] or r['errors'] or r['unsafe_buffers_retained'] or r.get('borrowed_extra_DMA')!=0 or r.get('additional_cma_requests_allowed') is not False:raise ValueError('Completion/ownership differs')
        plan=json.loads((PKG/'PLAN.json').read_bytes())
        if r['allocated_buffers']!=list(reversed(r['released_buffers'])) or [x['bytes'] for x in r['allocated_buffers']]!=plan['DMA_sizes'] or r['original_buffer_release_count']!=7:raise ValueError('Seven DMA ownership differs')
        if r['vision_forward_calls']!=12 or r['model_forward_calls']!=12 or r['decode_calls'] or r['output_budget']!=1 or r['selected_layers']!=list(range(13,24)) or r['selected_frame_indices']!=[3] or r['views']!=2:raise ValueError('Request scope differs')
        if r['fpga_transactions']!=12813 or r['host_calls']!=9372 or r['logical_calls']!=9336 or r['completed_language_physical']!=9372 or r['completed_visual_physical']!=3432 or r.get('transactions') or r.get('visual_transactions'):raise ValueError('Cumulative physical accounting differs')
        from m437_sequence import ORDER,NaturalSequence
        protocol_sha=json.loads((PKG/'PERFORMANCE_PLAN.json').read_bytes())['protocol_sha256']
        if r['natural_IO_protocol_sha256']!=protocol_sha:raise ValueError('Protocol differs')
        samples=r['samples']
        if len(samples)!=12 or ''.join(s['variant'] for s in samples)!=ORDER or r['warmup_samples']!=samples[:4] or r['formal_samples']!=samples[4:]:raise ValueError('Fixed sequence differs')
        board=json.loads((ROOT/'deployment/mage_vl4b/BOARD_GATE_RESULT.json').read_bytes())
        src=board['latest_m428_saved_language_board'];assert sha(ROOT/src['result'])==src['sha256']
        references=json.loads((ROOT/src['result']).read_bytes())['samples']
        sequence=NaturalSequence({},r['warm_environment_reference'],clock=lambda:0,protocol_sha=protocol_sha)
        for i,s in enumerate(samples):
            index=1;expected=references[index]
            expected_build=0x4d343431 if s['variant']=='A' else 0x4d343433
            if s.get('kernel_build')!=f'0x{expected_build:08X}':raise ValueError('Per-request kernel identity differs')
            sequence.before(i);sequence.record(s)
            if s['numerical_SHA_after_timer']!={k:expected[k] for k in ('input','visual','token','logits','keys','values')} or not all(s['exact_saved_reference'].values()):raise ValueError('Complete endpoint differs')
            if s['counts']!=expected['counts'] or s['language_physical_observed']!=781 or s['visual_physical_observed']!=(286 if index else 0):raise ValueError('Per-request retry/count differs')
            if index and [(x['layer'],x['part'],x['bytes']) for x in s['visual_staging']]!=[(a,p,2228224) for a in range(13,24) for p in ('fc1','fc2')]:raise ValueError('Candidate twenty-two stages differ')
            if not index and s['visual_staging']:raise ValueError('Original unexpectedly uses PL visual')
            for k in ('all_visual_bindings_restored','original_seven_DMA_still_resident'):
                if s.get(k) is not True:raise ValueError('Request lifecycle differs')
            if not safe_to_release(s['final_snapshot']) or s['final_snapshot']['ap_return']!=expected_build or s['sampled_memory']['observer_stopped'] is not True or s['sampled_memory']['stop_reason'] is not None:raise ValueError('Request DMA/observer unsafe')
            if set(s['timing']['stages_ms'])!={'preprocess','vision','prefill','head'} or any(not math.isfinite(t) or t<0 for t in s['timing']['stages_ms'].values()):raise ValueError('Stage timer missing/invalid')
            token=s['semantic']['token'];decision=expected['decision']
            if any(token[a]!=decision[b] for a,b in [('token_id','token_id'),('text','text'),('knife_verdict','verdict'),('knife_score','knife_score')]):raise ValueError('Constrained decision differs')
            expected_records=json.loads((ROOT/src['result']).read_bytes())['transactions'][index*781:(index+1)*781]
            if s['physical_record_SHA_after_timer']!=hashlib.sha256(json.dumps(expected_records,sort_keys=True,separators=(',',':')).encode()).hexdigest():raise ValueError('Complete post-timer language physical sequence differs')
            for k in ('physical_record_SHA_after_timer','visual_record_SHA_after_timer'):
                if not re.fullmatch('[0-9a-f]{64}',s[k]):raise ValueError('Transaction record digest missing')
        perf=json.loads((PKG/'PERFORMANCE_PLAN.json').read_bytes())
        if r.get('m443_video_numerical_source_sha256')!=perf['m443_video_sha256']:raise ValueError('M441 numerical prerequisite differs')
        switches=[(1,'A'),(2,'B'),(4,'A'),(6,'B'),(8,'A'),(9,'B'),(10,'A'),(12,'B')]
        transitions=r.get('kernel_transitions',[]);environments=r.get('kernel_switch_environment',[])
        if len(transitions)!=8 or len(environments)!=8 or r.get('kernel_switch_minimal_attempts')!=8:raise ValueError('Frozen eight transitions missing')
        prior=0x4d343433
        for row,env,(index,variant) in zip(transitions,environments,switches):
            expected=0x4d343431 if variant=='A' else 0x4d343433
            if row['index']!=index or row['variant']!=variant or row['from_build']!=prior or row['to_build']!=expected:raise ValueError('Kernel transition order differs')
            for key in ('completed','full_output_exact','original_buffer_identities_preserved','outside_request_timer'):
                if row.get(key) is not True:raise ValueError('Kernel transition incomplete '+key)
            if row.get('extra_DMA')!=0 or not safe_to_release(row['before_snapshot']) or row['before_snapshot']['ap_return']!=prior or not safe_to_release(row['completed_snapshot']) or row['completed_snapshot']['ap_return']!=expected:raise ValueError('Kernel transition ownership/Build unsafe')
            manifest='56253626a550c9c1358e805e6e3ad9b8b03c2fd9c1ff048be87c64c9f04dd5a0' if variant=='A' else '6b1942e566e78d229f0c62a69d3a1b05c00bce474fff314ecedfe014a65e50f8'
            if env['index']!=index or env['variant']!=variant or env['manifest_sha256']!=manifest or not re.fullmatch('[0-9a-f]{64}',env['environment_sha256']):raise ValueError('Switch environment proof differs')
            prior=expected
        proof=r['same_overlay_minimal_proof']
        if proof['full_output_exact'] is not True or not safe_to_release(proof['snapshot']) or proof['snapshot']['ap_return']!=0x4d343433:raise ValueError('Legal minimal missing')
        if not safe_to_release(r['final_snapshot']) or r['final_snapshot']['ap_return']!=0x4d343433 or r['stable_restore_transaction_submitted'] is not False:raise ValueError('Final/reload lifecycle differs')
        if r['head_observer_proof']['removed_observation_calls_ast_equals_original'] is not True or r['head_observer_proof']['exact_frozen_head_chains']!=8 or r['release_preflight']['status']!='READY_FOR_BOARD_PREFLIGHT':raise ValueError('Head/assets differ')
    elif r['status'] in ('FAIL','FAIL_COMPLETE_RUNTIME_CAPACITY','FAIL_UNSAFE_RETAINED','FAIL_BUDGET'):
        if r['gate_return_code']!=1 or not r['errors']:raise ValueError('Original failure not preserved')
    else:raise ValueError('Unknown saved status')
    return r

def decode(text):
    hashes=re.findall(r'(?m)^M443P_RESULT_SHA256=([0-9a-f]{64})\s*$',text);codes=re.findall(r'(?m)^M443P_SAVED_GATE_RC=([01])\s*$',text)
    chunks=re.findall(r'(?m)^M443P_RESULT_CHUNK=(\d+)/(\d+):([A-Za-z0-9+/=]+)\s*$',text)
    if len(hashes)!=1 or len(codes)!=1 or not chunks or len(chunks)!=int(chunks[0][1]):raise ValueError('Incomplete/duplicate result')
    parts=[]
    for i,(n,total,b64) in enumerate(chunks):
        p=base64.b64decode(b64,validate=True)
        if int(n)!=i or int(total)!=len(chunks) or not 0<len(p)<=900:raise ValueError('Chunk order/size differs')
        parts.append(p)
    raw=b''.join(parts);digest=hashlib.sha256(raw).hexdigest();r=check(json.loads(raw))
    if len(raw)>4<<20 or digest!=hashes[0] or r['gate_return_code']!=int(codes[0]):raise ValueError('Full raw SHA/rc differs')
    done=re.findall(r'M443P_DONE gate_rc=(\d+) export_rc=(\d+)',text)
    if done and done!=[(codes[0],'0')]:raise ValueError('Runner rc differs')
    return digest,raw,r,len(chunks)

def collect(log):
    digest,raw,r,count=decode(Path(log).read_text(encoding='utf-8-sig'))
    import m351_workflow as w
    from m441_host_io08 import atomic as saved_atomic
    w.atomic=saved_atomic
    atomic=saved_atomic
    atomic(OUT,raw,immutable=True)
    atomic(OUT.with_name('COLLECTION.json'),encoded(dict(raw_sha256=digest,chunks=count,source_log=str(log),source_log_sha256=sha(Path(log)),reexecuted=False)),immutable=True)
    sync('latest_m443_complete_request_board01',dict(status=r['status'],result=OUT.relative_to(ROOT).as_posix(),sha256=digest,manifest_sha256=r['manifest_sha256'],build_id=r['build_id'],numerical_pass=r['numerical_pass'],performance_pass=False),f'## M443 同视觉完整请求測量回收01（2026-10-11）\n\nraw {digest}，{count}个900B原字节块，原rc{r["gate_return_code"]}；{r["status"]}。固定同视觉A原M441/B新M443、4＋8全样本及计时后数值/七owner核对；只收集非性能裁决，不重跑或追加。')
    print(r['status'],digest,count)
    return r['gate_return_code']

if __name__=='__main__':
    import sys
    raise SystemExit(collect(sys.argv[1]))
