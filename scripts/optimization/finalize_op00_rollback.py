"""Accept recovery preparation only from two completed stable hardware probes."""
import json
from pathlib import Path
from measurement import exclusive_lock, sha256, write_json
from board_safety import safe_to_release

ROOT = Path(__file__).resolve().parents[2]
BASE = ROOT / 'deployment/mage_vl4b/optimization_v1'
source = BASE / 'gates/G00-stable-probe/attempt_03/result.json'
collected = json.loads(source.read_text())
board = collected['board_result']
checks = {
    'board_probe_pass': collected['status'] == 'PASS' and collected['raw_process_exit_code'] == 0,
    'initial_build': board['build_id'] == '0x4D395832',
    'restore_build': board['restore_completion']['ap_return'] == int('4D395832', 16),
    'two_stable_loads': board['overlay_loads'] == 2,
    'first_completion_safe': safe_to_release(board['transaction']['release_snapshot']),
    'restored_completion_safe': safe_to_release(board['restore_snapshot']),
    'boot_protected': board['boot_unchanged'] and board['cmdline_unchanged'],
    'original_stopped_service_preserved': not board['initial_service']['port8001_listening']
        and not board['final_service']['port8001_listening'] and not board['service_changed'],
    'no_recovery_pending': not board['recovery_required'] and not board['unsafe_dma_buffers_retained'],
    'full_stable_package': board['preflight']['verified_file_count'] == 18,
}
if not all(checks.values()):
    raise RuntimeError('Recovery prerequisites fail: ' + repr(checks))
with exclusive_lock(BASE / 'control.lock'):
    path = BASE / 'gates/G00.2/attempt_01/result.json'
    if path.exists():
        raise RuntimeError('Immutable G00.2 attempt exists')
    result = dict(schema_version=1, gate_id='G00.2', status='PASS',
        candidate_id='OP00-stable-probe-03', attempt_id='attempt_01',
        input_manifest_sha256='24edbec4231ff5c96fb564406ad05ef6bb430610a431975a9b54e06f628ec4c8',
        environment_manifest_sha256=sha256(BASE / 'contracts/environment.json'),
        prerequisite_results=[str(source)],
        criteria=[dict(name=k, threshold=True, observed=v, passed=v, evidence=str(source)) for k,v in checks.items()],
        evidence_files=[dict(path=str(source), sha256=sha256(source))], metrics={}, failure_reason=None,
        rollback_result=dict(stable_reloaded=True, restored_minimal_transaction_pass=True, service_stopped=True),
        next_action='Complete board weight/runtime identity for G00.1 and real OP01 SYS/Decode integration',
        scope='Recovery preparation for unchanged stable T32; not permission/evidence for a new hardware candidate')
    write_json(path, result)
    rollback_path = BASE / 'contracts/rollback.json'
    rollback = json.loads(rollback_path.read_text())
    rollback.update(status='PASS_G00.2_STABLE_T32', device_lock='/tmp/tellme_kv260_execution.lock',
        previous_service_running=False, verified_stop_command=None,
        verified_restore_command={
            'runner': '/home/ubuntu/tellme_m120_m89x2_20260901/optimization_v1/OP00-stable-probe-03/run_op00_stable_probe.sh',
            'manifest_sha256': result['input_manifest_sha256'],
            'result_path_policy': 'fresh unique JSON under optimization_v1/results; never overwrite a prior attempt',
            'operation': 'preflight, stable zero transaction, reload same stable bit, second zero transaction'},
        new_overlay_allowed=False, reason='Unchanged stable restoration verified; new kernels still require their full gates',
        evidence=str(path))
    write_json(rollback_path, rollback)
    state_path = BASE / 'STATE.json'
    state = json.loads(state_path.read_text())
    state['results']['G00.2'] = str(path)
    state['next_action'] = result['next_action']
    state['board_mutation_scope'] = 'Isolated audit/probe packages and stable T32 reload only; boot/DTB/CMA/service unchanged'
    write_json(state_path, state)
    board_path = ROOT / 'deployment/mage_vl4b/BOARD_GATE_RESULT.json'
    index = json.loads(board_path.read_text(encoding='utf-8-sig'))
    index['latest_optimization_v1_rollback_gate'] = dict(status='PASS', gate_id='G00.2',
        result=str(path.relative_to(ROOT)), sha256=sha256(path), build_id=board['build_id'],
        restored_hardware_minimal_pass=True, model_performance_measured=False)
    write_json(board_path, index)
print(json.dumps(result))
