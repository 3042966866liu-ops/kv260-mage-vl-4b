"""Recover saved bytes; performance adjudication is a separate offline step."""
import base64
import copy
import hashlib
import json
from pathlib import Path
import re
import sys
import m351_workflow as w
from board_safety import safe_to_release
from m376_gate_up_workers import PINNED
PKG=w.BASE/'candidates/M381-gate-up-performance-01'


def decode(log,manifest_sha=None,expected=None,visual=None):
    hs=re.findall(r'(?m)^M381_RESULT_SHA256=([0-9a-f]{64})\s*$',log)
    cs=re.findall(r'(?m)^M381_SAVED_GATE_RC=([01])\s*$',log)
    parts=re.findall(r'(?m)^M381_RESULT_CHUNK=(\d+)/(\d+):([A-Za-z0-9+/=]+)\s*$',log)
    if len(hs)!=1 or len(cs)!=1 or not parts or len(parts)!=int(parts[0][1]):raise ValueError('Missing/duplicate result')
    chunks=[]
    for i,(index,total,value) in enumerate(parts):
        b=base64.b64decode(value,validate=True)
        if int(index)!=i or int(total)!=len(parts) or not 0<len(b)<=900:raise ValueError('Chunk order/limit')
        chunks.append(b)
    raw=b''.join(chunks);digest=hashlib.sha256(raw).hexdigest();r=json.loads(raw)
    if digest!=hs[0] or r['gate_return_code']!=int(cs[0]):raise ValueError('SHA/rc')
    manifest_sha=manifest_sha or w.sha(PKG/'PACKAGE_MANIFEST.json')
    if r['manifest_sha256']!=manifest_sha or r['case']!='B1' or r['gate_level']!='balanced-fixed159-video-one-versus-two-parser-performance':raise ValueError('Identity/scope')
    if any(r[k] for k in ('memory_capacity_proven','performance_pass','formal_promotion_allowed')):raise ValueError('Scope promoted')
    done=re.findall(r'M381_DONE case=B1 gate_rc=(\d+) export_rc=(\d+)',log)
    if done and done!=[(cs[0],'0')]:raise ValueError('Main/export rc')
    if r['status']=='PASS_M381_LIGHT_VIDEO_MEASUREMENTS':
        if r['errors'] or r['gate_return_code'] or not r['numerical_pass'] or r['unsafe_buffers_retained'] or not r['safe_buffers_released']:raise ValueError('Incomplete PASS')
        if r['build_id']!='0x4D333537' or r['two_parser_video_sha256']!='947646a295cc3c60a0a80c49f89e9465ce7e9bac9a9446e34e3504b6d7f21985' or r['ps_prefetch_enabled'] is not False or not r['historical_hardware_40_81_percent_result_unchanged']:raise ValueError('Changed parser prerequisite/scope differs')
        if r['order']!='ABBABAAB' or len(r['samples'])!=8 or r['model_forward_calls']!=8 or r['vision_forward_calls']!=9 or not r['all8_requests_completed']:raise ValueError('Coverage/order')
        expected=expected or json.loads((PKG/'VIDEO_EXPECTED.json').read_text(encoding='utf-8'))['baseline']
        visual=visual or json.loads((PKG/'VISUAL_EXPECTED.json').read_text(encoding='utf-8'))
        shape=[6963200]*4+[389152,2621440,2621440]
        for i,s in enumerate(r['samples']):
            build='0x4D333537'
            if s['index']!=i+1 or s['variant']!='ABBABAAB'[i] or s['build_id']!=build:raise ValueError('Trial identity')
            if [x['bytes'] for x in s['allocated_buffers']]!=shape or s['released_buffers']!=list(reversed(s['allocated_buffers'])) or not s['safe_buffers_released']:raise ValueError('Seven lifecycle')
            scope=s['parser_scope']
            wanted=dict(parse_workers=1,original_single_worker_dispatch=True,bindings_restored=True,extra_dma_allocations=0) if s['variant']=='A' else dict(parse_workers=2,gate_up_calls=36,bindings_restored=True,extra_dma_allocations=0,pending_output_slots=2,statistics_lock=True,source_sha256=PINNED,performance_pass=False)
            if any(scope[k]!=v for k,v in wanted.items()) or not s['owner_registry_cleared'] or s['restored_owner_patch_count']!=4:raise ValueError('Parser variant/owner lifecycle differs')
            n=s['numeric_sha_after_timer']
            if any(n[k]!=expected[k] for k in ('input','token','logits','keys','values')) or n['visual']!=visual['visual_features'] or n['preprocessed']!=visual['preprocessed'] or s['semantic']!=expected['semantic']:raise ValueError('Exact post-timer reference')
            if any(v!=expected[k] for k,v in s['counts'].items()):raise ValueError('Counters')
            attempt_sha=hashlib.sha256(json.dumps(expected['scale_attempts'],sort_keys=True,separators=(',',':')).encode()).hexdigest()
            if s['scale_attempts_sha_after_timer']!=attempt_sha or s['retry_records']!=[a for a in expected['scale_attempts'] if len(a['attempted_shifts'])>1]:raise ValueError('Retry trace')
            if s['sampled_memory']['stop_reason'] or not s['sampled_memory']['observer_stopped'] or s['sampled_memory']['sample_interval_s']!=.1:raise ValueError('Monitor')
            if not safe_to_release(s['final_snapshot']) or s['final_snapshot']['ap_return']!=int(build,16) or not s['same_overlay_minimal_proof']['full_output_exact'] or not s['head_observer_proof']['removed_observation_calls_ast_equals_original']:raise ValueError('Hardware completion')
            t=s['timing'];stage=t['stages_ms']
            if not 0<t['first_token_ms']<=t['total_ms'] or set(stage)!=set(('preprocess','vision','prefill','head')) or any(v<0 for v in stage.values()) or stage['head']>stage['prefill']:raise ValueError('Timing boundaries')
            for cache in (s['before_cache'],s['after_cache']):
                if cache['cache_entries']!=26 or cache['cache_bytes']!=66699264 or cache['cache_misses']!=26 or not cache['cache_within_budget']:raise ValueError('Cache policy')
        if r['fpga_transactions_total']!=sum(1+s['counts']['host_calls'] for s in r['samples']) or not all(r[k] for k in ('stable_overlay_reloaded','boot_unchanged','cmdline_unchanged')):raise ValueError('Final restore/total')
    elif r['gate_return_code']!=1 or not r['errors']:raise ValueError('Invalid FAIL')
    return digest,raw,r


