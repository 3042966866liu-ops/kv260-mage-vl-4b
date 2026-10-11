"""Publish the bounded OP00/OP01 checkpoint from actual saved evidence only."""
from datetime import datetime, timezone
import json
from pathlib import Path
import re
from measurement import exclusive_lock, sha256, write_json

ROOT = Path(__file__).resolve().parents[2]
BASE = ROOT / 'deployment/mage_vl4b/optimization_v1'
load = lambda p: json.loads(Path(p).read_text(encoding='utf-8-sig'))
logs = {name: ROOT / f'tmp/op00_session/{name}.log'
        for name in ('shell_probe', 'os', 'memory', 'processes', 'manager')}
content = {k: p.read_text(encoding='utf-8-sig') for k, p in logs.items()}
for name in ('os', 'memory', 'manager'):
    if '__M75C_UART_RC_0__' not in content[name]:
        raise RuntimeError('Missing successful read-only result: ' + name)
if 'ubuntu@kria:' not in content['shell_probe'] or 'aarch64' not in content['os']:
    raise RuntimeError('Board shell/architecture not proved')
memory = {k: int(re.search(r'^' + k + r':\s+(\d+)\s+kB', content['memory'], re.M)[1])
          for k in ('MemTotal', 'MemAvailable', 'CmaTotal', 'CmaFree')}
result = {
    'schema_version': 1, 'gate_id': 'OP00-readonly-board-snapshot',
    'status': 'PROVISIONAL', 'observed_utc': datetime.now(timezone.utc).isoformat(),
    'scope': 'Read-only UART shell, OS, memory and process-name observation only',
    'architecture': 'aarch64', 'linux': '5.15.0-1027-xilinx-zynqmp',
    'memory_kib': memory, 'manager': 'operating', 'loaded_build_id': None,
    'matching_processes_found': False if '__M75C_UART_RC_1__' in content['processes'] else None,
    'process_pattern': 'tellme|mage|uvicorn',
    'process_rc_1_meaning': 'pgrep found no matching process; not an inference failure',
    'all_services_off_proved': False, 'root_authorization_checked': False,
    'board_mutated': False, 'new_fpga_transaction': False,
    'evidence': [{'path': str(p.relative_to(ROOT)), 'sha256': sha256(p)} for p in logs.values()],
    'remaining': ['live kernel register identity', 'XRT/PYNQ driver audit',
                  'device exclusive lock', 'verified existing service/overlay rollback commands'],
}
with exclusive_lock(BASE / 'control.lock'):
    snapshot = BASE / 'baselines/OP00_BOARD_READONLY.json'
    if snapshot.exists():
        raise RuntimeError('Use new attempt instead of replacing prior observation')
    write_json(snapshot, result)
    state = load(BASE / 'STATE.json')
    state['results']['board_readonly'] = str(snapshot)
    state['results']['wsl_identity'] = str(BASE / 'baselines/OP00_WSL_IDENTITY.json')
    state['next_action'] = 'Finish device lock/rollback audit; integrate real SYS and causal Decode event runner'
    write_json(BASE / 'STATE.json', state)
    environment = load(BASE / 'contracts/environment.json')
    environment['wsl'] = {'evidence': str(BASE / 'baselines/OP00_WSL_IDENTITY.json'),
                          'sha256': sha256(BASE / 'baselines/OP00_WSL_IDENTITY.json')}
    environment['live_board'] = {'evidence': str(snapshot), 'sha256': sha256(snapshot),
                                 'scope': result['scope']}
    write_json(BASE / 'contracts/environment.json', environment)
    board_path = ROOT / 'deployment/mage_vl4b/BOARD_GATE_RESULT.json'
    board = load(board_path)
    board['latest_optimization_v1_start'] = {
        'date': '2026-09-24', 'status': 'PROVISIONAL', 'goal': 'L1 then L2 then evidence-supported L3',
        'state': str((BASE / 'STATE.json').relative_to(ROOT)),
        'board_snapshot': str(snapshot.relative_to(ROOT)), 'board_snapshot_sha256': sha256(snapshot),
        'measurement_selftest': state['results']['selftest'],
        'wsl_identity': 'deployment/mage_vl4b/optimization_v1/baselines/OP00_WSL_IDENTITY.json',
        'new_fpga_execution': False, 'performance_improvement_measured': False,
        'achieved_level': None, 'stable_rollback_preserved': True,
        'historical_top_level_status_is_not_current_health_evidence': True,
    }
    write_json(board_path, board)
print(json.dumps(result, allow_nan=False))
