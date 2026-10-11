"""Export only the already saved fixture result, never execute its gate."""
import base64
import hashlib
import json
from pathlib import Path

path = Path('/home/ubuntu/m349_direct_hash_evidence_01/BOARD_RESULT.json')
raw = path.read_bytes()
code = json.loads(raw)['gate_return_code']
if type(code) is not int or code not in (0, 1):
    raise RuntimeError('Saved gate return code invalid')
chunks = [raw[i:i+1800] for i in range(0, len(raw), 1800)]
print('M349_RESULT_SHA256=' + hashlib.sha256(raw).hexdigest(), flush=True)
print('M349_SAVED_GATE_RC=' + str(code), flush=True)
for index, chunk in enumerate(chunks):
    print('M349_RESULT_CHUNK=' + str(index) + '/' + str(len(chunks)) + ':' + base64.b64encode(chunk).decode('ascii'), flush=True)
