"""Saved-only exact last31 chain recovery; never executes a board gate."""
import base64
import hashlib
import json
import re
import sys
from m351_workflow import ROOT,BASE,sha,atomic,sync
from board_safety import safe_to_release
from m399_tail_chain_scope import PLAN
PKG=BASE/'candidates/M399-tail-chain-01'
PRIOR='ca4a8d45e5e73190ee476958886cc97eafb42f6476d1c440fcbae9d99b2400ef'

def validate_chains(r):
    pin=json.loads((PKG/'TAIL_CHAIN_PREREQUISITE.json').read_text(encoding='utf-8'));fixtures=pin['reference_manifest']['fixtures']
    c=r['chain_scope']
    if r['original_reference_sha256']!=PRIOR or pin['raw_sha256']!=PRIOR or c['reference_sha256']!=PRIOR:raise ValueError('Reference raw pin differs')
    if not c['closed'] or c['retained'] or not c['reference_maps_released'] or c['reference_files_checked']!=7 or c['extra_DMA'] or c['original_parser_workers']!=1 or c['PS_prefetch'] or c['SiLU_workspace'] or c['full_model_candidate_executed'] or c['performance_pass']:raise ValueError('Independent chain scope/lifetime differs')
    if c['chains']!=r['last31_chains'] or len(c['chains'])!=3:raise ValueError('Three chains incomplete')
    original_path=BASE/'runs/M398-tail-reference-board-01/BOARD_RESULT.json'
    if sha(original_path)!=PRIOR:raise ValueError('Recovered original drift')
    original=json.loads(original_path.read_text(encoding='utf-8'))
    audit_path=BASE/'runs/M396-last-layer-tail-audit-01/RESULT.json'
    if sha(audit_path)!='f6ffc560988c79087bd4be8f5200945d89c4af701abdad6e64327505b10be56a':raise ValueError('Frozen chain macro audit differs')
    expected_macros=sum(row['per_transaction_expected_macros'] for row in json.loads(audit_path.read_text(encoding='utf-8'))['costs'])
    expected_transactions=[]
    for row,(family,source,goldens) in zip(c['chains'],PLAN):
        output={'model.language_model.layers.35.'+k:fixtures[n]['tensor'] for k,n in goldens.items()}
        if row!=dict(layer=35,family=family,original_token_start=128,local_token_start=0,tokens=31,input=fixtures[source]['tensor'],output=output,full_output_bitwise_equal=True):raise ValueError('Exact last31 full output/tensor mapping differs')
        matching=[t for t in original['transactions'] if t['layer']==35 and t['family']==family]
        expected_transactions.append(matching[-1])
    if r['transactions']!=expected_transactions:raise ValueError('Physical chain identities/byte counts differ')
    d=r['chain_call_delta']
    if d['logical_calls']!=3 or d['host_calls']!=3 or d['stage_bytes']!=45268992 or d['scale_retry_count'] or d['pipeline_retry_launches'] or d['logical_expected_macros']!=expected_macros or d['expected_macros']!=expected_macros:raise ValueError('Chain calls/staging/retry differs')
    e=r['chain_runtime_evidence']
    if e['logical_calls']!=3 or e['host_calls']!=3 or e['stage_bytes']!=45268992 or e['scale_retry_count'] or e['pipeline_retry_launches'] or e['logical_expected_macros']!=d['logical_expected_macros'] or e['expected_macros']!=d['expected_macros']:raise ValueError('Original runtime counters differ')

