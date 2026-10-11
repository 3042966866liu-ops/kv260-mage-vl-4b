"""Record only the completed real-family numerical gate, never a board PASS."""
import json
from pathlib import Path
from measurement import sha256, write_json, exclusive_lock
root=Path(__file__).resolve().parents[2]
base=root/'deployment/mage_vl4b/optimization_v1'
report=root/'tmp/op01_decode_one_real_csim/hls/csim/report/op01_decode_one_kernel_csim.log'
assert 'OP01_REAL_GATE_UP_CSIM_PASS words=311296 active_values=19456' in report.read_text()
header=base/'runs/OP01-decode-one-real-header/result.json'
assert json.loads(header.read_text())['missing']==[]
fixture=base/'runs/OP01-decode-one-real-fixture/real_gate_up.bin'
assert sha256(fixture)=='e4ec996a6c6cda9c0e890948258157bd9c77a98f95249a8435d8eae265fdef69'
previous=json.loads((base/'gates/G02-decode-one-csim/attempt_01/result.json').read_text())
for name in ['decode_one.cpp','decode_one.hpp']:
    path=root/'hls/mage_decode_op01_one'/name
    assert sha256(path)==previous['sources'][str(path.relative_to(root))]
out=base/'gates/G02-decode-one-real-csim/attempt_01/result.json'
if out.exists():raise RuntimeError('Immutable result exists')
result=dict(status='PASS_REAL_GATE_UP_NUMERICAL_CSIM_ONLY',build_id='0x4F503131',
    board_deployed=False,performance_pass=False,active_values=19456,output_words=311296,
    descriptors=10,groups=40,weight_bits=4,max_rows_per_shard=512,
    expected='Captured stable-board layer0 Gate/Up, exactly rescaled to wire FP16; inactive lanes zero',
    checks=['all output 64-bit words bit-exact','word count','final TLAST','keep/strb','input/output fully consumed'],
    report_sha256=sha256(report),fixture_sha256=sha256(fixture),header_sha256=sha256(header),
    sources={str(p.relative_to(root)):sha256(p) for p in (root/'hls/mage_decode_op01_one').iterdir() if p.is_file()},
    remaining=['maximum combined geometry and invalid protocol tests','RTL occupancy/backpressure/timeout','resource and implementation timing','board gates and matched performance'])
with exclusive_lock(base/'evidence.lock'):
    write_json(out,result)
    path=base/'STATE.json';state=json.loads(path.read_text())
    state['results']['decode_one_real_csim']=str(out.relative_to(root))
    state['next_action']='Decode-one real Gate/Up CSim passed. Complete boundary/negative tests, then RTL backpressure and implementation before board; stable build unchanged.'
    write_json(path,state)
    path=root/'deployment/mage_vl4b/BOARD_GATE_RESULT.json';index=json.loads(path.read_text(encoding='utf-8-sig'))
    index['latest_decode_one_real_csim']=dict(status=result['status'],result=str(out.relative_to(root)),sha256=sha256(out),board_deployed=False,performance_pass=False)
    write_json(path,index)
print(result['status'])
