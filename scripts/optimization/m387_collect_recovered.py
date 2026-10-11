"""Strict saved-byte recovery only. Never executes a board gate."""
import base64
import hashlib
import json
from pathlib import Path
import re
import sys
import m351_workflow as w
from board_safety import safe_to_release
sys.path.insert(0,str(w.BASE/'candidates/M387-ps-video-01'))
from m368_stage_policy import assess,SHAPES
PKG=w.BASE/'candidates/M387-ps-video-01'

def decode(log):
    hashes=re.findall(r'(?m)^M387_RESULT_SHA256=([0-9a-f]{64})\s*$',log)
    codes=re.findall(r'(?m)^M387_SAVED_GATE_RC=([01])\s*$',log)
    chunks=re.findall(r'(?m)^M387_RESULT_CHUNK=(\d+)/(\d+):([A-Za-z0-9+/=]+)\s*$',log)
    if len(hashes)!=1 or len(codes)!=1 or not chunks or len(chunks)!=int(chunks[0][1]):raise ValueError('Incomplete/duplicate raw')
    parts=[]
    for i,(index,total,value) in enumerate(chunks):
        b=base64.b64decode(value,validate=True)
        if int(index)!=i or int(total)!=len(chunks) or not 0<len(b)<=900:raise ValueError('Order/size differs')
        parts.append(b)
    raw=b''.join(parts);digest=hashlib.sha256(raw).hexdigest();r=json.loads(raw)
    if digest!=hashes[0] or r['gate_return_code']!=int(codes[0]):raise ValueError('SHA/rc differs')
    if r['manifest_sha256']!=w.sha(PKG/'PACKAGE_MANIFEST.json') or r['case']!='B1' or r['build_id']!='0x4D333537' or r['gate_level']!='sealed-DMA-PS-fixed159-video-numerical':raise ValueError('Package/scope differs')
    if any(r[k] for k in ('memory_capacity_proven','performance_pass','formal_promotion_allowed')):raise ValueError('Scope improperly promoted')
    done=re.findall(r'M387_DONE case=B1 gate_rc=(\d+) export_rc=(\d+)',log)
    if done and done!=[(codes[0],'0')]:raise ValueError('Gate/export rc differs')
    if r['status']=='PASS_M387_PS_VIDEO_NUMERICAL':
        if r['gate_return_code'] or r['errors'] or r['unsafe_buffers_retained'] or not r['safe_buffers_released'] or not r['numerical_pass']:raise ValueError('Incomplete PASS')
        if [x['bytes'] for x in r['allocated_buffers']]!=[6963200]*4+[389152,2621440,2621440] or r['released_buffers']!=list(reversed(r['allocated_buffers'])):raise ValueError('Owned buffer lifecycle differs')
        if r['model_forward_calls']!=1 or not all(r['exact_comparison'].values()) or r['blocked_inference_attempts']:raise ValueError('Layer coverage differs')
        visual=json.loads((PKG/'VISUAL_EXPECTED.json').read_text(encoding='utf-8'))
        if r['vision_forward_calls']!=1 or not all(r['visual_exact_comparison'].values()) or r['visual_features']!=visual['visual_features'] or r['preprocessed']!=visual['preprocessed'] or r['prompt_token_ids']!=visual['prompt_token_ids']:raise ValueError('Original visual identity/output differs')
        if r['same_loading_path_video_sha256']!='dbd3325e8152bf24402ce616b7fad4fe0584a4e7972aae573fb245a4eb52abaf':raise ValueError('Frozen original video loader differs')
        expected=json.loads((PKG/'VIDEO_EXPECTED.json').read_text(encoding='utf-8'))['baseline']
        if r['video_result']!=expected:raise ValueError('Independent reference differs')
        proof=r['head_observer_proof']
        if not proof['removed_observation_calls_ast_equals_original'] or proof['inserted_observation_calls']!=2 or not proof['every_retry_physical_boundary'] or proof['exact_frozen_head_chains']!=8 or len([t for t in r['transactions'] if t['method']=='head-original-execute'])!=8:raise ValueError('Original head physical coverage differs')
        if r['fpga_transactions']!=1+r['video_result']['host_calls'] or len(r['transactions'])!=r['video_result']['host_calls']:raise ValueError('Launch count differs')
        if r['sampled_memory']['stop_reason'] or not r['sampled_memory']['observer_stopped'] or not safe_to_release(r['final_snapshot']) or r['final_snapshot']['ap_return']!=0x4d333537:raise ValueError('Completion/monitor differs')
        if not all(r[k] for k in ('stable_overlay_reloaded','boot_unchanged','cmdline_unchanged','tokenizer_single_parse_reused')):raise ValueError('Environment/restore differs')
        if r['PS_text_prerequisite_sha256']!='775aaab821f251d12313dc7ac75fec71ac6130bda0d54cb4ef2910cdcb057c01' or not r['ps_prefetch_enabled'] or not r['session_weakref_dead'] or not r['patch_registry_cleared'] or not r['worker_started'] or r['extra_pynq_allocations'] or r['original_parser_workers']!=1:raise ValueError('PS prerequisite/scope/lifetime differs')
        p=r['ps_session'];c=p['component']
        required=dict(status='COMPLETE_COMPONENT_ONLY',stages=162,submissions=162,ps_payload_bytes=27852800,extra_cma_allocation_calls=0,total_weight_bytes=expected['stage_bytes'],open_files=0,live_views=0,performance_pass=False,hardware_contract_changed=False)
        if any(c[k]!=v for k,v in required.items()) or p['production_policy_changed'] or p['additional_dma_allocations'] or not p['source_component_unchanged']:raise ValueError('PS plan/accounting differs')
        if p['slot_release']!=dict(released_ports=4,bytearrays_sole_owned_before_release=True,all_owner_weakrefs_dead=True,explicit_gc_or_trim=False):raise ValueError('PS slot release differs')
        if p['budget_growth_bytes']!=1024<<20 or p['available_margin_bytes']!=64<<20:raise ValueError('Combined layer budget differs')
        if len(p['independent_memory_checks'])<166:raise ValueError('PS memory coverage absent')
        counts=p['independent_memory_checks'][0]['cma_counts']
        for x in p['independent_memory_checks']:
            actual=assess(x['memory'],p['budget_baseline_rss'],x['cma_counts'],counts,sealed=True,buffer_bytes=SHAPES)
            if x['decision']!=actual:raise ValueError('PS actual admission differs')
        for x in r['stage_memory']:
            if x['admission'] is not None:
                actual=assess(x['memory'],p['budget_baseline_rss'],x['cma_counts'],counts,sealed=True,buffer_bytes=SHAPES)
                if x['admission']!=actual:raise ValueError('Physical/family memory decision differs')
        if not r['same_overlay_minimal_proof']['full_output_exact'] or r['same_overlay_minimal_proof']['output_bytes']!=4096:raise ValueError('Same-overlay minimal proof absent')
    elif r['gate_return_code']!=1 or not r['errors']:raise ValueError('Invalid failure')
    return digest,raw,r

