import json
import re
from pathlib import Path
from measurement import exclusive_lock, sha256, write_json

ROOT = Path(__file__).resolve().parents[2]
BASE = ROOT / 'deployment/mage_vl4b/optimization_v1'
log = ROOT / 'tmp/op00_import_decode01/run.log'
text = log.read_text(encoding='utf-8-sig')
raw = json.loads(text.split('OP00_IMPORT_JSON_BEGIN',1)[1].split('OP00_IMPORT_JSON_END',1)[0])
rc = int(re.search(r'__OP00_IMPORT_RC_(\d+)__', text)[1])
with exclusive_lock(BASE / 'control.lock'):
    output = BASE / 'gates/G00-import-decode/attempt_01/result.json'
    if output.exists():
        raise RuntimeError('Immutable attempt exists')
    result = dict(status=raw['status'], raw_process_exit_code=rc, board_result=raw,
        evidence_files=[dict(path=str(log), sha256=sha256(log))],
        complete_G00_1_pass=False, model_inference=False)
    write_json(output, result)
    index_path = ROOT / 'deployment/mage_vl4b/BOARD_GATE_RESULT.json'
    index = json.loads(index_path.read_text(encoding='utf-8-sig'))
    index['latest_optimization_v1_import_decode'] = dict(status=raw['status'],
        result=str(output.relative_to(ROOT)), sha256=sha256(output), errors=raw['errors'],
        runtime_imports_pass=raw.get('runtime_imports_pass'), raw_video_decode_pass=raw.get('raw_video_decode_pass'),
        overlay_loaded=False)
    write_json(index_path,index)
    state_path = BASE / 'STATE.json'
    state = json.loads(state_path.read_text())
    state['results']['board_import_decode'] = str(output)
    state['next_action'] = 'Runtime imports verified; provision isolated raw-video decoder without modifying existing M190 runtime'
    write_json(state_path,state)
print(json.dumps(dict(status=raw['status'], result=str(output))))
