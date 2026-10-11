"""Strict saved-byte recovery; never starts hardware."""
import base64,hashlib,json,re
from pathlib import Path
from m351_workflow import ROOT,BASE,sha,atomic,encoded,sync
from board_safety import safe_to_release
from m376_gate_up_workers import PINNED
from m377_prepare import PKG,PRIOR
def validate(r):
    if r['manifest_sha256']!=sha(PKG/'PACKAGE_MANIFEST.json') or r['case']!='B1' or r['build_id']!='0x4D333537' or r['gate_level']!='independent-gate-up-family-pair':raise ValueError('Identity/scope differs')
    if any(r[k] for k in ('memory_capacity_proven','performance_pass','formal_promotion_allowed')):raise ValueError('Improper promotion')
    if r['status']!='PASS_M377_GATE_UP_PAIR_NUMERICAL':
        if r['gate_return_code']!=1 or not r['errors']:raise ValueError('Invalid failure')
        return
    if r['gate_return_code'] or r['errors'] or r['unsafe_buffers_retained'] or not r['safe_buffers_released'] or not r['numerical_pass']:raise ValueError('Incomplete PASS')
    if [x['bytes'] for x in r['allocated_buffers']]!=[6963200]*4+[389152,2621440,2621440] or r['released_buffers']!=list(reversed(r['allocated_buffers'])):raise ValueError('Buffer lifecycle differs')
    if r['model_forward_calls']!=0 or r['blocked_inference_attempts'] or r['parser_capability_sha256']!=PRIOR or r['ps_prefetch_enabled'] is not False or not r['gate_up_family_pair_pass']:raise ValueError('Coverage differs')
    expected=json.loads((PKG/'LAYER_EXPECTED.json').read_text(encoding='utf-8'))
    pair=r['family_pair'];a,b=pair['pairs']
    if pair['status']!='PASS_CURRENT_SINGLE_VS_TWO_WORKER_GATE_UP_FAMILY_NUMERICAL' or pair['additional_cma_bytes'] or pair['model_forward_calls'] or pair['performance_pass']:raise ValueError('Pair scope differs')
    if [a['workers'],b['workers']]!=[1,2] or a['input']!=expected['input_contract']['input_tensor'] or b['input']!=a['input']:raise ValueError('Input identity differs')
    if a['outputs']!=b['outputs'] or a['counts']!=b['counts'] or a['scale_attempts']!=b['scale_attempts']:raise ValueError('Full outputs/retries differ')
    widths=next(f['output'] for f in expected['baseline']['families'] if f['family']=='gate_up')
    if set(a['outputs'])!=set(widths):raise ValueError('Output modules differ')
    for name,row in a['outputs'].items():
        if any(row[k]!=widths[name][k] for k in ('shape','dtype','bytes')) or not re.fullmatch('[0-9a-f]{64}',row['sha256']):raise ValueError('Full output geometry differs')
    counts=a['counts'];retry=counts['pipeline_retry_launches'];physical=5+retry
    if type(retry) is not int or retry<0 or any(counts[k]!=v for k,v in dict(logical_calls=5,host_calls=physical,scale_retry_count=retry,fused_nonfinite_detections=retry,pipeline_submissions=5,pipeline_reuse_waits=3,parse_calls=physical).items()):raise ValueError('Counter contract differs')
    if len(a['scale_attempts'])!=5 or counts['stage_bytes']<=0:raise ValueError('Stage/retry records incomplete')
    if a['scope']!=dict(parse_workers=1,gate_up_calls=1,bindings_restored=True,extra_dma_allocations=0,original_single_worker_dispatch=True):raise ValueError('Original dispatch differs')
    scope=b['scope']
    if any(scope[k]!=v for k,v in dict(parse_workers=2,gate_up_calls=1,bindings_restored=True,extra_dma_allocations=0,pending_output_slots=2,statistics_lock=True,source_sha256=PINNED,performance_pass=False).items()):raise ValueError('Candidate binding/ownership differs')
    if r['logical_calls']!=10 or r['host_calls']!=2*physical or len(r['transactions'])!=2*physical or r['fpga_transactions']!=1+2*physical:raise ValueError('Physical accounting differs')
    chain=json.loads((BASE/'candidates/M376-gate-up-worker-component-01/GATE_UP_FIXTURE.json').read_text(encoding='utf-8'))['chain']
    for t in r['transactions']:
        if any(t[k]!=chain[k] for k in ('layer','family','chain_index','input_bytes','output_bytes')) or t['method'] not in ('_launch_prepacked','_launch_once'):raise ValueError('Chain scope differs')
    if r['sampled_memory']['stop_reason'] or not r['sampled_memory']['observer_stopped'] or not safe_to_release(r['final_snapshot']) or r['final_snapshot']['ap_return']!=0x4d333537:raise ValueError('Completion/monitor differs')
    if not all(r[k] for k in ('stable_overlay_reloaded','boot_unchanged','cmdline_unchanged','tokenizer_single_parse_reused')):raise ValueError('Restore differs')
    if not r['same_overlay_minimal_proof']['full_output_exact'] or r['same_overlay_minimal_proof']['output_bytes']!=4096 or not safe_to_release(r['same_overlay_minimal_proof']['snapshot']):raise ValueError('Same-overlay minimal absent')
    required={'before-gate-up-workers:1','after-gate-up-workers:1','before-gate-up-workers:2','after-gate-up-workers:2'}
    if not required<={x['label'] for x in r['stage_memory'] if x['admission'] is not None}:raise ValueError('Memory checkpoints absent')
