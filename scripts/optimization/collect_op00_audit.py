"""Collect the exact JSON printed by the bounded board audit; preserve raw UART."""
import json
from pathlib import Path
import re
from measurement import exclusive_lock, sha256, write_json

ROOT = Path(__file__).resolve().parents[2]
BASE = ROOT / 'deployment/mage_vl4b/optimization_v1'
log = ROOT / 'tmp/op00_audit01/run.log'
text = log.read_text(encoding='utf-8-sig')
payload = text.split('OP00_AUDIT_JSON_BEGIN', 1)[1].split('OP00_AUDIT_JSON_END', 1)[0].strip()
raw = json.loads(payload)
exit_match = re.search(r'__OP00_AUDIT_RC_(\d+)__', text)
if not exit_match:
    raise RuntimeError('Missing final process exit marker')
rc = int(exit_match[1])
with exclusive_lock(BASE / 'control.lock'):
    path = BASE / 'gates/G00-audit/attempt_01/result.json'
    if path.exists():
        raise RuntimeError('Immutable attempt exists')
    criteria = []
    for name, threshold, observed in (
        ('audit_exit', 0, rc), ('audit_status', 'PASS', raw['status']),
        ('xrt_probe_count', 1, raw.get('evidence', {}).get('xrt', {}).get('probe')),
        ('device_count', 1, raw.get('evidence', {}).get('xrt', {}).get('devices')),
        ('device_lock_exclusion', True, raw.get('evidence', {}).get('device_lock_exclusion')),
    ):
        criteria.append(dict(name=name, threshold=threshold, observed=observed,
                             passed=observed == threshold, evidence=str(log)))
    result = {'schema_version': 1, 'gate_id': 'G00-audit', 'attempt_id': 'attempt_01',
              'status': 'PASS' if all(x['passed'] for x in criteria) else 'FAIL',
              'candidate_id': 'OP00-audit-01',
              'input_manifest_sha256': sha256(BASE / 'candidates/OP00-audit-01/PACKAGE_MANIFEST.json'),
              'environment_manifest_sha256': sha256(BASE / 'contracts/environment.json'),
              'prerequisite_results': [], 'criteria': criteria, 'metrics': {},
              'evidence_files': [{'path': str(log), 'sha256': sha256(log)}],
              'failure_reason': None if rc == 0 else raw.get('errors'),
              'rollback_result': {'overlay_changed': False, 'service_changed': False,
                                  'boot_dtb_cma_changed': False, 'audit_package_retained': True},
              'next_action': 'Verify full stable package and executable load/restore; then Build-ID-only',
              'raw_process_exit_code': rc, 'board_result': raw,
              'full_G00_1_pass': False, 'full_G00_2_pass': False}
    write_json(path, result)
    state_path = BASE / 'STATE.json'
    state = json.loads(state_path.read_text())
    state['results']['board_environment_audit'] = str(path)
    state['board_mutated'] = True
    state['board_mutation_scope'] = 'Isolated audit package/result and advisory lock only; no overlay or service change'
    write_json(state_path, state)
    board_path = ROOT / 'deployment/mage_vl4b/BOARD_GATE_RESULT.json'
    board = json.loads(board_path.read_text(encoding='utf-8-sig'))
    board['latest_optimization_v1_board_audit'] = {
        'status': result['status'], 'result': str(path.relative_to(ROOT)), 'sha256': sha256(path),
        'scope': 'Environment/rollback-file/device-lock audit, not inference or full G00 acceptance',
        'current_web_8001_listening': False if ':8001' not in raw.get('evidence', {}).get('listeners', '') else None,
        'new_fpga_execution': False, 'stable_rollback_preserved': True}
    write_json(board_path, board)
print(json.dumps(result, allow_nan=False))