def self_test():
    r=dict(status='FAIL',manifest_sha256='0'*64,case='B1',gate_level='balanced-fixed159-video-one-versus-two-parser-performance',gate_return_code=1,errors=['fake failure '*200],memory_capacity_proven=False,performance_pass=False,formal_promotion_allowed=False)
    def export(x):
        raw=w.encoded(x);parts=[raw[i:i+900] for i in range(0,len(raw),900)]
        return 'M381_RESULT_SHA256='+hashlib.sha256(raw).hexdigest()+'\nM381_SAVED_GATE_RC='+str(x['gate_return_code'])+'\n'+''.join(f'M381_RESULT_CHUNK={i}/{len(parts)}:'+base64.b64encode(b).decode()+'\n' for i,b in enumerate(parts))+'M381_DONE case=B1 gate_rc=1 export_rc=0\n'
    valid=export(r);assert decode(valid,'0'*64)[2]==r
    bad=[valid.replace('M381_SAVED_GATE_RC=1','M381_SAVED_GATE_RC=0'),valid.replace('export_rc=0','export_rc=1'),valid.replace('CHUNK=1/','CHUNK=0/'),valid+'M381_RESULT_SHA256='+'0'*64+'\n',export(dict(r,performance_pass=True)),export(dict(r,errors=[])),export(dict(r,manifest_sha256='1'*64)),valid.replace('CHUNK=0/','CHUNK=99/')]
    for x in bad:
        try:decode(x,'0'*64)
        except ValueError:pass
        else:raise AssertionError('Invalid collection accepted')
    return len(bad)


def collect(path):
    digest,raw,r=decode(Path(path).read_text(encoding='utf-8-sig'))
    out=w.BASE/'runs/M381-gate-up-performance-board-01';w.atomic(out/'BOARD_RESULT.json',raw,immutable=True)
    w.sync('latest_m381_gate_up_performance_board',dict(status=r['status'],sha256=digest,result=(out/'BOARD_RESULT.json').relative_to(w.ROOT).as_posix(),numerical_pass=r['numerical_pass'],performance_pass=False),f'## M381 固定159视频轻量交错请求测量\n\n裁决 {r["status"]}，原rc{r["gate_return_code"]}，原字节SHA `{digest}`。两组都Build0x4D333537；A原1/B只gate_up2解析worker，ABBABAAB；原请求计时结束后核对全部输出/72KV/视觉/重试。当前只保存测量证据，下一步离线计算完整请求净收益与两种顺序波动；未晋级。')
    print(json.dumps(dict(status=r['status'],sha256=digest,errors=r['errors'],samples=[dict(index=s['index'],variant=s['variant'],timing=s['timing']) for s in r.get('samples',[])])))


if __name__=='__main__':
    if sys.argv[1]=='SelfTest':print(self_test())
    else:collect(sys.argv[1])
