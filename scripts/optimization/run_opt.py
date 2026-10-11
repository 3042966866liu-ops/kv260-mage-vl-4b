"""Versioned OP00/OP01 entry point; never connects to a board implicitly.

Unimplemented execution adapters return BLOCKED/exit 2, not a fictitious PASS.
Inspect and self-test operate on host files only. Each invocation preserves an
independent run directory; no historical board PASS is promoted by this tool.
"""
import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import subprocess
import sys
import uuid

sys.dont_write_bytecode = True
from measurement import exclusive_lock, sha256, write_json

ROOT = Path(__file__).resolve().parents[2]
BASE = ROOT / 'deployment/mage_vl4b/optimization_v1'
DEFAULT_CONFIG = BASE / 'contracts/config.json'
STEPS = {
    'OP00': ('Inventory and rollback', []), 'OP01': ('Measurement and baselines', ['OP00']),
    'OP02': ('Development quality and sealed evaluation', ['OP00', 'OP01-interface']),
    'OP03': ('MLP/Decode attribution and feasibility', ['OP01']),
    'OP04': ('Quality-constrained T32 token budgets', ['OP02', 'OP03']),
    'OP05': ('First-use vision optimization', ['OP02', 'OP03']),
    'OP06': ('Single language optimization', ['OP03']),
    'OP07': ('Combine accepted candidates', ['OP04/05/06-available']),
    'OP08': ('Blind quality and formal tier acceptance', ['OP07']),
    'OP09': ('Web integration and stability', ['L1-PASS']),
    'OP10': ('Attribution, limitations and delivery', ['completed-or-blocked-evidence']),
}


def load(path):
    return json.loads(Path(path).read_text(encoding='utf-8-sig'))


def gate(gate_id, run_id, status, candidate, criteria, reason=None):
    return dict(schema_version=1, gate_id=gate_id, attempt_id=run_id, status=status,
                candidate_id=candidate, input_manifest_sha256=None,
                environment_manifest_sha256=None, prerequisite_results=[],
                criteria=criteria, metrics={}, evidence_files=[], failure_reason=reason,
                rollback_result={'board_mutated': False, 'restore_needed': False},
                next_action='Complete live identity/rollback and integrate real token-ready runner')


