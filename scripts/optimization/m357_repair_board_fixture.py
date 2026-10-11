"""Preserve incorrect offline OP00 oracle; repair before any board upload."""
import copy
import json
import shutil
from pathlib import Path
import m351_workflow as w
ROOT=Path(__file__).resolve().parents[2]
BASE=ROOT/'deployment/mage_vl4b/optimization_v1'
old=ROOT/'tmp/m357_board_fixture_01';out=ROOT/'tmp/m357_board_fixture_02'
if out.exists():raise RuntimeError('Existing corrected fixture; inspect only')
assert w.sha(old/'BOARD_CASES.json')=='c21e795bd292ac396f74fc3ae70036f081bd63769abd27df8bdcd13e0d62b2fa'
original=BASE/'candidates/M341-build-id-01/m341_build_id_gate.py'
text=original.read_text(encoding='utf-8')
assert 'output_bytes = 32 * 4 * 4 * 8' in text
packet=(old/'build_packet.bin').read_bytes();descriptor=int.from_bytes(packet[:16],'little')
rows=(descriptor>>32)&1023;bits=(descriptor>>42)&7
assert rows==8 and bits==2 and len(packet)==16+32*80
words=rows//8*32*4*4;size=words*8
assert words==512 and size==32*4*4*8==4096
out.mkdir()
for p in old.iterdir():
    if p.name not in ('BOARD_CASES.json','build_golden.bin'):shutil.copyfile(p,out/p.name)
w.atomic(out/'build_golden.bin',bytes(size),immutable=True)
spec=copy.deepcopy(json.loads((old/'BOARD_CASES.json').read_text(encoding='utf-8')))
spec['schema']='m357-original-q-board-fixtures-v2'
spec['files']=[dict(path=p.name,bytes=p.stat().st_size,sha256=w.sha(p)) for p in sorted(out.iterdir())]
spec['build_output_contract']=dict(rows_per_shard=rows,tokens=32,shards=4,pairs_per8rows=4,wire_word_bytes=8,output_words=words,output_bytes=size,original_gate_source_sha256=w.sha(original))
w.atomic(out/'BOARD_CASES.json',w.encoded(spec),immutable=True)
result=dict(status='CORRECTED_OFFLINE_OP00_REFERENCE_BEFORE_UPLOAD',build_id='0x4D333537',
    rejected_contract_sha256=w.sha(old/'BOARD_CASES.json'),corrected_contract_sha256=w.sha(out/'BOARD_CASES.json'),
    original_gate_source_sha256=w.sha(original),old_incorrect_bytes=1024,correct_wire_bytes=size,
    q_and_descriptor_unchanged=all(w.sha(old/p)==w.sha(out/p) for p in ['q_packet.bin','q_golden.bin','descriptor_packet.bin','descriptor_golden.bin','build_packet.bin']),
    files=[dict(path=p.relative_to(ROOT).as_posix(),sha256=w.sha(p)) for p in sorted(out.iterdir())],
    old_bundle_never_uploaded=True,board=False,hardware_pass=False)
ev=BASE/'runs/M357-board-fixture-repair-01/RESULT.json';w.atomic(ev,w.encoded(result),immutable=True);digest=w.sha(ev)
w.sync('M357_board_fixture_repair',dict(status=result['status'],sha256=digest,evidence_path=ev.relative_to(ROOT).as_posix(),build_id='0x4D333537'),
    'M357 板前原始门禁源码/字数独立复核发现零事务输出参考1024B错误，正确512words/4096B；未上传/0板端事务，保留01在02修正，真实Q及单descriptor不变。证据 '+digest)
print(json.dumps(dict(status=result['status'],sha256=digest,corrected_contract_sha256=result['corrected_contract_sha256'])))
