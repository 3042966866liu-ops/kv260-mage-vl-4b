"""Strict saved-byte recovery only. Never executes a board gate."""
import base64
import hashlib
import json
from pathlib import Path
import re
import sys
import m351_workflow as w
from board_safety import safe_to_release
from m374_wait_validation import validate
PKG=w.BASE/'candidates/M374-layer-future-wait-01'

def decode(log):
    hashes=re.findall(r'(?m)^M374_RESULT_SHA256=([0-9a-f]{64})\s*$',log)
    codes=re.findall(r'(?m)^M374_SAVED_GATE_RC=([01])\s*$',log)
    chunks=re.findall(r'(?m)^M374_RESULT_CHUNK=(\d+)/(\d+):([A-Za-z0-9+/=]+)\s*$',log)
    if len(hashes)!=1 or len(codes)!=1 or not chunks or len(chunks)!=int(chunks[0][1]):raise ValueError('Incomplete/duplicate raw')
    parts=[]
    for i,(index,total,value) in enumerate(chunks):
        b=base64.b64decode(value,validate=True)
        if int(index)!=i or int(total)!=len(chunks) or not 0<len(b)<=900:raise ValueError('Order/size differs')
        parts.append(b)
    raw=b''.join(parts);digest=hashlib.sha256(raw).hexdigest();r=json.loads(raw)
    if digest!=hashes[0] or r['gate_return_code']!=int(codes[0]):raise ValueError('SHA/rc differs')
    if r['manifest_sha256']!=w.sha(PKG/'PACKAGE_MANIFEST.json') or r['case']!='B1' or r['build_id']!='0x4D333537' or r['gate_level']!='independent-single-layer-capacity-diagnostic':raise ValueError('Package/scope differs')
    if any(r[k] for k in ('memory_capacity_proven','performance_pass','formal_promotion_allowed')):raise ValueError('Scope improperly promoted')
    done=re.findall(r'M374_DONE case=B1 gate_rc=(\d+) export_rc=(\d+)',log)
    if done and done!=[(codes[0],'0')]:raise ValueError('Gate/export rc differs')
    if r['status']=='PASS_M374_SINGLE_LAYER_DIAGNOSTIC':
        if r['gate_return_code'] or r['errors'] or r['unsafe_buffers_retained'] or not r['safe_buffers_released'] or not r['numerical_pass']:raise ValueError('Incomplete PASS')
        if [x['bytes'] for x in r['allocated_buffers']]!=[6963200]*4+[389152,2621440,2621440] or r['released_buffers']!=list(reversed(r['allocated_buffers'])):raise ValueError('Owned buffer lifecycle differs')
        if r['model_forward_calls']!=1 or not all(r['exact_comparison'].values()) or r['blocked_inference_attempts']:raise ValueError('Layer coverage differs')
        expected=json.loads((PKG/'LAYER_EXPECTED.json').read_text(encoding='utf-8'))['baseline']
        if r['layer_result']!=expected:raise ValueError('Independent reference differs')
        if r['fpga_transactions']!=1+r['layer_result']['host_calls'] or len(r['transactions'])!=r['layer_result']['host_calls']:raise ValueError('Launch count differs')
        if r['sampled_memory']['stop_reason'] or not r['sampled_memory']['observer_stopped'] or not safe_to_release(r['final_snapshot']) or r['final_snapshot']['ap_return']!=0x4d333537:raise ValueError('Completion/monitor differs')
        if not all(r[k] for k in ('stable_overlay_reloaded','boot_unchanged','cmdline_unchanged','tokenizer_single_parse_reused')):raise ValueError('Environment/restore differs')
        if r.get('future_wait_recovery_error') or r.get('ps_prefetch_enabled') is not False or r['future_capability_raw_sha256']!='52d05d3aa2ab204fa53a9281804b5ad76e15fdd92c6376780bf506fe60868067':raise ValueError('Wait observation prerequisite/scope differs')
        if validate(r['future_wait'],r['transactions'])!=r['future_wait_summary']:raise ValueError('Wait attribution differs')
        if not r['same_overlay_minimal_proof']['full_output_exact'] or r['same_overlay_minimal_proof']['output_bytes']!=4096:raise ValueError('Same-overlay minimal proof absent')
    elif r['gate_return_code']!=1 or not r['errors']:raise ValueError('Invalid failure')
    return digest,raw,r

def collect(path):
    digest,raw,r=decode(Path(path).read_text(encoding='utf-8-sig'))
    out=w.BASE/'runs/M374-layer-wait-board-01';w.atomic(out/'BOARD_RESULT.json',raw,immutable=True)
    w.sync('latest_m374_layer_wait_board',dict(status=r['status'],result=(out/'BOARD_RESULT.json').relative_to(w.ROOT).as_posix(),sha256=digest,numerical_pass=r['numerical_pass'],memory_capacity_proven=False,performance_pass=False),f'## M374 独立单层容量诊断\n\nBuild0x4D333537，原rc{r["gate_return_code"]}，裁决{r["status"]}；完整runtime对象保留，只layer0/159重复文本embedding，非视频。原生产64MiB保持，额外CMA申请封锁，记录逐family/提交内存和20ms采样；严格原数值/退出回收核对，非全模型容量/峰值或性能晋级。原字节SHA `{digest}`。本次仅观察真实Future等待，下一步先解释单层结果；不能外推视频等待或新增提速，预读仍关闭。')
    print(json.dumps(dict(status=r['status'],raw_sha256=digest,errors=r['errors'],sampled=r.get('sampled_memory'),production_admission=r.get('production_threshold_would_admit'))))

if __name__=='__main__':collect(sys.argv[1])
