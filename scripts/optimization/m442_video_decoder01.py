"""Strict raw recovery and synchronized fixed-feature quality evidence."""
import base64,copy,hashlib,json,math,re
from pathlib import Path
from m351_workflow import ROOT,BASE,HERE,atomic,encoded,sha,sync
from board_safety import safe_to_release
PKG=BASE/'candidates/M442-live-parser-video-01'
OUT=BASE/'runs/M442-live-parser-video-board-01/BOARD_RESULT.json'

def check(r):
    plan=json.loads((PKG/'PLAN.json').read_bytes())
    if r['manifest_sha256']!=sha(PKG/'PACKAGE_MANIFEST.json') or r['gate_level']!='integrated-fixed159-visual-language-quality' or r['build_id']!='0x4D343431' or type(r['gate_return_code']) is not int:raise ValueError('Identity/rc differs')
    if r.get('features_verified_before_overlay') is True and (r.get('selected_layers')!=plan['selected_layers'] or r.get('saved_feature_source_sha256')!=plan['M427_raw_sha256'] or r.get('saved_feature_identities')!=[dict(path=plan['feature_directories'][x['source']]+'/'+x['path'],file_sha256=x['file_sha256'],tensor=x['tensor']) for x in plan['features']]):raise ValueError('M427 accepted late11 source/layers/retained features differ')
    if r.get('temperature_measurement_enabled') is not False:raise ValueError('Temperature measurement forbidden')
    if r['performance_pass'] or r['formal_promotion_allowed'] or r.get('expanded_24_layers',False) or not 0<=r.get('vision_forward_calls',0)<=1 or r.get('semantic_accuracy_proven',False):raise ValueError('Quality scope escaped')
    if r['status']=='PASS_M442V_INTEGRATED_VIDEO_NUMERICAL':
        if r.get('parser_candidate_sha256')!=sha(PKG/'m442_output_parser06.py') or r.get('parser_component_sha256')!=sha(PKG/'PARSER_COMPONENT.json') or r.get('parser_workers')!=1 or r.get('kernel_changed') is not False:raise ValueError('New parser/worker/kernel identity differs')
        if r.get('vision_forward_calls')!=1 or r['gate_return_code'] or r['errors'] or r['model_forward_calls']!=1 or r['decode_calls']!=0 or r['output_budget']!=1 or r['selected_frame_indices']!=[3] or r['views']!=2:raise ValueError('Request scope differs')
        for k in ('features_verified_before_overlay','head_AST_checked_before_overlay','request_tokenizer_restored_before_prefill','original_reference_pass','candidate_finite_complete','saved_features_unchanged_after','numerical_pass','decision_consistency_pass','safe_buffers_released','stable_overlay_reloaded','boot_unchanged','cmdline_unchanged'):
            if r.get(k) is not True:raise ValueError('PASS evidence missing: '+k)
        if r['unsafe_buffers_retained'] or r['allocated_buffers']!=list(reversed(r['released_buffers'])) or [x['bytes'] for x in r['allocated_buffers']]!=plan['DMA_sizes'] or r['original_buffer_release_count']!=7:raise ValueError('DMA ownership/release differs')
        if not all(r['original_exact_comparison'].values()):raise ValueError('Original reference not exact')
        expected=json.loads((PKG/'VIDEO_EXPECTED.json').read_bytes())['baseline'];samples=r['samples']
        if len(samples)!=1 or [s['variant'] for s in samples]!=plan['variants'][1:]:raise ValueError('Sample order differs')
        ids=json.loads((PKG/'VISUAL_EXPECTED.json').read_bytes())['prompt_token_ids']
        if r['prompt_token_ids']!=ids or r['prompt']!='[TELLME_KNIFE_BINARY_V3] Knife visible? Reply exactly 1 for yes or 0 for no:':raise ValueError('Prompt differs')
        from m368_video_contract import check_call_contract
        from m368_stage_policy import FAMILIES
        total=0
        for i,s in enumerate(samples,1):
            counts=s['counts'];check_call_contract(counts,expected['logical_expected_macros']);total+=counts['host_calls']
            if counts['stage_bytes']!=expected['stage_bytes'] or s['physical_observed']!=counts['host_calls'] or [(x['layer'],x['family']) for x in s['families']]!=FAMILIES or s['grouped_attention_calls']!=36:raise ValueError('Full language/family/byte contract differs')
            if s['input']['shape']!=[159,2560] or s['logits']['shape']!=[151936] or s['logits']['dtype']!='float32' or s['logits']['bytes']!=607744 or s['visual']!=plan['features'][i]['tensor']:raise ValueError('Full saved-input/logits differs')
            for name in ('keys','values'):
                if len(s[name])!=36 or any({k:x[k] for k in ('shape','dtype','bytes')}!={k:y[k] for k in ('shape','dtype','bytes')} for x,y in zip(s[name],expected[name])):raise ValueError('Full KV geometry differs')
            if not safe_to_release(s['final_snapshot']) or s['final_snapshot']['ap_return']!=0x4d343431 or s['sampled_memory']['stop_reason'] is not None or s['sampled_memory']['observer_stopped'] is not True:raise ValueError('Observer/DMA unsafe')
        if r['fpga_transactions']!=1+total+286 or r['host_calls']!=total or r['logical_calls']!=778 or len(r['transactions'])!=total:raise ValueError('Physical accounting differs')
        from m429_pl_range import SavedWireCheck
        board=json.loads((ROOT/'deployment/mage_vl4b/BOARD_GATE_RESULT.json').read_bytes())
        language_e=board['latest_m428_saved_language_board'];software_e=board['latest_m427_half_software_board']
        for e in (language_e,software_e):
            if sha(ROOT/e['result'])!=e['sha256']:raise ValueError('Frozen comparison source differs')
        language=json.loads((ROOT/language_e['result']).read_bytes())
        software=json.loads((ROOT/software_e['result']).read_bytes())
        accepted=next(x for x in software['ranges'] if x['name']=='late_13_23')
        keys=('input','visual','token','logits','keys','values','families','grouped_attention_calls','counts','decision')
        if any(any(s[k]!=old[k] for k in keys) for s,old in zip(samples,language['samples'][1:])) or r['transactions']!=language['transactions'][language['samples'][0]['counts']['host_calls']:]:raise ValueError('Complete accepted M428 sample/physical retry sequence differs')
        for k in ('integrated_sources_checked_before_overlay','visual_provider_disposed','borrowed_buffer_identity_preserved','visual_static_cache_invalidated','visual_bindings_restored'):
            if r.get(k) is not True:raise ValueError('Borrowed integration owner proof missing:'+k)
        if r.get('borrowed_extra_DMA')!=0 or r.get('peak_live_visual_layer_scopes')!=1 or r.get('visual_matched_wire_batches')!=286:raise ValueError('Exact borrowed visual scope required')
        if r.get('integrated_visual')!=[plan['features'][1]['tensor']] or len(r.get('integrated_exact_comparisons',[]))!=1 or any(set(x)!=set(('input','visual','token','logits','keys','values','families','grouped_attention_calls','counts')) or not all(v is True for v in x.values()) for x in r['integrated_exact_comparisons']):raise ValueError('Complete integrated references missing')
        expected_boundaries=[dict(layer=i,tensor=x['candidate']) for i,x in enumerate(accepted['boundary_comparison'])]
        if r.get('integrated_boundaries')!=expected_boundaries:raise ValueError('All24 complete visual boundaries differ')
        guard=SavedWireCheck(accepted['reference_batches'],lambda *x:None)
        rows=r.get('visual_transactions',[])
        if len(rows)!=286 or [(x['layer'],x['part'],x['start'],x['shift']) for x in rows]!=list(guard.expected_position):raise ValueError('All286 saved visual transaction identities required')
        for x in rows:
            ref=accepted['reference_batches'][str(x['layer'])][x['part']][x['start']//32]
            if x.get('completed') is not True or x['input_bytes']!=ref['input_bytes'] or x['output_bytes']!=ref['output_bytes'] or not safe_to_release(x['completed_snapshot']) or x['completed_snapshot']['ap_return']!=0x4d343431:raise ValueError('Visual DMA completion/build/bytes unproven')
        staging=r.get('visual_staging',[])
        if [(x['layer'],x['part'],x['bytes']) for x in staging]!=[(i,p,2228224) for i in range(13,24) for p in ('fc1','fc2')]:raise ValueError('All22 actual visual windows differ')
        if r.get('saved_reference_variant')!='late13_23_candidate' or samples[0]['decision']!=language['samples'][1]['decision']:raise ValueError('Complete accepted baseline decision differs')
        files=r['logit_files']
        if len(files)!=1 or files[0]['path']!='late13_23_candidate_logits.npy' or files[0]['tensor']!=samples[0]['logits'] or files[0]['file_bytes']!=607872 or not re.fullmatch('[0-9a-f]{64}',files[0]['file_sha256']):raise ValueError('Saved complete logits identity differs')
        if r.get('prior_fixed_text_raw_sha256')!='f508e2ccf1b274aea12072f2ee9b0be44050712c35ca67a80f633fb07e02ed8d' or r.get('source_compatibility_checked_before_overlay') is not True or r.get('prior_board_sha256')!='0b416a17669ae1a5690a62650237ce6ced33f922017625f685401ca806e2273d':raise ValueError('Actual M441 prerequisite differs')
        if r['head_observer_proof']['removed_observation_calls_ast_equals_original'] is not True or r['head_observer_proof']['exact_frozen_head_chains']!=8 or r['release_preflight']['status']!='READY_FOR_BOARD_PREFLIGHT':raise ValueError('Frozen head/assets differ')
        proof=r['same_overlay_minimal_proof']
        if proof['full_output_exact'] is not True or not safe_to_release(proof['snapshot']) or proof['snapshot']['ap_return']!=0x4d343431:raise ValueError('Legal minimal not proven')
        if not safe_to_release(r['final_snapshot']) or r['final_snapshot']['ap_return']!=0x4d343431 or r['stable_restore_transaction_submitted'] is not False:raise ValueError('Final/reload lifecycle differs')
        for row in r['stage_memory']:
            a=row['admission']
            if a is not None:
                growth=max(0,row['memory']['process_bytes']['VmRSS']-next(x['memory']['process_bytes']['VmRSS'] for x in r['stage_memory'] if x['label']=='diagnostic-admission-after-seven-real-buffers'))
                required=max(0,(1024<<20)-growth)+(64<<20)
                if a['diagnostic_additional_explicit_cma_bytes']!=0 or a['observed_rss_growth_bytes']!=growth or growth>1024<<20 or a['required_mem_available_bytes']!=required or a['mem_available_bytes']<required:raise ValueError('Actual ordinary memory guard differs')
    elif r['status'] in ('FAIL','FAIL_COMPLETE_RUNTIME_CAPACITY','FAIL_UNSAFE_RETAINED','FAIL_BUDGET'):
        if r['gate_return_code']!=1 or not r['errors']:raise ValueError('Failure without original rc/error')
    else:raise ValueError('Unknown status')
    return r

def decode(text):
    hashes=re.findall(r'(?m)^M442V_RESULT_SHA256=([0-9a-f]{64})\s*$',text);codes=re.findall(r'(?m)^M442V_SAVED_GATE_RC=([01])\s*$',text)
    chunks=re.findall(r'(?m)^M442V_RESULT_CHUNK=(\d+)/(\d+):([A-Za-z0-9+/=]+)\s*$',text)
    if len(hashes)!=1 or len(codes)!=1 or not chunks or len(chunks)!=int(chunks[0][1]):raise ValueError('Incomplete/duplicate result')
    parts=[]
    for i,(n,total,b64) in enumerate(chunks):
        p=base64.b64decode(b64,validate=True)
        if int(n)!=i or int(total)!=len(chunks) or not 0<len(p)<=900:raise ValueError('Chunk order/size differs')
        parts.append(p)
    raw=b''.join(parts);digest=hashlib.sha256(raw).hexdigest();r=check(json.loads(raw))
    if len(raw)>4<<20 or digest!=hashes[0] or r['gate_return_code']!=int(codes[0]):raise ValueError('Full raw SHA/rc differs')
    done=re.findall(r'M442V_DONE gate_rc=(\d+) export_rc=(\d+)',text)
    if done and done!=[(codes[0],'0')]:raise ValueError('Runner rc differs')
    return digest,raw,r,len(chunks)
