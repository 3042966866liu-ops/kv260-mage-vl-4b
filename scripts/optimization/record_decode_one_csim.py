import json
from pathlib import Path
from measurement import sha256,write_json,exclusive_lock
root=Path(__file__).resolve().parents[2];base=root/'deployment/mage_vl4b/optimization_v1'
report=root/'tmp/op01_decode_one_csim/hls/csim/report/op01_decode_one_kernel_csim.log'
text=report.read_text();header=base/'runs/OP01-decode-one-header/result.json'
assert text.count('M128_CHAIN_PASS')==14 and text.count('M128_OUTPUT_WORDS=16384')==2
assert 'OP01_T32_AND_DECODE_ONE_NUMERICAL_PASS' in text
assert json.loads(header.read_text())['missing']==[]
out=base/'gates/G02-decode-one-csim/attempt_01/result.json'
if out.exists():raise RuntimeError('Immutable result exists')
result=dict(status='PASS_NUMERICAL_CSIM_ONLY',build_id='0x4F503131',board_deployed=False,
    modes=['legacy_T32','decode_one_full_T32_wire'],real_fixture_chains_per_mode=7,
    groups=[40,64,152],weight_bits=[2,4],maximum_test_descriptors=10,
    coverage='Frozen real-record microtiles; full-family live capture, max-row RTL/backpressure, resource/timing remain pending',
    report_sha256=sha256(report),header_sha256=sha256(header),
    sources={str(p.relative_to(root)):sha256(p) for p in (root/'hls/mage_decode_op01_one').iterdir() if p.is_file()},
    rejected_launches=['Initial pwd was tool-owned, fixture path rejected before CSim',
        'Absolute Windows project path creation rejected; used verified temporary T mapping; launcher zero was not accepted as PASS'])
with exclusive_lock(base/'evidence.lock'):
    write_json(out,result)
    p=base/'STATE.json';state=json.loads(p.read_text());state['results']['decode_one_csim']=str(out.relative_to(root))
    state['next_action']='Extend decode_one to captured real Gate/Up and max geometry/negative packet tests, then RTL/backpressure and implementation gates. Stable T32 unchanged; no board promotion.'
    write_json(p,state)
    p=root/'deployment/mage_vl4b/BOARD_GATE_RESULT.json';index=json.loads(p.read_text(encoding='utf-8-sig'))
    index['latest_decode_one_csim']=dict(status=result['status'],result=str(out.relative_to(root)),sha256=sha256(out),board_deployed=False)
    write_json(p,index)
print('DECODE_ONE_NUMERICAL_CSIM_PASS_ONLY')
