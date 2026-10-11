"""Strict raw recovery and synchronized fixed-feature quality evidence."""
import base64,copy,hashlib,json,math,re
from pathlib import Path
from m351_workflow import ROOT,BASE,HERE,atomic,encoded,sha,sync
from board_safety import safe_to_release
PKG=BASE/'candidates/M423-integrated-video-01'
OUT=BASE/'runs/M423-integrated-video-board-01/BOARD_RESULT.json'

def check(r):
    plan=json.loads((PKG/'PLAN.json').read_bytes())
    if r['manifest_sha256']!=sha(PKG/'PACKAGE_MANIFEST.json') or r['gate_level']!='integrated-fixed159-visual-language-quality' or r['build_id']!='0x4D333537' or type(r['gate_return_code']) is not int:raise ValueError('Identity/rc differs')
    if r.get('features_verified_before_overlay') is True and (r.get('selected_layers')!=[12,13] or r.get('saved_feature_source_sha256')!=plan['M420_raw_sha256'] or r.get('saved_feature_identities')!=[dict(path=plan['feature_directory']+'/'+x['path'],file_sha256=x['file_sha256'],tensor=x['tensor']) for x in plan['features']]):raise ValueError('M420 source/layers/retained features differ')
    if r['performance_pass'] or r['formal_promotion_allowed'] or r.get('expanded_24_layers',False) or not 0<=r.get('vision_forward_calls',0)<=2 or r.get('semantic_accuracy_proven',False):raise ValueError('Quality scope escaped')
    if r['status']=='PASS_M423_INTEGRATED_VIDEO_NUMERICAL':
        if r.get('vision_forward_calls')!=2 or r['gate_return_code'] or r['errors'] or r['model_forward_calls']!=2 or r['decode_calls']!=0 or r['output_budget']!=1 or r['selected_frame_indices']!=[3] or r['views']!=2:raise ValueError('Request scope differs')
        for k in ('features_verified_before_overlay','head_AST_checked_before_overlay','request_tokenizer_restored_before_prefill','original_reference_pass','candidate_finite_complete','saved_features_unchanged_after','numerical_pass','decision_consistency_pass','safe_buffers_released','stable_overlay_reloaded','boot_unchanged','cmdline_unchanged'):
            if r.get(k) is not True:raise ValueError('PASS evidence missing: '+k)
        if r['unsafe_buffers_retained'] or r['allocated_buffers']!=list(reversed(r['released_buffers'])) or [x['bytes'] for x in r['allocated_buffers']]!=plan['DMA_sizes'] or r['original_buffer_release_count']!=7:raise ValueError('DMA ownership/release differs')
        if not all(r['original_exact_comparison'].values()):raise ValueError('Original reference not exact')
        expected=json.loads((PKG/'VIDEO_EXPECTED.json').read_bytes())['baseline'];samples=r['samples']
        if len(samples)!=2 or [s['variant'] for s in samples]!=plan['variants']:raise ValueError('Sample order differs')
        ids=json.loads((PKG/'VISUAL_EXPECTED.json').read_bytes())['prompt_token_ids']
        if r['prompt_token_ids']!=ids or r['prompt']!='[TELLME_KNIFE_BINARY_V3] Knife visible? Reply exactly 1 for yes or 0 for no:':raise ValueError('Prompt differs')
        from m368_video_contract import check_call_contract
        from m368_stage_policy import FAMILIES
        total=0
        for i,s in enumerate(samples):
            counts=s['counts'];check_call_contract(counts,expected['logical_expected_macros']);total+=counts['host_calls']
            if counts['stage_bytes']!=expected['stage_bytes'] or s['physical_observed']!=counts['host_calls'] or [(x['layer'],x['family']) for x in s['families']]!=FAMILIES or s['grouped_attention_calls']!=36:raise ValueError('Full language/family/byte contract differs')
            if s['input']['shape']!=[159,2560] or s['logits']['shape']!=[151936] or s['logits']['dtype']!='float32' or s['logits']['bytes']!=607744 or s['visual']!=plan['features'][i]['tensor']:raise ValueError('Full saved-input/logits differs')
            for name in ('keys','values'):
                if len(s[name])!=36 or any({k:x[k] for k in ('shape','dtype','bytes')}!={k:y[k] for k in ('shape','dtype','bytes')} for x,y in zip(s[name],expected[name])):raise ValueError('Full KV geometry differs')
            if not safe_to_release(s['final_snapshot']) or s['final_snapshot']['ap_return']!=0x4d333537 or s['sampled_memory']['stop_reason'] is not None or s['sampled_memory']['observer_stopped'] is not True:raise ValueError('Observer/DMA unsafe')
            if i==0:
                for name in ('input','families','token','logits','keys','values','grouped_attention_calls'):
                    if s[name]!=expected[name]:raise ValueError('Original output differs: '+name)
                for name in counts:
                    if counts[name]!=expected[name]:raise ValueError('Original count/retry differs: '+name)
        if r['fpga_transactions']!=1+total+52 or r['host_calls']!=total or r['logical_calls']!=1556 or len(r['transactions'])!=total:raise ValueError('Physical accounting differs')
        if r.get('integrated_sources_checked_before_overlay') is not True or r.get('visual_provider_disposed') is not True or r.get('borrowed_buffer_identity_preserved') is not True or r.get('visual_static_cache_invalidated') is not True or r.get('borrowed_extra_DMA')!=0:raise ValueError('Borrowed integration owner proof missing')
        if r.get('integrated_visual')!=[x['tensor'] for x in plan['features']] or len(r.get('integrated_exact_comparisons',[]))!=2 or any(set(x)!=set(('input','visual','token','logits','keys','values','families','grouped_attention_calls','counts')) or not all(v is True for v in x.values()) for x in r['integrated_exact_comparisons']):raise ValueError('Full integrated references differ')
        rows=r.get('visual_transactions',[])
        if len(rows)!=52 or [(x['layer'],x['part'],x['start']) for x in rows]!=[(i,p,start) for i in (12,13) for p in ('fc1','fc2') for start in range(0,392,32)] or any(x.get('completed') is not True or not safe_to_release(x['completed_snapshot']) or x['completed_snapshot']['ap_return']!=0x4d333537 for x in rows):raise ValueError('All52 visual physical transactions not proven')
        staging=r.get('visual_staging',[])
        if len(staging)!=4 or [(x['layer'],x['part'],x['bytes']) for x in staging]!=[(i,p,2228224) for i in (12,13) for p in ('fc1','fc2')]:raise ValueError('Actual four visual stage windows differ')
        q=r['logit_comparison']
        if q['same_constrained_decision'] is not True or q['accuracy_proven'] or q['performance_proven'] or q['original']!=samples[0]['decision'] or q['candidate']!=samples[1]['decision']:raise ValueError('Decision consistency differs')
        if any(not math.isfinite(q[k]) for k in ('relative_l2','cosine','RMSE','max_abs','knife_score_delta','margin_delta')) or not 0<=q['changed_FP32_words']<=151936:raise ValueError('Invalid full logit comparison')
        if len(r['logit_files'])!=2 or [x['path'] for x in r['logit_files']]!=['original_logits.npy','layer12_13_candidate_logits.npy'] or any(x['tensor']!=s['logits'] or x['file_bytes']!=607872 or not re.fullmatch('[0-9a-f]{64}',x['file_sha256']) for x,s in zip(r['logit_files'],samples)):raise ValueError('Retained logits identity differs')
        if r['head_observer_proof']['removed_observation_calls_ast_equals_original'] is not True or r['head_observer_proof']['exact_frozen_head_chains']!=8 or r['release_preflight']['status']!='READY_FOR_BOARD_PREFLIGHT':raise ValueError('Frozen head/assets differ')
        proof=r['same_overlay_minimal_proof']
        if proof['full_output_exact'] is not True or not safe_to_release(proof['snapshot']) or proof['snapshot']['ap_return']!=0x4d333537:raise ValueError('Legal minimal not proven')
        if not safe_to_release(r['final_snapshot']) or r['final_snapshot']['ap_return']!=0x4d333537 or r['stable_restore_transaction_submitted'] is not False:raise ValueError('Final/reload lifecycle differs')
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
    hashes=re.findall(r'(?m)^M423_RESULT_SHA256=([0-9a-f]{64})\s*$',text);codes=re.findall(r'(?m)^M423_SAVED_GATE_RC=([01])\s*$',text)
    chunks=re.findall(r'(?m)^M423_RESULT_CHUNK=(\d+)/(\d+):([A-Za-z0-9+/=]+)\s*$',text)
    if len(hashes)!=1 or len(codes)!=1 or not chunks or len(chunks)!=int(chunks[0][1]):raise ValueError('Incomplete/duplicate result')
    parts=[]
    for i,(n,total,b64) in enumerate(chunks):
        p=base64.b64decode(b64,validate=True)
        if int(n)!=i or int(total)!=len(chunks) or not 0<len(p)<=900:raise ValueError('Chunk order/size differs')
        parts.append(p)
    raw=b''.join(parts);digest=hashlib.sha256(raw).hexdigest();r=check(json.loads(raw))
    if len(raw)>4<<20 or digest!=hashes[0] or r['gate_return_code']!=int(codes[0]):raise ValueError('Full raw SHA/rc differs')
    done=re.findall(r'M423_DONE gate_rc=(\d+) export_rc=(\d+)',text)
    if done and done!=[(codes[0],'0')]:raise ValueError('Runner rc differs')
    return digest,raw,r,len(chunks)

