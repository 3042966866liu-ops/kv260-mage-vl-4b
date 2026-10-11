"""Saved-only exact fixed30 text / complete LM head numerical recovery."""
import base64
import hashlib
import json
import re
import sys
from m351_workflow import ROOT,BASE,sha,atomic,sync
from board_safety import safe_to_release
PKG=BASE/'candidates/M393-silu-text-01'
PRIOR='8eb467882777edd2ff8d9b11e6b02077a58b72f20a1d401478ac67502b35a63d'

def expected_scope():
    return dict(calls=36,closed=True,retained=False,
                events=['before-layer-workspace-scope']+['before-silu','after-mlp-down-before-reuse']*36+['before-workspace-close'],
                workspace_bytes=1167360,workspace_object_released=True,workspace_buffer_released=True,binding_callback_removed=True)

def decode(text):
    hs=re.findall(r'(?m)^M393_RESULT_SHA256=([0-9a-f]{64})\s*$',text);cs=re.findall(r'(?m)^M393_SAVED_GATE_RC=([01])\s*$',text)
    pieces=re.findall(r'(?m)^M393_RESULT_CHUNK=(\d+)/(\d+):([A-Za-z0-9+/=]+)\s*$',text)
    if len(hs)!=1 or len(cs)!=1 or not pieces or len(pieces)!=int(pieces[0][1]):raise ValueError('Incomplete/duplicate raw')
    data=[]
    for i,(n,total,b64) in enumerate(pieces):
        p=base64.b64decode(b64,validate=True)
        if int(n)!=i or int(total)!=len(pieces) or not 0<len(p)<=900:raise ValueError('Order/size differs')
        data.append(p)
    raw=b''.join(data);d=hashlib.sha256(raw).hexdigest();r=json.loads(raw)
    if d!=hs[0] or type(r['gate_return_code']) is not int or r['gate_return_code']!=int(cs[0]):raise ValueError('SHA/code differs')
    if r['manifest_sha256']!=sha(PKG/'PACKAGE_MANIFEST.json') or r['case']!='B1' or r['build_id']!='0x4D333537' or r['gate_level']!='sealed-DMA-SiLU-workspace-fixed-text-numerical':raise ValueError('Package/scope differs')
    if any(r[k] for k in ('memory_capacity_proven','performance_pass','formal_promotion_allowed')):raise ValueError('Improperly promoted')
    done=re.findall(r'M393_DONE case=B1 gate_rc=(\d+) export_rc=(\d+)',text)
    if done and done!=[(cs[0],'0')]:raise ValueError('Original/export code differs')
    if r['status']=='PASS_M393_SILU_TEXT_NUMERICAL':
        if r['gate_return_code'] or r['errors'] or r['unsafe_buffers_retained'] or not r['safe_buffers_released'] or not r['numerical_pass']:raise ValueError('Incomplete PASS')
        if [x['bytes'] for x in r['allocated_buffers']]!=[6963200]*4+[389152,2621440,2621440] or r['released_buffers']!=r['allocated_buffers'][::-1] or r['original_buffer_release_count']!=7:raise ValueError('Owned DMA closure differs')
        expected=json.loads((PKG/'LAYER_EXPECTED.json').read_text(encoding='utf-8'))['baseline']
        if r['model_forward_calls']!=1 or r['layer_result']!=expected or not all(r['exact_comparison'].values()) or r['blocked_inference_attempts']:raise ValueError('Independent fixed text reference differs')
        if r['fpga_transactions']!=1+expected['host_calls'] or len(r['transactions'])!=expected['host_calls']:raise ValueError('Actual launch count differs')
        if r['sampled_memory']['stop_reason'] or not r['sampled_memory']['observer_stopped'] or not safe_to_release(r['final_snapshot']) or r['final_snapshot']['ap_return']!=0x4d333537:raise ValueError('Completion/monitor differs')
        if not all(r[k] for k in ('stable_overlay_reloaded','boot_unchanged','cmdline_unchanged','tokenizer_single_parse_reused','patch_registry_cleared')) or r['stable_bit_sha256']!='1cbf7bbb86cfe64c2349418d5a15890d735bea3fa4c999060c8a9da9ac3206ac':raise ValueError('Restore/identity differs')
        if r['silu_layer_prerequisite_sha256']!=PRIOR or r['ps_prefetch_enabled'] or r['worker_started'] or not r['scope_weakref_dead'] or not r['silu_workspace_enabled'] or r['extra_pynq_allocations'] or r['original_parser_workers']!=1:raise ValueError('Variant/lifetime differs')
        if r['silu_scope']!=expected_scope():raise ValueError('36 borrowed-result scopes differ')
        if r['diagnostic_ps_growth_limit_bytes']!=256<<20 or r['diagnostic_ps_available_margin_bytes']!=64<<20 or r['additional_cma_requests_allowed']:raise ValueError('Diagnostic policy differs')
        counts=r['stage_memory'][0]['cma_counts']
        for point in r['stage_memory']:
            decision=point['admission']
            if decision is None:continue
            if point['cma_counts']!=counts or not 0<=decision['observed_rss_growth_bytes']<=256<<20 or decision['diagnostic_additional_explicit_cma_bytes'] or decision['required_mem_available_bytes']!=(256<<20)-decision['observed_rss_growth_bytes']+(64<<20) or decision['mem_available_bytes']<decision['required_mem_available_bytes']:raise ValueError('Sealed memory decision differs')
        if not r['same_overlay_minimal_proof']['full_output_exact'] or r['same_overlay_minimal_proof']['output_bytes']!=4096:raise ValueError('Same-overlay minimal absent')
        if r['head_observer_proof']['original_module']!='m230_prefill_runtime' or r['head_observer_proof']['original_function']!='M230PrefillRuntime._execute':raise ValueError('Head observer identity differs')
    elif r['gate_return_code']!=1 or not r['errors']:raise ValueError('Unknown/empty failure')
    return d,raw,r

def collect(path):
    d,raw,r=decode(path.read_text(encoding='utf-8-sig'));out=BASE/'runs/M393-silu-text-board-01/BOARD_RESULT.json';atomic(out,raw,immutable=True)
    sync('latest_m393_silu_text_board',dict(status=r['status'],result=out.relative_to(ROOT).as_posix(),sha256=d,numerical_pass=r['numerical_pass'],performance_pass=False),
         f'## M393 SiLU固定文本板端结果（2026-10-04）\n\nBuild0x4D333537，原rc{r["gate_return_code"]}，{r["status"]}，原SHA {d}。原固定30Token/36层/154family/151936logits/72KV和真实head物理观察，原单parser/暂存，无PS预读/新增DMA。36次工作缓冲借用到down完成与绑定/owner/七DMA释放、稳定恢复核对；仅文本数值与生命周期，无新视频/完整请求收益。下一步独立闭合后原159视频。')
    print(json.dumps(dict(status=r['status'],sha256=d,errors=r['errors'],scope=r.get('silu_scope'),sampled=r.get('sampled_memory'))))

if __name__=='__main__':collect(ROOT/sys.argv[1])