def decode(text):
    hs=re.findall(r'(?m)^M399_RESULT_SHA256=([0-9a-f]{64})\s*$',text);cs=re.findall(r'(?m)^M399_SAVED_GATE_RC=([01])\s*$',text)
    pieces=re.findall(r'(?m)^M399_RESULT_CHUNK=(\d+)/(\d+):([A-Za-z0-9+/=]+)\s*$',text)
    if len(hs)!=1 or len(cs)!=1 or not pieces or len(pieces)!=int(pieces[0][1]):raise ValueError('Incomplete/duplicate raw')
    data=[]
    for i,(n,total,b64) in enumerate(pieces):
        p=base64.b64decode(b64,validate=True)
        if int(n)!=i or int(total)!=len(pieces) or not 0<len(p)<=900:raise ValueError('Order/size differs')
        data.append(p)
    raw=b''.join(data);digest=hashlib.sha256(raw).hexdigest();r=json.loads(raw)
    if digest!=hs[0] or type(r['gate_return_code']) is not int or r['gate_return_code']!=int(cs[0]):raise ValueError('SHA/code differs')
    if r['manifest_sha256']!=sha(PKG/'PACKAGE_MANIFEST.json') or r['case']!='B1' or r['build_id']!='0x4D333537' or r['gate_level']!='sealed-DMA-isolated-last31-three-chains':raise ValueError('Package/scope differs')
    if any(r[k] for k in ('memory_capacity_proven','performance_pass','formal_promotion_allowed')):raise ValueError('Improperly promoted')
    done=re.findall(r'M399_DONE case=B1 gate_rc=(\d+) export_rc=(\d+)',text)
    if done and done!=[(cs[0],'0')]:raise ValueError('Original/export code differs')
    if r['status']=='PASS_M399_LAST31_CHAIN_NUMERICAL':
        if r['gate_return_code'] or r['errors'] or r['unsafe_buffers_retained'] or not r['safe_buffers_released'] or not r['numerical_pass']:raise ValueError('Incomplete PASS')
        if [x['bytes'] for x in r['allocated_buffers']]!=[6963200]*4+[389152,2621440,2621440] or r['released_buffers']!=r['allocated_buffers'][::-1] or r['original_buffer_release_count']!=7:raise ValueError('Owned DMA closure differs')
        if r['model_forward_calls'] or r.get('vision_forward_calls',0) or r['blocked_inference_attempts'] or r['candidate_full_model_executed'] or not r['chain_numerical_pass'] or any(r.get(k,False) for k in ('fixed_video_diagnostic_pass','candidate_numerical_pass','reference_capture_pass','full_model','video','promoted')):raise ValueError('Independent chain escaped scope')
        if r['fpga_transactions']!=4 or r['logical_calls']!=3 or r['host_calls']!=3:raise ValueError('Actual launch count differs')
        if r['sampled_memory']['stop_reason'] or not r['sampled_memory']['observer_stopped'] or not safe_to_release(r['final_snapshot']) or r['final_snapshot']['ap_return']!=0x4d333537:raise ValueError('Completion/monitor differs')
        if not all(r[k] for k in ('stable_overlay_reloaded','boot_unchanged','cmdline_unchanged','tokenizer_single_parse_reused','patch_registry_cleared')) or r['stable_bit_sha256']!='1cbf7bbb86cfe64c2349418d5a15890d735bea3fa4c999060c8a9da9ac3206ac':raise ValueError('Restore/identity differs')
        if r['ps_prefetch_enabled'] or r['worker_started'] or not r['scope_weakref_dead'] or r['silu_workspace_enabled'] or r['extra_pynq_allocations'] or r['original_parser_workers']!=1:raise ValueError('Original-only variant/lifetime differs')
        validate_chains(r)
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
    digest,raw,r=decode(path.read_text(encoding='utf-8-sig'));out=BASE/'runs/M399-tail-chain-board-01/BOARD_RESULT.json';atomic(out,raw,immutable=True)
    passed=r['status']=='PASS_M399_LAST31_CHAIN_NUMERICAL'
    detail='三个原末31 chain完整输出精确一致、3逻辑/3物理加minimal4，七DMA与参考map安全释放/稳定恢复。只解锁独立单层准备，未完成候选模型或性能。' if passed else '本级失败，保持原返回码和资源状态；仅本级故障/保存结果回收，不解锁单层。'
    sync('latest_m399_tail_chain_board',dict(status=r['status'],result=out.relative_to(ROOT).as_posix(),sha256=digest,chain_numerical_pass=passed,candidate_full_model_executed=False,performance_pass=False),
         f'## M399 三个末31 chain板端结果（2026-10-04）\n\nBuild0x4D333537，原rc{r["gate_return_code"]}，{r["status"]}，raw `{digest}`。{detail}生产政策/稳定回滚保持。')
    print(json.dumps(dict(status=r['status'],sha256=digest,errors=r['errors'],chain_numerical_pass=passed,physical_calls=r['fpga_transactions'])))

if __name__=='__main__':collect(ROOT/sys.argv[1])
