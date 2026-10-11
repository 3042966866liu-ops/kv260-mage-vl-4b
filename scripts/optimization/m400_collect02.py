"""Saved-only exact last31 chain recovery; never executes a board gate."""
import base64
import hashlib
import json
import re
import sys
from m351_workflow import ROOT,BASE,sha,atomic,sync
from board_safety import safe_to_release
from m400_tail_layer_scope import PLAN
PKG=BASE/'candidates/M400-tail-layer-02'
PRIOR='ca4a8d45e5e73190ee476958886cc97eafb42f6476d1c440fcbae9d99b2400ef'

def validate_layer(r):
    pin=json.loads((PKG/'TAIL_LAYER_PREREQUISITE.json').read_text(encoding='utf-8'))
    c=r['layer_scope'];f=pin['reference_manifest']['fixtures']
    if r['original_reference_sha256']!=PRIOR or pin['raw_sha256']!=PRIOR or c['reference_sha256']!=PRIOR:raise ValueError('Original reference pin differs')
    if r['chain_prerequisite_sha256']!=pin['chain_raw_sha256'] or pin['chain_raw_sha256']!='924ae716e4e399b6f94f522d279b5f6472328bbb6049ebfb6d16004d5f95c992':raise ValueError('Prior three-chain pin differs')
    original=BASE/'runs/M398-tail-reference-board-01/BOARD_RESULT.json'
    chain=BASE/'runs/M399-tail-chain-board-01/BOARD_RESULT.json'
    if sha(original)!=PRIOR or sha(chain)!=pin['chain_raw_sha256']:raise ValueError('Recovered prerequisite drift')
    if not c['closed'] or c['retained'] or not c['invoked'] or not c['reference_maps_released'] or not c['binding_callback_removed'] or not c['original_family_restored'] or c['reference_files_checked']!=11:raise ValueError('Layer owner/maps/binding closure differs')
    if c['extra_DMA'] or c['parser_workers']!=1 or c['PS_prefetch'] or c['SiLU_workspace'] or c['candidate_full_model_executed'] or c['performance_pass']:raise ValueError('Layer scope exceeded')
    expected=dict(families=pin['expected_families'],key=pin['expected_key'],value=pin['expected_value'],
                  attended_full=f['attended_full']['tensor'],hidden_tail=f['hidden_tail']['tensor'],final_norm=f['final_norm']['tensor'],
                  full_QKV_KV_SHA_equal=True,full_attention_and_tail_tensors_bitwise_equal=True,
                  last_layer=35,original_tokens=159,tail_start=128,tail_tokens=31,grouped_attention_calls=1,LM_head_executed=False)
    if r['layer_result']!=expected or c['layer_result']!=expected or c['family_rows']!=expected['families']:raise ValueError('Full layer numerical tensor contract differs')
    if r['transactions']!=pin['expected_transactions']:raise ValueError('Physical layer identities/byte counts differ')
    d=r['layer_call_delta']
    expected_counts=dict(logical_calls=8,host_calls=8,stage_bytes=53624832,scale_retry_count=0,pipeline_retry_launches=0,logical_expected_macros=81920000,expected_macros=81920000)
    if d!=expected_counts:raise ValueError('Layer calls/staging/macros/retry differs')
    e=r['layer_runtime_evidence']
    if any(e[k]!=v for k,v in expected_counts.items()) or e['scale_attempts']!=pin['expected_scale_attempts']:raise ValueError('Original runtime counters/scale choices differ')
    if r['isolated_layer_calls']!=1:raise ValueError('Independent layer count differs')