def collect(log):
    digest,raw,r,count=decode(Path(log).read_text(encoding='utf-8-sig'));atomic(OUT,raw,immutable=True)
    report='# M423 已保存视觉特征的原语言路径质量比较\n\n'+r['status']+'，原SHA '+digest+'，rc '+str(r['gate_return_code'])+'。\n\n'
    report+='实际原版和第12＋13层候选视觉复用原七DMA、各接相同语言；同159-token提示、权重、单token输出，2实际视觉前向、0Decode、0扩层。时间含诊断和哈希，仅质量，不是性能。\n\n'
    if 'logit_comparison' in r:report+='```json\n'+json.dumps(r['logit_comparison'],ensure_ascii=False,indent=2)+'\n```\n\n'
    report+='判定一致只是这份末帧两视图输入的原版/候选一致性；没有独立标注准确率、类别/位置或时序方向质量证明。原版全部logits/KV/family/事务重试须精确旧参考，候选差异记录而不拟合阈值。\n\n'
    if r['errors']:report+='失败原文：\n```json\n'+json.dumps(r['errors'],ensure_ascii=False,indent=2)+'\n```\n'
    atomic(OUT.with_name('REPORT.md'),report.encode('utf-8'),immutable=True)
    sync('latest_m423_integrated_board',dict(status=r['status'],result=OUT.relative_to(ROOT).as_posix(),sha256=digest,manifest_sha256=r['manifest_sha256'],build_id=r['build_id'],decision_consistency_pass=r.get('decision_consistency_pass',False),accuracy_proven=False,performance_pass=False),
         f'## M423 保存特征语言质量门禁（2026-10-06）\n\n原SHA {digest}，{count}个≤900B分块逐顺序和整SHA回收，rc{r["gate_return_code"]}，{r["status"]}。2实际视觉前向，原M420两份特征接同159刀具提示及原语言/LM head；原版逐位参考、候选有限输出及受限判定一致性，非独立标注准确率/性能/扩层。失败只本级闭合，回收失败只补原字节，不硬件重跑；三记录同步后再决定后续。')
    print('M423_RESULT_SYNC',digest,count);return r