def decode(log):
    hashes=re.findall(r'(?m)^M377_RESULT_SHA256=([0-9a-f]{64})\s*$',log);codes=re.findall(r'(?m)^M377_SAVED_GATE_RC=([01])\s*$',log)
    chunks=re.findall(r'(?m)^M377_RESULT_CHUNK=(\d+)/(\d+):([A-Za-z0-9+/=]+)\s*$',log)
    if len(hashes)!=1 or len(codes)!=1 or not chunks or len(chunks)!=int(chunks[0][1]):raise ValueError('Incomplete/duplicate raw')
    pieces=[]
    for i,(index,total,value) in enumerate(chunks):
        b=base64.b64decode(value,validate=True)
        if int(index)!=i or int(total)!=len(chunks) or not 0<len(b)<=900:raise ValueError('Order/size differs')
        pieces.append(b)
    raw=b''.join(pieces);digest=hashlib.sha256(raw).hexdigest();r=json.loads(raw)
    if digest!=hashes[0] or r['gate_return_code']!=int(codes[0]):raise ValueError('SHA/rc differs')
    done=re.findall(r'M377_DONE case=B1 gate_rc=(\d+) export_rc=(\d+)',log)
    if done and done!=[(codes[0],'0')]:raise ValueError('Gate/export rc differs')
    validate(r);return digest,raw,r
def collect(path):
    digest,raw,r=decode(Path(path).read_text(encoding='utf-8-sig'));out=BASE/'runs/M377-gate-up-pair-board-01'
    atomic(out/'BOARD_RESULT.json',raw,immutable=True)
    sync('latest_m377_gate_up_pair_board',dict(status=r['status'],result=(out/'BOARD_RESULT.json').relative_to(ROOT).as_posix(),sha256=digest,numerical_pass=r['numerical_pass'],performance_pass=False),f'## M377 gate_up 原1/候选2解析 worker 板端 family 数值门禁（2026-10-03）\n\nBuild0x4D333537；原rc{r["gate_return_code"]}，{r["status"]}。原同输入159重复文本embedding、完整gate/up输出逐位SHA、计数/重试和七缓冲生命周期核对；0新增CMA，无完整层/视频/性能结论。原字节 SHA {digest}；下一步只能按本级裁决后准备单层。')
    print(json.dumps(dict(status=r['status'],sha256=digest,errors=r['errors'],pairs=r.get('family_pair'),memory=r.get('sampled_memory')),ensure_ascii=False))
