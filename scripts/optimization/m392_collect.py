"""Strict saved single-layer outputs and workspace/DMA lifetime, no gate execution."""
import base64
import hashlib
import json
import re
import sys
from m351_workflow import ROOT,BASE,sha,atomic,sync
from board_safety import safe_to_release
PKG=BASE/'candidates/M392-silu-layer-02'

def decode(text):
    hs=re.findall(r'(?m)^M392_RESULT_SHA256=([0-9a-f]{64})\s*$',text);cs=re.findall(r'(?m)^M392_SAVED_GATE_RC=([01])\s*$',text)
    pieces=re.findall(r'(?m)^M392_RESULT_CHUNK=(\d+)/(\d+):([A-Za-z0-9+/=]+)\s*$',text)
    if len(hs)!=1 or len(cs)!=1 or not pieces or len(pieces)!=int(pieces[0][1]):raise ValueError('Incomplete/duplicate raw')
    data=[]
    for i,(n,total,b64) in enumerate(pieces):
        p=base64.b64decode(b64,validate=True)
        if int(n)!=i or int(total)!=len(pieces) or not 0<len(p)<=900:raise ValueError('Order/size differs')
        data.append(p)
    raw=b''.join(data);d=hashlib.sha256(raw).hexdigest();r=json.loads(raw)
    if d!=hs[0] or type(r['gate_return_code']) is not int or r['gate_return_code']!=int(cs[0]):raise ValueError('SHA/code differs')
    if r['manifest_sha256']!=sha(PKG/'PACKAGE_MANIFEST.json') or r['case']!='B1' or r['build_id']!='0x4D333537' or r['gate_level']!='sealed-DMA-SiLU-workspace-single-layer-numerical':raise ValueError('Package/scope differs')
    if any(r[k] for k in ('memory_capacity_proven','performance_pass','formal_promotion_allowed')):raise ValueError('Improperly promoted')
    done=re.findall(r'M392_DONE case=B1 gate_rc=(\d+) export_rc=(\d+)',text)
    if done and done!=[(cs[0],'0')]:raise ValueError('Original/export code differs')
    if r['status']=='PASS_M392_SILU_LAYER_NUMERICAL':
        if r['gate_return_code'] or r['errors'] or r['unsafe_buffers_retained'] or not r['safe_buffers_released'] or not r['numerical_pass']:raise ValueError('Incomplete PASS')
        if [x['bytes'] for x in r['allocated_buffers']]!=[6963200]*4+[389152,2621440,2621440] or r['released_buffers']!=r['allocated_buffers'][::-1] or r['original_buffer_release_count']!=7:raise ValueError('Owned DMA closure differs')
        expected=json.loads((PKG/'LAYER_EXPECTED.json').read_text(encoding='utf-8'))['baseline']
        if r['model_forward_calls']!=1 or r['layer_result']!=expected or not all(r['exact_comparison'].values()) or r['blocked_inference_attempts']:raise ValueError('Independent layer reference differs')
        if r['fpga_transactions']!=1+expected['host_calls'] or len(r['transactions'])!=expected['host_calls']:raise ValueError('Launch count differs')
        if any(t['layer']!=0 or t['family'] not in ('q','kv','attention_out','gate_up','mlp_down') for t in r['transactions']):raise ValueError('Transaction escaped')
        if r['sampled_memory']['stop_reason'] or not r['sampled_memory']['observer_stopped'] or not safe_to_release(r['final_snapshot']) or r['final_snapshot']['ap_return']!=0x4d333537:raise ValueError('Completion/monitor differs')
        if not all(r[k] for k in ('stable_overlay_reloaded','boot_unchanged','cmdline_unchanged','tokenizer_single_parse_reused','patch_registry_cleared')):raise ValueError('Restore/identity differs')
        if r['component_prerequisite_sha256']!='377ac2cf8b082eadbffad43c440ff32fcb24d377280a96e6e56f9d07f2efb5b4' or r['ps_prefetch_enabled'] or r['worker_started'] or not r['scope_weakref_dead'] or not r['silu_workspace_enabled'] or r['extra_pynq_allocations'] or r['original_parser_workers']!=1:raise ValueError('Variant/lifetime differs')
        s=r['silu_scope']
        if s!=dict(calls=1,closed=True,retained=False,events=['before-layer-workspace-scope','before-silu','after-mlp-down-before-reuse','before-workspace-close'],workspace_bytes=6187008,workspace_object_released=True,workspace_buffer_released=True,binding_callback_removed=True):raise ValueError('Borrowed result closure differs')
        if r['diagnostic_ps_growth_limit_bytes']!=256<<20 or r['diagnostic_ps_available_margin_bytes']!=64<<20 or r['additional_cma_requests_allowed']:raise ValueError('Diagnostic policy differs')
        counts=r['stage_memory'][0]['cma_counts']
        for point in r['stage_memory']:
            decision=point['admission']
            if decision is None:continue
            if point['cma_counts']!=counts or not 0<=decision['observed_rss_growth_bytes']<=256<<20 or decision['diagnostic_additional_explicit_cma_bytes'] or decision['required_mem_available_bytes']!=(256<<20)-decision['observed_rss_growth_bytes']+(64<<20) or decision['mem_available_bytes']<decision['required_mem_available_bytes']:raise ValueError('Sealed memory decision differs')
        if not r['same_overlay_minimal_proof']['full_output_exact'] or r['same_overlay_minimal_proof']['output_bytes']!=4096:raise ValueError('Same-overlay minimal absent')
    elif r['gate_return_code']!=1 or not r['errors']:raise ValueError('Unknown/empty failure')
    return d,raw,r

def collect(path):
    d,raw,r=decode(path.read_text(encoding='utf-8-sig'));out=BASE/'runs/M392-silu-layer-board-01/BOARD_RESULT.json';atomic(out,raw,immutable=True)
    sync('latest_m392_silu_layer_board',dict(status=r['status'],result=out.relative_to(ROOT).as_posix(),sha256=d,numerical_pass=r['numerical_pass'],performance_pass=False),
         f'## M392 SiLU工作缓冲单层板端结果（2026-10-04）\n\nBuild0x4D333537，原rc{r["gate_return_code"]}，{r["status"]}，原SHA {d}。原完整runtime/七DMA封锁新分配，原159重复文本layer0五family/hidden/KV/缩放重试全参考，单parser/无PS预读。工作缓冲借用至mlp_down完成、对象/绑定/七DMA/稳定恢复核对；仅本级数值，无文本/视频或新请求性能。下一步独立本级闭合同步后才扩大；任何容量/生命周期问题停止。')
    print(json.dumps(dict(status=r['status'],sha256=d,errors=r['errors'],scope=r.get('silu_scope'),sampled=r.get('sampled_memory'))))

if __name__=='__main__':collect(ROOT/sys.argv[1])