def inspect(config, run):
    records = []
    for name in config['references']:
        path = ROOT / name
        records.append({'path': name, 'exists': path.is_file(),
                        'bytes': path.stat().st_size if path.is_file() else None,
                        'sha256': sha256(path) if path.is_file() else None})
    manifest_path = ROOT / config['stable_artifact_manifest']
    manifest_match = sha256(manifest_path) == config['stable_artifact_manifest_sha256']
    stable = []
    for item in load(manifest_path):
        path = (manifest_path.parent / item['path']).resolve()
        path.relative_to(manifest_path.parent.resolve())
        observed = sha256(path) if path.is_file() else None
        stable.append({**item, 'observed_sha256': observed,
                       'match': observed == item['sha256'] and path.stat().st_size == item['bytes']})
    source = Path(config['source_contract'])
    frozen = BASE / 'contracts/source_execution_contract.md'
    if frozen.exists() and sha256(frozen) != sha256(source):
        raise ValueError('Source contract changed: explicit new version required')
    if not frozen.exists():
        frozen.write_bytes(source.read_bytes())
    wsl_path = BASE / 'baselines/OP00_WSL_IDENTITY.json'
    board_path = BASE / 'baselines/OP00_BOARD_READONLY.json'
    identity = {'references': records, 'stable_files': stable,
                'stable_manifest_match': manifest_match,
                'source_contract_sha256': sha256(source),
                'git_directory_present': (ROOT / '.git').exists(),
                'git_commit': None, 'build_id_historical': config['build_id'],
                'live_build_id': None, 'live_board_observed': False,
                'wsl_identity_evidence': str(wsl_path) if wsl_path.exists() else None,
                'wsl_weights_currently_verified': False,
                'note': 'Host SHA audit only; historical board results are not live observations.'}
    write_json(run / 'identity.json', identity)
    write_json(BASE / 'baselines/identity.json', identity)
    environment = {'workspace': str(ROOT), 'python_used': sys.executable,
                   'config_sha256': sha256(config['_config_path']),
                   'source_contract_sha256': sha256(source),
                   'board_transport': 'COM3-only, explicit locked runner',
                   'live_board': None, 'wsl': None,
                   'verified_tools': {name: Path(config[name]).is_file()
                                      for name in ('windows_python', 'powershell')}}
    # Preserve old observation separately; attaching it does not make it fresh.
    for key, path in (('wsl', wsl_path), ('live_board', board_path)):
        if path.exists():
            environment[key] = {'evidence': str(path), 'sha256': sha256(path),
                                'fresh_in_this_inspection': False}
    write_json(run / 'environment.json', environment)
    write_json(BASE / 'contracts/environment.json', environment)
    missing = sum(not x['exists'] for x in records)
    failures = sum(not x['match'] for x in stable) + (not manifest_match)
    criteria = [
        dict(name='host_reference_missing', threshold=0, observed=missing, passed=missing == 0,
             evidence=str(run / 'identity.json')),
        dict(name='stable_artifact_mismatch', threshold=0, observed=failures, passed=failures == 0,
             evidence=str(run / 'identity.json')),
        dict(name='live_board_and_wsl_identity', threshold='verified', observed=None, passed=False,
             evidence=None),
    ]
    result = gate('G00.1', run.name, 'FAIL' if missing or failures else 'BLOCKED',
                  config['candidate_id'], criteria, 'Complete live kernel/driver identity and rollback audit required')
    result['environment_manifest_sha256'] = sha256(run / 'environment.json')
    result['input_manifest_sha256'] = sha256(run / 'identity.json')
    result['evidence_files'] = [str(run / 'identity.json'), str(run / 'environment.json')]
    write_json(BASE / 'gates/G00.1' / run.name / 'result.json', result)
    report = ['# OP00 inventory — local audit only', '',
              f'Contract SHA-256: `{sha256(source)}`',
              f'Local references: {len(records)}, missing: {missing}.',
              f'Stable artifacts: {len(stable)}, mismatches including manifest: {failures}.',
              '', '## Still required', '',
              '- Current WSL model/tokenizer/checkpoint identity (do not copy large weights).',
              '- Fresh FTDI/board OS, memory, driver and kernel identity.',
              '- Actual service state and exact restore command; do not start a previously stopped service.',
              '- Device-side exclusive lock and executable rollback audit before any overlay action.',
              '', 'No deployment or speedup was performed. G00.1 is not a full PASS.',
              'Historical M277 single-frame binary TTFT cannot substitute for four-frame SYS.',
              'M320 software full-keep equality does not prove PL arithmetic or semantic correctness.',
              '', f'Evidence: `{run / "identity.json"}`', '']
    (BASE / 'reports/OP00_INVENTORY.md').write_text('\n'.join(report), encoding='utf-8')
    return result