def decode(text):
    hs=re.findall(r'(?m)^M400_RESULT_SHA256=([0-9a-f]{64})\s*$',text);cs=re.findall(r'(?m)^M400_SAVED_GATE_RC=([01])\s*$',text)
    pieces=re.findall(r'(?m)^M400_RESULT_CHUNK=(\d+)/(\d+):([A-Za-z0-9+/=]+)\s*$',text)
    if len(hs)!=1 or len(cs)!=1 or not pieces or len(pieces)!=int(pieces[0][1]):raise ValueError('Incomplete/duplicate raw')
    data=[]
    for i,(n,total,b64) in enumerate(pieces):
        p=base64.b64decode(b64,validate=True)
        if int(n)!=i or int(total)!=len(pieces) or not 0<len(p)<=900:raise ValueError('Order/size differs')
        data.append(p)
    raw=b''.join(data);digest=hashlib.sha256(raw).hexdigest();r=json.loads(raw)
    if digest!=hs[0] or type(r['gate_return_code']) is not int or r['gate_return_code']!=int(cs[0]):raise ValueError('SHA/code differs')
    if r['manifest_sha256']!=sha(PKG/'PACKAGE_MANIFEST.json') or r['case']!='B1' or r['build_id']!='0x4D333537' or r['gate_level']!='sealed-DMA-isolated-layer35-fullAttention-last31':raise ValueError('Package/scope differs')
    if any(r[k] for k in ('memory_capacity_proven','performance_pass','formal_promotion_allowed')):raise ValueError('Improperly promoted')
    done=re.findall(r'M400_DONE case=B1 gate_rc=(\d+) export_rc=(\d+)',text)
    if done and done!=[(cs[0],'0')]:raise ValueError('Original/export code differs')
    if r.get('source_precheck_before_hardware_import')!={'original_source_sha256': '24f419ea8e0f130cefc8eb51f916dca3fb945b84f0dc8e73dec9f5376be3ad09', 'frozen_sha256': 'fc5543e48aecc49dad0c08eb5efefa82a12ed607088b30cbba1a9b792d06f40b', 'deterministic_source_equal': True, 'same_interpreter_AST_arithmetic_equal': True, 'uses_ast_unparse': False, 'imports_numpy_or_pynq': False}:raise ValueError('Pre-resource source proof differs')
    if r['status']=='PASS_M400_TAIL_LAYER_NUMERICAL':
        if r['gate_return_code'] or r['errors'] or r['unsafe_buffers_retained'] or not r['safe_buffers_released'] or not r['numerical_pass']:raise ValueError('Incomplete PASS')
        if [x['bytes'] for x in r['allocated_buffers']]!=[6963200]*4+[389152,2621440,2621440] or r['released_buffers']!=r['allocated_buffers'][::-1] or r['original_buffer_release_count']!=7:raise ValueError('Owned DMA closure differs')
        if r['model_forward_calls'] or r.get('vision_forward_calls',0) or r['blocked_inference_attempts'] or r['candidate_full_model_executed'] or not r['layer_numerical_pass'] or any(r.get(k,False) for k in ('fixed_video_diagnostic_pass','candidate_numerical_pass','reference_capture_pass','full_model','video','promoted')):raise ValueError('Independent layer escaped scope')
        if r['fpga_transactions']!=9 or r['logical_calls']!=8 or r['host_calls']!=8:raise ValueError('Actual launch count differs')
        if r['sampled_memory']['stop_reason'] or not r['sampled_memory']['observer_stopped'] or not safe_to_release(r['final_snapshot']) or r['final_snapshot']['ap_return']!=0x4d333537:raise ValueError('Completion/monitor differs')
        if not all(r[k] for k in ('stable_overlay_reloaded','boot_unchanged','cmdline_unchanged','tokenizer_single_parse_reused','patch_registry_cleared')) or r['stable_bit_sha256']!='1cbf7bbb86cfe64c2349418d5a15890d735bea3fa4c999060c8a9da9ac3206ac':raise ValueError('Restore/identity differs')
        if r['ps_prefetch_enabled'] or r['worker_started'] or not r['scope_weakref_dead'] or r['silu_workspace_enabled'] or r['extra_pynq_allocations'] or r['original_parser_workers']!=1:raise ValueError('Original-only variant/lifetime differs')
        validate_layer(r)
        if r['diagnostic_ps_growth_limit_bytes']!=1024<<20 or r['diagnostic_ps_available_margin_bytes']!=64<<20 or r['additional_cma_requests_allowed']:raise ValueError('Diagnostic policy differs')
        counts=r['stage_memory'][0]['cma_counts']
        for point in r['stage_memory']:
            decision=point['admission']
            if decision is None:continue
            if point['cma_counts']!=counts or not 0<=decision['observed_rss_growth_bytes']<=1024<<20 or decision['diagnostic_additional_explicit_cma_bytes'] or decision['required_mem_available_bytes']!=(1024<<20)-decision['observed_rss_growth_bytes']+(64<<20) or decision['mem_available_bytes']<decision['required_mem_available_bytes']:raise ValueError('Sealed memory decision differs')
        if not r['same_overlay_minimal_proof']['full_output_exact'] or r['same_overlay_minimal_proof']['output_bytes']!=4096:raise ValueError('Same-overlay minimal absent')
    elif r['gate_return_code']!=1 or not r['errors']:raise ValueError('Unknown/empty failure')
    return digest,raw,r

def collect(path):
    digest,raw,r=decode(path.read_text(encoding='utf-8-sig'));out=BASE/'runs/M400-tail-layer-board-02/BOARD_RESULT.json';atomic(out,raw,immutable=True)
    passed=r['status']=='PASS_M400_TAIL_LAYER_NUMERICAL'
    detail='原layer35完整159QKV/Attention/KV及末31后三投影/hidden/norm精确一致，8逻辑/8层物理加minimal9，七DMA/reference maps/owner安全释放与稳定恢复。仅单层，未固定文本/候选视频或性能。' if passed else '本级失败，保持原返回码和资源；只允许本单层级调试或保存结果回收，不解锁固定文本。'
    sync('latest_m400_tail_layer_board02',dict(status=r['status'],result=out.relative_to(ROOT).as_posix(),sha256=digest,layer_numerical_pass=passed,candidate_full_model_executed=False,performance_pass=False),
         f'## M400 末层组合板端结果（2026-10-04）\n\nBuild0x4D333537，原rc{r["gate_return_code"]}，{r["status"]}，raw `{digest}`。{detail}生产政策/稳定回滚保持。')
    print(json.dumps(dict(status=r['status'],sha256=digest,errors=r['errors'],layer_numerical_pass=passed,physical_calls=r['fpga_transactions'])))

if __name__=='__main__':collect(ROOT/sys.argv[1])
