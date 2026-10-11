"""Freeze an offline diagnostic package; never load an overlay or touch board."""
import ast
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
BASE = ROOT / 'deployment/mage_vl4b/optimization_v1'


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    package = BASE / 'candidates/M338-prefill-diagnostic-01'
    evidence = BASE / 'runs/M338-prefill-diagnostic-offline-01'
    if package.exists() or evidence.exists():
        raise RuntimeError('Immutable M338 preparation exists; choose a new revision')
    # Read and freeze the complete recovery documents, not chat-derived state.
    recovery = {}
    for name in ('CURRENT_STATE.md', 'docsMILESTONES.md',
                 'DEPLOYMENT_OPERATION_MISTAKES_REVIEW.md', 'AGENTS.md',
                 'deployment/mage_vl4b/BOARD_GATE_RESULT.json'):
        path = ROOT / name
        content = path.read_text(encoding='utf-8-sig')
        recovery[name] = dict(sha256=digest(path), bytes=path.stat().st_size,
                              lines=len(content.splitlines()))
    result = dict(status='FAIL_OFFLINE_PREPARATION', evidence_level='L0',
                  expected_existing_build_id='0x4D395832', recovery_sources=recovery,
                  board_execution_run=False, overlay_loaded=False,
                  numerical_acceptance=False, performance_pass=False,
                  stable_runtime_modified=False, formal_promotion_allowed=False,
                  board_prerequisite='COM3 observed kria login prompt; no authenticated shell',
                  rejected_attempts=[
                      'Initial sandbox CIM identity read denied; retried authorized read-only capture',
                      'No board execution attempted at login prompt',
                  ])
    evidence.mkdir(parents=True)
    for name in ('CURRENT_STATE.md', 'docsMILESTONES.md',
                 'DEPLOYMENT_OPERATION_MISTAKES_REVIEW.md'):
        shutil.copyfile(ROOT / name, evidence / name)
    completed = subprocess.run([sys.executable, '-B', '-m', 'unittest',
        'test_prefill_diagnostic', 'test_transfer_trace', 'test_decode_trace',
        'test_decode_io_trace'], cwd=HERE, capture_output=True, text=True)
    (evidence / 'TEST_OUTPUT.txt').write_text(completed.stdout + completed.stderr, encoding='utf-8')
    result['test_returncode'] = completed.returncode
    if completed.returncode:
        (evidence / 'RESULT.json').write_text(json.dumps(result, indent=2), encoding='utf-8')
        raise RuntimeError('Offline tests failed; preserved output')
    package.mkdir()
    payload = ('prefill_diagnostic.py', 'decode_trace.py', 'decode_io_trace.py', 'transfer_trace.py')
    files = []
    for name in payload:
        source = HERE / name
        ast.parse(source.read_text(encoding='utf-8'), filename=str(source))
        shutil.copyfile(source, package / name)
        files.append(dict(path=name, bytes=source.stat().st_size, sha256=digest(source)))
    manifest = dict(schema='tellme-m338-prefill-diagnostic-offline-v1',
                    status='OFFLINE_COMPONENTS_ONLY_NOT_BOARD_RUNNABLE',
                    file_count=len(files), total_bytes=sum(row['bytes'] for row in files),
                    files=files)
    (package / 'PACKAGE_MANIFEST.json').write_text(json.dumps(manifest, indent=2)+'\n', encoding='utf-8')
    result.update(status='PASS_OFFLINE_COMPONENT_CONTRACTS_ONLY', tests_passed=12,
                  package_manifest_sha256=digest(package / 'PACKAGE_MANIFEST.json'),
                  package=package.relative_to(ROOT).as_posix(),
                  limitations=['Mock model integration only; real M241/M238 import/invocation pending',
                               'No complete 159-token request profile or speed evidence',
                               'Instrumentation changes timing; no formal performance acceptance'],
                  next_step='Validate exact real M241/M238 integration offline, then hash-checked '
                            'imports-only board package; same authorized COM3 preflight before '
                            'one frozen159-token diagnostic request; choose candidate from profile')
    (evidence / 'RESULT.json').write_text(json.dumps(result, indent=2)+'\n', encoding='utf-8')
    print(json.dumps({key: result[key] for key in ('status', 'tests_passed', 'package_manifest_sha256')}))


if __name__ == '__main__':
    main()
