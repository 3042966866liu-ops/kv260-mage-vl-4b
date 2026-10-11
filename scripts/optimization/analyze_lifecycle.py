"""Read-only validation of collected lifecycle experiment, never a tier gate."""
import hashlib
import json
from pathlib import Path
import numpy as np
from measurement import sha256,write_json
from summarize_decode_trace import summarize
from replay_io_summary import read_io_summary
root=Path(__file__).resolve().parents[2];base=root/'deployment/mage_vl4b/optimization_v1'
source=base/'gates/G01-lifecycle/attempt_01/board_result.json'
data=json.loads(source.read_text())
if data['status']!='MEASURED':raise RuntimeError('Review failed gate at its original level')
if not data['boot_unchanged'] or not data['cmdline_unchanged'] or not data['cleanup']['buffers_released']:
    raise RuntimeError('Safety contract not established')
transactions=data['transactions']
if len(transactions)!=486 or any(t['ap_return']!=0x4D395832 for t in transactions):
    raise RuntimeError('Physical identity/count mismatch')
records=data['lifecycle']['records']
if [r['state'] for r in records]!=['A-retained','B-released','C-trimmed']:
    raise RuntimeError('Incomplete state coverage')
capture=base/'runs/OP01-replay01-real-capture/array03.npy'
if sha256(capture)!='19b51a93ed2f8dec257e2a0ab00d9c3639cb23b3f9a76b95cbfe8c4770f74c40':raise RuntimeError('Reference identity')
prior_hash=hashlib.sha256(np.load(capture,allow_pickle=False).tobytes()).hexdigest()
rows=[]
for record in records:
    if not record['logits_bit_exact_vs_A']:raise RuntimeError('Cross-state logits mismatch')
    detail=record['detail'];step=detail['steps'][0]
    attributed=summarize(step);counts=attributed['counters']
    if counts['logical_calls']!=162 or counts['host_calls']!=162 or counts['scale_retry_count']!=0:
        raise RuntimeError('Unexpected execution plan')
    io=read_io_summary(step['trace']['events'])
    if not io['read_plan_accepted']:raise RuntimeError('Unexpected read count')
    if record['token_ready_s']!=detail['token_ready_s'] or record['token_ready_s']<attributed['decode_call_s']:
        raise RuntimeError('Timing boundary inconsistent')
    rows.append(dict(state=record['state'],token_ready_s=record['token_ready_s'],
        callback_wall_s=record['decode_callback_wall_s'],exclusive_s=attributed['main_thread_exclusive_s'],
        read_io=io,output=record['output'],exact_vs_prior_replay=record['output']['sha256']==prior_hash,
        memory_before=record['memory_before'],memory_after=record['memory_after'],transition=record['transition'],
        preparation=record['preparation']))
result=dict(status='MEASURED_VALIDATED_DIAGNOSTIC_ONLY',source_sha256=sha256(source),rows=rows,
    formal_performance_pass=False,causal_speedup_proven=False,
    caveat='Same read-preparation protocol, not identical residency. A/B/C order and visual reload cost require independent evaluation.')
out=base/'runs/OP01-lifecycle-attribution/result.json'
if out.exists():raise RuntimeError('Immutable analysis exists')
write_json(out,result)
print(json.dumps(result))