def upload_names():
    old=json.loads((BASE/'candidates/M421-combination-saved-language-01/PACKAGE_MANIFEST.json').read_bytes());byname={x['path']:x for x in old['files']}
    m=json.loads((PKG/'PACKAGE_MANIFEST.json').read_bytes())
    return ['PACKAGE_MANIFEST.json']+[x['path'] for x in m['files'] if byname.get(x['path'])!=x]

def transfer():
    folder=ROOT/'tmp/m42301';m=json.loads((PKG/'PACKAGE_MANIFEST.json').read_bytes());receipts=[]
    for name in upload_names():
        size=(PKG/name).stat().st_size;count=(size+899)//900;prefix='upload_'+name.replace('.','_')
        final=(folder/(prefix+'_final.log')).read_text(encoding='utf-8-sig')
        if 'M212_CHUNKED_FILE_PASS' not in final or sha(PKG/name) not in final:raise ValueError('Transfer SHA missing')
        chunks=sorted(folder.glob(prefix+'_chunk_*.log'))
        if len(chunks)!=count:raise ValueError('Transfer receipt count differs')
        for i,p in enumerate(chunks,1):
            if not re.search(r'M212_CHUNK_PASS\s+'+str(i)+r'\s+'+str(count)+r'\s+'+str(min(i*900,size))+r'\s',p.read_text(encoding='utf-8-sig')):raise ValueError('Transfer sequence differs')
        receipts.append(dict(path=name,sha256=sha(PKG/name),chunks=count))
    marker=f'M423_ASSEMBLY_PASS {sha(PKG/"PACKAGE_MANIFEST.json")} {m["file_count"]} {m["total_bytes"]}'
    if marker not in (folder/'assembly.log').read_text(encoding='utf-8-sig') or '__M423_SYNTAX_RC_0__' not in (folder/'syntax.log').read_text(encoding='utf-8-sig'):raise ValueError('Assembly/bash receipt missing')
    r=dict(status='PASS_M423_MANIFEST_FIRST_HASHED_TRANSFER',manifest_sha256=sha(PKG/'PACKAGE_MANIFEST.json'),receipts=receipts,assembled_existing_assets_only=True,gate_started=False)
    p=BASE/'runs/M423-integrated-transfer-01/RESULT.json';atomic(p,encoded(r),immutable=True)
    sync('latest_m423_integrated_transfer',dict(status=r['status'],result=p.relative_to(ROOT).as_posix(),sha256=sha(p),manifest_sha256=r['manifest_sha256']),f'## M423 保存特征语言包传输（2026-10-06）\n\nSHA {sha(p)}；manifest-first900B全部回执逐文件SHA、复用旧同SHA原参考资产完整组装和bash-n通过，尚未执行。')
    print('M423_TRANSFER_SYNC',sha(p))

if __name__=='__main__':
    import sys
    if sys.argv[1:]==['transfer']:transfer()
    elif len(sys.argv)==3 and sys.argv[1]=='collect':collect(sys.argv[2])
    else:raise SystemExit('transfer | collect LOG')
