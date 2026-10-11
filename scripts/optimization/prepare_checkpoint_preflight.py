import hashlib
import json
from pathlib import Path
from measurement import sha256,write_json
root=Path(__file__).resolve().parents[2];base=root/'deployment/mage_vl4b/optimization_v1'
source=base/'gates/G01-SYS-development/attempt_05/board_result.json';data=json.loads(source.read_text())
checkpoint=data['decode_diagnostic']['checkpoint']
if checkpoint['status']!='RECORDED' or len(checkpoint['files'])!=72:raise RuntimeError('Checkpoint incomplete')
# Same serialized-byte contract as frozen measurement.write_json. Board must
# independently check actual file bytes; a mismatch is not silently normalized.
expected=hashlib.sha256((json.dumps(checkpoint,ensure_ascii=False,indent=2,allow_nan=False)+'\n').encode()).hexdigest()
out=base/'runs/OP01-checkpoint-preflight-01/plan.json'
if out.exists():raise RuntimeError('Immutable plan')
write_json(out,dict(source_sha256=sha256(source),checkpoint_manifest_sha256=expected,
    identity=checkpoint['identity'],next_token=checkpoint['next_token'],
    package_manifest_sha256=sha256(base/'candidates/OP01-SYS-05/PACKAGE_MANIFEST.json')))
print('CHECKPOINT_EXPECTED_MANIFEST '+expected)