def collect(path):
    digest,raw,r=decode(Path(path).read_text(encoding='utf-8-sig'))
    out=w.BASE/'runs/M387-ps-video-board-01';w.atomic(out/'BOARD_RESULT.json',raw,immutable=True)
    w.sync('latest_m387_ps_video_board',dict(status=r['status'],result=(out/'BOARD_RESULT.json').relative_to(w.ROOT).as_posix(),sha256=digest,numerical_pass=r['numerical_pass'],memory_capacity_proven=False,performance_pass=False),f'## M387 PS固定159视频数值门禁\n\nBuild0x4D333537，原rc{r["gate_return_code"]}，裁决{r["status"]}；完整runtime对象保留，原159Token视频/视觉/36层/head与162窗口PS预读，原单parser。原生产64MiB保持，额外CMA申请封锁，记录逐family/提交内存和20ms采样；严格原数值/退出回收核对，非全模型容量/峰值或性能晋级。原字节SHA `{digest}`。下一步仅本级数值和生命周期闭合，之后才准备同核单parser原暂存/PS预读轻量交错请求性能；容量或生命周期问题停止扩大。')
    print(json.dumps(dict(status=r['status'],raw_sha256=digest,errors=r['errors'],sampled=r.get('sampled_memory'),production_admission=r.get('production_threshold_would_admit'))))

if __name__=='__main__':collect(sys.argv[1])
