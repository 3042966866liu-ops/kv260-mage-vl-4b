"""User-authorized experimental export, explicitly NOT a capacity-gate PASS."""
import json
import shutil
from pathlib import Path
from measurement import sha256, write_json

root = Path(__file__).resolve().parents[2]
base = root/'deployment/mage_vl4b/optimization_v1'
stop_path = base/'gates/G02-decode-one-occupancy/attempt_03/result.json'
stop = json.loads(stop_path.read_text())
if stop['status'] != 'STOPPED_BY_USER_NOT_PASS':
    raise RuntimeError('Expected explicit user-stop evidence')
prior_path = base/'runs/OP01-decode-one-prerequisite-audit/result.json'
prior = json.loads(prior_path.read_text())
if prior['status'] != 'PASS_SAVED_IDENTITY_AUDIT_ONLY':
    raise RuntimeError('Missing prerequisite identity audit')
for relative, digest in prior['evidence'].items():
    p = (root/relative).resolve()
    p.relative_to(root)
    if sha256(p) != digest:
        raise RuntimeError('Prior identity changed: '+relative)
source = root/'tmp/op01_decode_one_rtl'
target = root/'tmp/op01_decode_one_experimental_export'
if target.exists():
    raise RuntimeError('Refuse existing experimental staging')
shutil.copytree(source, target, ignore=shutil.ignore_patterns('csim','sim','impl','*.log','*.jou'))
app = target/'hls.app'
text = app.read_text()
if text.count('name="op01_decode_one_rtl"') != 1:
    raise RuntimeError('Unexpected project identity')
app.write_text(text.replace('name="op01_decode_one_rtl"','name="op01_decode_one_experimental_export"'))
write_json(target/'EXPERIMENTAL_PREREQUISITES.json', {
    'status': 'EXPERIMENTAL_PREPARED_NOT_EXPORTED', 'build_id': '0x4F503131',
    'user_instruction': '停止这个直接上板吧',
    'capacity_gate_pass': False, 'formal_promotion_allowed': False,
    'stop_evidence_sha256': sha256(stop_path), 'prior_audit_sha256': sha256(prior_path),
    'revalidated_files': len(prior['evidence']),
    'copied_inputs': {p.relative_to(target).as_posix(): sha256(p) for p in target.rglob('*') if p.is_file()},
    'board_deployed': False, 'performance_pass': False})
print('EXPERIMENTAL_EXPORT_PREPARED_CAPACITY_INCOMPLETE')
