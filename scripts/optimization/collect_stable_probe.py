"""Persist immutable probe outcome before updating current project indexes."""
import argparse
import json
import re
from pathlib import Path
from measurement import exclusive_lock, sha256, write_json

ap = argparse.ArgumentParser()
ap.add_argument('--attempt', required=True)
args = ap.parse_args()
if not re.fullmatch(r'\d{2}', args.attempt):
    raise ValueError('two-digit attempt required')
root = Path(__file__).resolve().parents[2]
base = root / 'deployment/mage_vl4b/optimization_v1'
raw_path = root / f'tmp/op00_stable_probe{args.attempt}/run.log'
text = raw_path.read_text(encoding='utf-8-sig')
raw = json.loads(text.split('OP00_PROBE_JSON_BEGIN', 1)[1].split('OP00_PROBE_JSON_END', 1)[0].strip())
match = re.search(r'__OP00_PROBE_RC_(\d+)__', text)
rc = int(match[1]) if match else None
with exclusive_lock(base / 'control.lock'):
    dest = base / f'gates/G00-stable-probe/attempt_{args.attempt}/result.json'
    if dest.exists():
        raise RuntimeError('Immutable result exists')
    result = dict(gate_id='G00-stable-probe', attempt_id=args.attempt,
        status='PASS' if raw['status'] == 'PASS' and rc == 0 else 'FAIL',
        raw_process_exit_code=rc, board_result=raw, metrics={},
        failure_reason=raw.get('errors'),
        evidence_files=[dict(path=str(raw_path), sha256=sha256(raw_path))],
        no_model_performance_claim=True)
    write_json(dest, result)
    board_path = root / 'deployment/mage_vl4b/BOARD_GATE_RESULT.json'
    board = json.loads(board_path.read_text(encoding='utf-8-sig'))
    board['latest_optimization_v1_stable_probe'] = dict(
        status=result['status'], result=str(dest.relative_to(root)), sha256=sha256(dest),
        build_id=raw['build_id'], overlay_loads=raw['overlay_loads'],
        recovery_required=raw['recovery_required'], errors=raw['errors'],
        scope='Stable load/minimal-zero/restore gate; not inference performance')
    write_json(board_path, board)
    state_path = base / 'STATE.json'
    state = json.loads(state_path.read_text())
    state['results']['stable_probe'] = str(dest)
    state['next_action'] = ('Connect real model measurements' if result['status'] == 'PASS'
                            else 'Debug same stable-probe level; do not run full model')
    write_json(state_path, state)
print(json.dumps(result, ensure_ascii=False))
