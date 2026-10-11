import json
from pathlib import Path
from measurement import sha256,write_json,exclusive_lock
root=Path(__file__).resolve().parents[2];base=root/'deployment/mage_vl4b/optimization_v1'
report=root/'tmp/op01_decode_one_boundary_csim_02/hls/csim/report/op01_decode_one_kernel_csim.log'
text=report.read_text()
for marker in ['OP01_NEGATIVE_PASS cases=13','OP01_MAXIMUM_PASS bits=2 words=327680','OP01_MAXIMUM_PASS bits=4 words=327680','OP01_BOUNDARY_NUMERICAL_PASS']:
    assert marker in text,marker
old=json.loads((base/'gates/G02-decode-one-csim/attempt_01/result.json').read_text())
for name in ['decode_one.cpp','decode_one.hpp']:
    p=root/'hls/mage_decode_op01_one'/name
    assert sha256(p)==old['sources'][str(p.relative_to(root))]
out=base/'gates/G02-decode-one-boundary/attempt_02/result.json'
if out.exists():raise RuntimeError('Immutable result exists')
result=dict(status='PASS_BOUNDARY_NUMERICAL_ONLY',build_id='0x4F503131',board_deployed=False,
    maximum=dict(groups=152,rows_per_shard=512,descriptors=10,bits=[2,4],words_per_case=327680),
    oracle='Analytic constant weight/activation result608 FP16 0x60c0; nonzero inactive inputs discarded',
    negative_cases=13,report_sha256=sha256(report),testbench_sha256=sha256(root/'hls/mage_decode_op01_one/tb_boundary.cpp'),
    rejected_attempt='attempt01 testbench compilation: missing fp_struct declaration; fixed using independently derived IEEE FP16 constant. Kernel unchanged.',
    limitations=['synthetic boundary, not real model quality','C streams unbounded, not RTL FIFO proof','missing-input timeout and AXI backpressure pending RTL','no measured speedup'])
with exclusive_lock(base/'evidence.lock'):
    write_json(out,result)
    p=base/'STATE.json';s=json.loads(p.read_text());s['results']['decode_one_boundary']=str(out.relative_to(root))
    s['next_action']='Run isolated Decode-one HLS/RTL tests with maximum FIFO, descriptor occupancy, AXI backpressure and timeout rejection; then resource/timing gates before board.'
    write_json(p,s)
    p=root/'deployment/mage_vl4b/BOARD_GATE_RESULT.json';s=json.loads(p.read_text(encoding='utf-8-sig'))
    s['latest_decode_one_boundary']=dict(status=result['status'],result=str(out.relative_to(root)),sha256=sha256(out),board_deployed=False)
    write_json(p,s)
print(result['status'])
