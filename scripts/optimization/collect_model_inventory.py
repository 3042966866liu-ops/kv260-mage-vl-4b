import json
import re
from pathlib import Path
from measurement import exclusive_lock, sha256, write_json
ROOT = Path(__file__).resolve().parents[2]
BASE = ROOT / 'deployment/mage_vl4b/optimization_v1'
log = ROOT / 'tmp/op00_model_inventory01/run.log'
text = log.read_text(encoding='utf-8-sig')
raw = json.loads(text.split('OP00_MODEL_JSON_BEGIN',1)[1].split('OP00_MODEL_JSON_END',1)[0])
rc = int(re.search(r'__OP00_MODEL_RC_(\d+)__', text)[1])
with exclusive_lock(BASE / 'control.lock'):
    output = BASE / 'gates/G00-model-inventory/attempt_01/result.json'
    if output.exists():
        raise RuntimeError('Immutable attempt exists')
    raw_path = output.with_name('board_raw.json')
    write_json(raw_path, raw)
    result = dict(status=raw['status'], raw_process_exit_code=rc, board_result=raw,
        evidence_files=[dict(path=str(log),sha256=sha256(log)),dict(path=str(raw_path),sha256=sha256(raw_path))],
        complete_G00_1_pass=False, overlay_loaded=False)
    write_json(output, result)
    index_path = ROOT / 'deployment/mage_vl4b/BOARD_GATE_RESULT.json'
    index = json.loads(index_path.read_text(encoding='utf-8-sig'))
    index['latest_optimization_v1_model_inventory'] = dict(status=raw['status'],
        result=str(output.relative_to(ROOT)), sha256=sha256(output), errors=raw['errors'],
        verified_package_count=len(raw['packages']), verified_layout_count=len(raw['layouts']), overlay_loaded=False)
    write_json(index_path,index)
    state_path = BASE / 'STATE.json'
    state = json.loads(state_path.read_text())
    state['results']['board_model_inventory'] = str(output)
    state['next_action'] = 'Retain successful full-file hashes; correct isolated m190 Python path and audit imports/decoder only'
    write_json(state_path,state)
print(json.dumps(dict(status=raw['status'],raw_board_json_sha256=sha256(raw_path),result=str(output))))
