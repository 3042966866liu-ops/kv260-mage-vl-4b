"""Freeze original Q and first-descriptor packets/goldens; no board commands."""
import copy
import importlib.util
import json
import sys
from pathlib import Path
from m355_reference import activation,digest
import m351_workflow as w
ROOT=Path(__file__).resolve().parents[2]
BASE=ROOT/'deployment/mage_vl4b/optimization_v1'
out=ROOT/'tmp/m357_board_fixture_01'
if out.exists():raise RuntimeError('Existing board fixture; inspect only')
source=BASE/'candidates/M355-device-phase-01/CASE_CONTRACT.json'
spec=json.loads(source.read_text(encoding='utf-8'));case=spec['cases'][0]
path=ROOT/'deployment/mage_vl4b/m175_m120_fixed_text_candidate/runtime/contract_runtime.py'
assert w.sha(path)==spec['stable_sources']['runtime/contract_runtime.py']['sha256']
ms=importlib.util.spec_from_file_location('contract_runtime',path)
module=importlib.util.module_from_spec(ms);sys.modules['contract_runtime']=module;ms.loader.exec_module(module)
packet=module.pack_chain_input(case['chain'],activation(case['chain']['groups']),case['base_words'],0)
assert digest(packet)==case['packet_sha256']
golden=(BASE/'runs/M355-device-phase-preparation-01/golden/0.bin').read_bytes()
assert digest(golden)==case['expected_ftz_sha256'] and len(golden)==524288
single=copy.deepcopy(case['chain']);single['descriptors']=single['descriptors'][:1];single['descriptor_count']=1
single['config_u32']=hex((int(single['config_u32'],16)&~0xff0000)|(1<<16))
single['input_bytes']=case['chain']['input_bytes']-16
single['output_bytes']=single['descriptors'][0]['output_bytes']
single['expected_macros']=single['descriptors'][0].get('expected_macros',1)
single_packet=module.pack_chain_input(single,activation(single['groups']),case['base_words'],0)
assert single_packet==packet[:16]+packet[32:]
single_golden=golden[:single['output_bytes']]
assert len(single_golden)==262144
zero=(8<<32|2<<42).to_bytes(8,'little')+bytes(8)+bytes(32*80)
out.mkdir()
for name,raw in [('q_packet.bin',packet),('q_golden.bin',golden),('descriptor_packet.bin',single_packet),('descriptor_golden.bin',single_golden),('build_packet.bin',zero),('build_golden.bin',bytes(1024))]:
    w.atomic(out/name,raw,immutable=True)
data=dict(schema='m357-original-q-board-fixtures-v1',stable_build='0x4D395832',candidate_build='0x4D333537',
    original_m355_contract_sha256=w.sha(source),original_q_case=case,single_descriptor_chain=single,
    stable_sources=spec['stable_sources'],layout_path=spec['layout_path'],layout_sha256=spec['layout_sha256'],
    build_config='0x00010201',build_scope='Original OP00 legal zero transaction; not a real-weight descriptor acceptance',
    files=[dict(path=p.name,bytes=p.stat().st_size,sha256=w.sha(p)) for p in sorted(out.iterdir())],
    board_executed=False,promoted=False)
w.atomic(out/'BOARD_CASES.json',w.encoded(data),immutable=True)
print(json.dumps(dict(status='PREPARED_ORIGINAL_Q_AND_DESCRIPTOR_BOARD_FIXTURES',sha256=w.sha(out/'BOARD_CASES.json'),files=len(data['files']))))