def selftest(config, run):
    command = [sys.executable, '-B', '-m', 'unittest', 'discover', '-s', str(Path(__file__).parent),
               '-p', 'test_*.py', '-v']
    proc = subprocess.run(command, text=True, capture_output=True, timeout=60)
    log = run / 'measurement_selftest.log'
    log.write_text(proc.stdout + proc.stderr, encoding='utf-8')
    result = gate('G01.1-selftest', run.name, 'PASS' if proc.returncode == 0 else 'FAIL',
                  config['candidate_id'], [dict(name='synthetic_contract_tests', threshold=0,
                  observed=proc.returncode, passed=proc.returncode == 0, evidence=str(log))])
    result['evidence_scope'] = 'HOST_SYNTHETIC_MEASUREMENT_TEST_ONLY'
    result['full_G01_1_pass'] = False
    result['board_performance_measured'] = False
    result['raw_process_exit_code'] = proc.returncode
    result['sources'] = {p.name: sha256(p) for p in [Path(__file__), Path(__file__).with_name('measurement.py'),
                        Path(__file__).with_name('causal_generation.py'),
                        Path(__file__).with_name('board_safety.py'),
                        Path(__file__).with_name('sys_video_input.py'),
                        Path(__file__).with_name('sys_request.py'),
                        Path(__file__).with_name('video_contract_v2.py'),
                        Path(__file__).with_name('decode_trace.py'),
                        Path(__file__).with_name('decode_diagnostic.py'),
                        Path(__file__).with_name('decode_checkpoint.py'),
                        Path(__file__).with_name('summarize_decode_trace.py'),
                        Path(__file__).with_name('transfer_trace.py'),
                        Path(__file__).with_name('numerical_capture.py'),
                        Path(__file__).with_name('m120_group_reference.py'),
                        *Path(__file__).parent.glob('test_*.py')]}
    result['evidence_files'] = [str(log)]
    write_json(BASE / 'gates/G01.1-selftest' / run.name / 'result.json', result)
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    subs = parser.add_subparsers(dest='command', required=True)
    for name in ('inspect', 'selftest', 'baseline', 'profile', 'evaluate', 'gate', 'report'):
        sub = subs.add_parser(name)
        sub.add_argument('--config', type=Path, default=DEFAULT_CONFIG)
        if name == 'baseline':
            sub.add_argument('--track', choices=['sys', 'fix', 'decode'], required=True)
        if name == 'profile':
            sub.add_argument('--family', required=True)
        if name == 'evaluate':
            sub.add_argument('--split', choices=['dev', 'eval'], required=True)
        if name == 'gate':
            sub.add_argument('--id', required=True)
        if name == 'report':
            sub.add_argument('--level', choices=['L1', 'L2', 'L3'], required=True)
    args = parser.parse_args()
    config = load(args.config)
    config['_config_path'] = str(args.config.resolve())
    for folder in ('contracts', 'datasets', 'baselines', 'candidates', 'runs', 'gates', 'reports'):
        (BASE / folder).mkdir(parents=True, exist_ok=True)
    run_id = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ') + '-' + uuid.uuid4().hex[:8]
    run = BASE / 'runs' / run_id
    run.mkdir()
    print(f'RUN_DIRECTORY={run}', flush=True)
    with exclusive_lock(BASE / 'control.lock'):
        if args.command == 'inspect':
            result = inspect(config, run)
        elif args.command == 'selftest':
            result = selftest(config, run)
        elif args.command == 'report':
            result = {'status': 'PROVISIONAL', 'requested_level': args.level, 'achieved_level': None,
                      'reason': 'No OP08 formal acceptance exists; historical measurements are separate',
                      'board_performance_measured': False}
        else:
            reason = ('Evaluation is sealed: no frozen candidate, blind predictions and scoring manifest'
                      if args.command == 'evaluate' and args.split == 'eval'
                      else 'Execution adapter pending verified OP00 rollback and OP01 board integration')
            result = gate(getattr(args, 'id', args.command), run_id, 'BLOCKED',
                          config['candidate_id'], [], reason)
        write_json(run / 'result.json', result)
        if args.command in ('inspect', 'selftest'):
            state_path = BASE / 'STATE.json'
            state = load(state_path) if state_path.exists() else {
                'schema_version': 1, 'goal_status': 'ACTIVE', 'achieved_level': None,
                'board_mutated': False, 'steps': {k: {'title': v[0], 'dependencies': v[1],
                    'status': 'NOT_RUN'} for k, v in STEPS.items()}, 'results': {}}
            state['results'][args.command] = str(run / 'result.json')
            # A host inspect/selftest cannot revoke completed board gates, nor
            # promote their status. Only begin its own still-unstarted step.
            step = 'OP00' if args.command == 'inspect' else 'OP01'
            if state['steps'][step]['status'] == 'NOT_RUN':
                state['steps'][step]['status'] = 'RUNNING'
            state['updated_utc'] = datetime.now(timezone.utc).isoformat()
            write_json(state_path, state)
    print(json.dumps(result, ensure_ascii=False, allow_nan=False))
    return 0 if result['status'] == 'PASS' else 2


if __name__ == '__main__':
    raise SystemExit(main())
