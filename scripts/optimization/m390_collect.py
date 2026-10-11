"""Strict saved-byte capture recovery only; never executes a model."""
import base64
import hashlib
import json
import re
from m351_workflow import ROOT,BASE,sha,atomic,encoded,sync

PKG=BASE/'candidates/M390-gate-up-capture-01'
LEVEL='sealed-DMA-fixed159-layer0-gate-up-capture'


def decode(text):
    digests=re.findall(r'M390_RESULT_SHA256=([0-9a-f]{64})',text)
    codes=re.findall(r'M390_SAVED_GATE_RC=(\d+)',text)
    chunks=re.findall(r'M390_RESULT_CHUNK=(\d+)/(\d+):([A-Za-z0-9+/=]+)',text)
    if len(digests)!=1 or len(codes)!=1 or not chunks or len(chunks)!=int(chunks[0][1]):raise ValueError('Missing/duplicate result')
    pieces=[]
    for i,(index,total,data) in enumerate(chunks):
        if int(index)!=i or int(total)!=len(chunks):raise ValueError('Chunk sequence differs')
        piece=base64.b64decode(data,validate=True)
        if not 0<len(piece)<=1800:raise ValueError('Chunk bound differs')
        pieces.append(piece)
    raw=b''.join(pieces);digest=hashlib.sha256(raw).hexdigest()
    if digest!=digests[0]:raise ValueError('Raw SHA differs')
    r=json.loads(raw)
    if r['gate_level']!=LEVEL or r['case']!='B1' or r['build_id']!='0x4D333537':raise ValueError('Scope differs')
    if type(r['gate_return_code']) is not int or r['gate_return_code']!=int(codes[0]) or int(codes[0]) not in (0,1):raise ValueError('Original code differs')
    if r['manifest_sha256']!=sha(PKG/'PACKAGE_MANIFEST.json'):raise ValueError('Manifest differs')
    if r['numerical_pass'] or r['performance_pass'] or r['formal_promotion_allowed'] or r['memory_capacity_proven']:raise ValueError('Overclaimed scope')
    done=re.findall(r'M390_DONE case=B1 gate_rc=(\d+) export_rc=(\d+)',text)
    if done and (len(done)!=1 or done[0]!=(codes[0],'0')):raise ValueError('Gate/export code differs')
    if r['status']=='PASS_M390_ACTUAL_GATE_UP_CAPTURE':
        if r['gate_return_code'] or r['errors']:raise ValueError('PASS code/errors differ')
        expected=json.loads((PKG/'VIDEO_EXPECTED.json').read_text(encoding='utf-8'))['baseline']
        visual=json.loads((PKG/'VISUAL_EXPECTED.json').read_text(encoding='utf-8'))
        if r['captured_families']!=expected['families'][:4] or r['input']!=expected['input']:raise ValueError('Actual language prefix differs')
        if r['visual_features']!=visual['visual_features'] or r['preprocessed']!=visual['preprocessed'] or r['prompt_token_ids']!=visual['prompt_token_ids']:raise ValueError('Actual visual identity differs')
        if not r['boundary_reached'] or not r['capture_pass'] or r['attempted_after_boundary']:raise ValueError('Boundary escaped')
        if r['model_forward_calls']!=1 or r['vision_forward_calls']!=1 or r['ps_prefetch_enabled'] or r['original_parser_workers']!=1 or r['extra_pynq_allocations']:raise ValueError('Wrong variant/coverage')
        if r['host_calls']!=20 or r['logical_calls']!=20 or r['fpga_transactions']!=21 or len(r['transactions'])!=20:raise ValueError('Transaction count differs')
        if any(t['layer']!=0 or t['family'] not in ('q','kv','attention_out','gate_up') for t in r['transactions']):raise ValueError('Transaction scope escaped')
        calls=r['partial_call_contract']
        if calls['scale_attempts']!=expected['scale_attempts'][:20] or any(calls[k] for k in ('scale_retry_count','pipeline_retry_launches','fused_nonfinite_detections')):raise ValueError('Retry identity differs')
        if set(r['actual_gate_up_fixtures'])!={'gate','up'}:raise ValueError('Fixture missing')
        for short,item in r['actual_gate_up_fixtures'].items():
            ref=expected['families'][3]['output']['model.language_model.layers.0.mlp.'+short+'_proj']
            if item['tensor']!=ref or item['path']!='/home/ubuntu/m390_gate_up_capture_01/B1/'+short+'.npy':raise ValueError('Fixture identity differs')
            if not re.fullmatch('[0-9a-f]{64}',item['file_sha256']) or not 6187008<item['file_bytes']<=6187520:raise ValueError('File metadata differs')
        if [p['name'] for n,p in r['events'] if n=='stage']!=['preprocess','vision','prefill'] or any(n!='stage' for n,p in r['events']):raise ValueError('Unexpected full request output')
        if len(r['allocated_buffers'])!=7 or [x['bytes'] for x in r['allocated_buffers']]!=[6963200]*4+[389152,2621440,2621440]:raise ValueError('Allocation closure differs')
        if r['released_buffers']!=r['allocated_buffers'][::-1] or r['original_buffer_release_count']!=7 or not r['safe_buffers_released'] or r['unsafe_buffers_retained'] or r['blocked_inference_attempts']:raise ValueError('Release closure differs')
        if not r['patch_registry_cleared'] or not r['stable_overlay_reloaded'] or r['stable_bit_sha256']!='1cbf7bbb86cfe64c2349418d5a15890d735bea3fa4c999060c8a9da9ac3206ac' or not r['boot_unchanged'] or not r['cmdline_unchanged']:raise ValueError('Protected identities/restoration differs')
        s=r['final_snapshot']
        if s['ap_ctrl']!=4 or s['ap_return']!=int('4D333537',16) or any(s[k] for k in ('mm2s_error','s2mm_error')) or not s['mm2s_idle'] or not s['s2mm_idle']:raise ValueError('Final DMA state unsafe')
        if not r['sampled_memory']['observer_stopped'] or r['sampled_memory']['stop_reason']:raise ValueError('Monitor stop/lifetime differs')
    elif r['gate_return_code']!=1 or not r['errors']:raise ValueError('Failure lacks original cause')
    return digest,raw,r


def collect(path):
    digest,raw,r=decode(path.read_text(encoding='utf-8-sig'))
    out=BASE/'runs/M390-gate-up-capture-board-01/BOARD_RESULT.json'
    atomic(out,raw,immutable=True)
    sync('latest_m390_capture_board',dict(status=r['status'],sha256=digest,result=out.relative_to(ROOT).as_posix(),capture_pass=r.get('capture_pass',False),numerical_pass=False,performance_pass=False),
         f'## M390 有界真实gate/up捕获板端结果（2026-10-04）\n\nBuild0x4D333537，原rc{r["gate_return_code"]}，裁决{r["status"]}，原SHA {digest}。仅固定159视频视觉与layer0四family，gate/up真实数组板端保存；不是完整视频/新SiLU数值或性能PASS。原七DMA封锁及稳定恢复逐项核对，PS预读/双parser关闭。下一步独立输入身份/生命周期闭合同步后才准备无Overlay CPU组件；已有result/runlog只能Collect，不重跑硬件。')
    print(json.dumps(dict(status=r['status'],sha256=digest,errors=r['errors'],fixtures=r.get('actual_gate_up_fixtures'))))


if __name__=='__main__':
    import sys
    collect(ROOT/sys.argv[1])
