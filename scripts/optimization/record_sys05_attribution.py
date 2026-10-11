"""Publish only the hash-bound, already-collected SYS05 attribution."""
import json
from pathlib import Path
from measurement import sha256, write_json, exclusive_lock

root=Path(__file__).resolve().parents[2]
base=root/'deployment/mage_vl4b/optimization_v1'
result_path=base/'runs/OP01-SYS05-decode-attribution/result.json'
result=json.loads(result_path.read_text())
source=base/'gates/G01-SYS-development/attempt_05/board_result.json'
if result['status']!='ATTRIBUTED_DIAGNOSTIC' or result['source_sha256']!=sha256(source):
    raise RuntimeError('Attribution source identity mismatch')
with exclusive_lock(base/'control.lock'):
    path=root/'deployment/mage_vl4b/BOARD_GATE_RESULT.json'
    index=json.loads(path.read_text(encoding='utf-8-sig'))
    index['latest_decode97_attribution']=dict(status=result['status'],
        result=str(result_path.relative_to(root)),sha256=sha256(result_path),
        numerical_acceptance=False,optimization_speedup_proven=False)
    write_json(path,index)
    path=base/'STATE.json';state=json.loads(path.read_text())
    state['results']['decode_attribution']=str(result_path.relative_to(root))
    state['next_action']='Use SYS05 real KV checkpoint for bounded replay: isolate file-read/cache behavior and capture layer0 gate_up real input for same-quant reference; no full-video rerun or speedup claim'
    write_json(path,state)
print('SYS05_ATTRIBUTION_INDEXED')
