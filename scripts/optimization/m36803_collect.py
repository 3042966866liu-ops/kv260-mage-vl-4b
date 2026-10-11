"""Strict saved-byte recovery only. Never executes a board gate."""
import base64
import hashlib
import json
from pathlib import Path
import re
import sys
import m351_workflow as w
from board_safety import safe_to_release
PKG=w.BASE/'candidates/M368-staged-video-03'

def decode(log):
    hashes=re.findall(r'(?m)^M368_RESULT_SHA256=([0-9a-f]{64})\s*$',log)
    codes=re.findall(r'(?m)^M368_SAVED_GATE_RC=([01])\s*$',log)
    chunks=re.findall(r'(?m)^M368_RESULT_CHUNK=(\d+)/(\d+):([A-Za-z0-9+/=]+)\s*$',log)
    if len(hashes)!=1 or len(codes)!=1 or not chunks or len(chunks)!=int(chunks[0][1]):raise ValueError('Incomplete/duplicate raw')
    parts=[]
    for i,(index,total,value) in enumerate(chunks):
        b=base64.b64decode(value,validate=True)
        if int(index)!=i or int(total)!=len(chunks) or not 0<len(b)<=900:raise ValueError('Order/size differs')
        parts.append(b)
    raw=b''.join(parts);digest=hashlib.sha256(raw).hexdigest();r=json.loads(raw)
    if digest!=hashes[0] or r['gate_return_code']!=int(codes[0]):raise ValueError('SHA/rc differs')
    if r['manifest_sha256']!=w.sha(PKG/'PACKAGE_MANIFEST.json') or r['case']!='B1' or r['build_id']!='0x4D333537' or r['gate_level']!='independent-fixed159-video-capacity-diagnostic':raise ValueError('Package/scope differs')
    if any(r[k] for k in ('memory_capacity_proven','performance_pass','formal_promotion_allowed')):raise ValueError('Scope improperly promoted')
    done=re.findall(r'M368_DONE case=B1 gate_rc=(\d+) export_rc=(\d+)',log)
    if done and done!=[(codes[0],'0')]:raise ValueError('Gate/export rc differs')
    if r['status']=='PASS_M368_FIXED_VIDEO_DIAGNOSTIC':
        if r['gate_return_code'] or r['errors'] or r['unsafe_buffers_retained'] or not r['safe_buffers_released'] or not r['numerical_pass']:raise ValueError('Incomplete PASS')
        if [x['bytes'] for x in r['allocated_buffers']]!=[6963200]*4+[389152,2621440,2621440] or r['released_buffers']!=list(reversed(r['allocated_buffers'])):raise ValueError('Owned buffer lifecycle differs')
        if r['model_forward_calls']!=1 or r['vision_forward_calls']!=1 or not all(r['exact_comparison'].values()) or not all(r['visual_exact_comparison'].values()) or r['blocked_inference_attempts']:raise ValueError('Video coverage differs')
        expected=json.loads((PKG/'VIDEO_EXPECTED.json').read_text(encoding='utf-8'))['baseline']
        if r['video_result']!=expected:raise ValueError('Independent reference differs')
        if not r['head_observer_proof']['removed_observation_calls_ast_equals_original'] or len([t for t in r['transactions'] if t['method']=='head-original-execute'])!=8:raise ValueError('Head physical coverage differs')
        if r['fpga_transactions']!=1+r['video_result']['host_calls'] or len(r['transactions'])!=r['video_result']['host_calls']:raise ValueError('Launch count differs')
        if r['sampled_memory']['stop_reason'] or not r['sampled_memory']['observer_stopped'] or not safe_to_release(r['final_snapshot']) or r['final_snapshot']['ap_return']!=0x4d333537:raise ValueError('Completion/monitor differs')
        if not all(r[k] for k in ('stable_overlay_reloaded','boot_unchanged','cmdline_unchanged','tokenizer_single_parse_reused')):raise ValueError('Environment/restore differs')
        if not r['same_overlay_minimal_proof']['full_output_exact'] or r['same_overlay_minimal_proof']['output_bytes']!=4096:raise ValueError('Same-overlay minimal proof absent')
    elif r['gate_return_code']!=1 or not r['errors']:raise ValueError('Invalid failure')
    return digest,raw,r

def collect(path):
    digest,raw,r=decode(Path(path).read_text(encoding='utf-8-sig'))
    out=w.BASE/'runs/M368-staged-video-board-02';w.atomic(out/'BOARD_RESULT.json',raw,immutable=True)
    w.sync('latest_m368_staged_layer_board',dict(status=r['status'],result=(out/'BOARD_RESULT.json').relative_to(w.ROOT).as_posix(),sha256=digest,numerical_pass=r['numerical_pass'],memory_capacity_proven=False,performance_pass=False),f'## M368 独立固定视频容量诊断\n\nBuild0x4D333537，原rc{r["gate_return_code"]}，裁决{r["status"]}；完整runtime对象保留，原159-token视频/视觉/36层/完整head。原生产64MiB保持，额外CMA申请封锁，记录逐family/提交内存和20ms采样；严格原数值/退出回收核对，非全模型容量/峰值或性能晋级。原字节SHA `{digest}`。下一步先视频裁决并同步；通过后才可准备轻量交错完整请求性能。')
    print(json.dumps(dict(status=r['status'],raw_sha256=digest,errors=r['errors'],sampled=r.get('sampled_memory'),production_admission=r.get('production_threshold_would_admit'))))

if __name__=='__main__':collect(sys.argv[1])
