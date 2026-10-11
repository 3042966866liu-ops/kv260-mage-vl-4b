"""Build a clean dependency-closed diagnostic around the frozen M332 baseline runner."""
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
PACKAGE = BASE / 'candidates/M339-prefill-profile-04'


def digest(path): return hashlib.sha256(path.read_bytes()).hexdigest()


def replace_once(text, old, new):
    if text.count(old) != 1: raise RuntimeError('Replacement count mismatch: '+old)
    return text.replace(old, new)


def main():
    if PACKAGE.exists(): raise RuntimeError('Immutable package exists')
    # Freeze complete recovery inputs before deriving any operational runner.
    recovery = {name: digest(ROOT / name) for name in
                ('CURRENT_STATE.md', 'docsMILESTONES.md', 'DEPLOYMENT_OPERATION_MISTAKES_REVIEW.md',
                 'deployment/mage_vl4b/BOARD_GATE_RESULT.json')}
    for name in recovery: (ROOT / name).read_text(encoding='utf-8-sig')
    probe = json.loads((BASE / 'runs/M338-real-import-01/BOARD_RESULT.json').read_text())
    for row in probe['modules'].values():
        relative = row['path'].split('/tellme_release_install_20260926/')[1]
        source = ROOT / relative
        if digest(source) != row['sha256']: raise RuntimeError('Local/board source mismatch: '+relative)
    test = subprocess.run([sys.executable, '-B', '-m', 'unittest',
        'test_prefill_diagnostic', 'test_transfer_trace', 'test_decode_trace',
        'test_decode_io_trace', 'test_board_safety'], cwd=HERE, capture_output=True, text=True)
    if test.returncode: raise RuntimeError(test.stdout+test.stderr)
    PACKAGE.mkdir(parents=True)
    payload = ('m339_diagnostic_gate.py', 'prefill_diagnostic.py', 'decode_trace.py',
               'decode_io_trace.py', 'transfer_trace.py', 'board_safety.py')
    for name in payload: shutil.copyfile(HERE / name, PACKAGE / name)
    previous = BASE / 'candidates/M332-parser-scale-video-03'
    text = (previous / 'run_fixed_video_ab.py').read_text(encoding='utf-8').replace('M332','M339')
    text = replace_once(text, 'M339_SOURCE = PACKAGE / "m236_prefill_runtime.py"',
                        'M339_SOURCE = PACKAGE / "m339_diagnostic_gate.py"')
    text = replace_once(text, 'M339_SOURCE_SHA = "7e36223f762cfc04c0fc74e3f468664e05d38b8f8024c8eb194e77cdc12944e8"',
                        'M339_SOURCE_SHA = "'+digest(PACKAGE / 'm339_diagnostic_gate.py')+'"')
    text = replace_once(text, 'dirs = module_paths()', 'dirs = [PACKAGE] + module_paths()')
    text = replace_once(text, 'if VARIANT not in ("baseline", "candidate"):',
        'manifest_path = PACKAGE / "PACKAGE_MANIFEST.json"\n'
        '        if digest(manifest_path) != os.environ["M339_MANIFEST_SHA"]:\n'
        '            raise RuntimeError("Profile package manifest mismatch")\n'
        '        manifest = json.loads(manifest_path.read_text())\n'
        '        rows = manifest["files"]\n'
        '        expected = {row["path"] for row in rows}\n'
        '        actual = {p.name for p in PACKAGE.iterdir() if p.is_file() and p.name != "PACKAGE_MANIFEST.json"}\n'
        '        if actual != expected or len(rows) != manifest["file_count"] or len(expected) != len(rows):\n'
        '            raise RuntimeError("Profile package whitelist/count mismatch")\n'
        '        if sum(row["bytes"] for row in rows) != manifest["total_bytes"]:\n'
        '            raise RuntimeError("Profile package byte count mismatch")\n'
        '        for row in rows:\n'
        '            path = PACKAGE / row["path"]\n'
        '            if path.stat().st_size != row["bytes"] or digest(path) != row["sha256"]:\n'
        '                raise RuntimeError("Profile member mismatch: " + row["path"])\n'
        '        record["profile_manifest_sha256"] = digest(manifest_path)\n'
        '        if VARIANT not in ("baseline", "candidate"):')
    text = replace_once(text, '(VARIANT == "candidate" and path.resolve() == PACKAGE.resolve())',
                        '(path.resolve() == PACKAGE.resolve())')
    text = replace_once(text, 'str(candidate / "m277_fixed_window_gate.py")',
                        'str(PACKAGE / "m339_diagnostic_gate.py")')
    text = replace_once(text, 'if PREFLIGHT_ONLY:\n            record["status"]',
                        'from transfer_trace import instrument\n        from decode_io_trace import DecodeIOTrace\n'
                        '        import board_runtime\n        import m339_diagnostic_gate\n'
                        '        instrument(board_runtime.copy_window_to_buffer, DecodeIOTrace())\n'
                        '        record["diagnostic_wrapper_imported"] = True\n'
                        '        record["timing_eligible"] = False\n        record["performance_pass"] = False\n'
                        '        if PREFLIGHT_ONLY:\n            record["status"]')
    text = replace_once(text, 'record["status"] = "PASS_INDEPENDENT_VIDEO_E2E"',
                        'trace = json.loads((RESULTS / "prefill_trace.json").read_text())\n'
                        '        if trace["status"] != "RECORDED" or trace["input_shape"] != [159, 2560]:\n'
                        '            raise RuntimeError("Diagnostic trace missing or wrong geometry")\n'
                        '        record["trace_sha256"] = digest(RESULTS / "prefill_trace.json")\n'
                        '        record["status"] = "PASS_INSTRUMENTED_PREFILL_PROFILE_NOT_PERFORMANCE"')
    # Original subprocess timeout kills its group; do not kill unsafe retained DMA.
    text = replace_once(text, 'os.killpg(proc.pid, signal.SIGTERM)\n\n            timer',
                        'print("M339_TIMEOUT_REQUIRES_OPERATOR_RECOVERY", flush=True)\n\n            timer')
    text = replace_once(text, 'timer.start()\n            try:',
                        'timer.start()\n            heartbeat_stop = threading.Event()\n'
                        '            def heartbeat():\n'
                        '                while not heartbeat_stop.wait(30):\n'
                        '                    print("M339_HEARTBEAT child_pid=" + str(proc.pid) + " elapsed_s=" + str(round(time.monotonic()-started, 1)), flush=True)\n'
                        '            threading.Thread(target=heartbeat, daemon=True).start()\n            try:')
    text = replace_once(text, 'timer.cancel()\n                if proc.poll()',
                        'timer.cancel()\n                heartbeat_stop.set()\n                if proc.poll()')
    (PACKAGE / 'run_fixed_video_profile.py').write_text(text, encoding='utf-8', newline='\n')
    shell = (previous / 'run_m332_video_variant.sh').read_text().replace('M332','M339')
    shell = shell.replace('run_fixed_video_ab.py','run_fixed_video_profile.py')
    shell = shell.replace('variant=${1:?baseline or candidate required}', 'variant=baseline')
    shell = shell.replace('mode=${2:-full}', 'mode=${1:-preflight}')
    shell = shell.replace('sha256sum -c SHA256SUMS',
                          'manifest_sha=${2:?manifest SHA required}\n'
                          'printf "%s  PACKAGE_MANIFEST.json\\n" "$manifest_sha" | sha256sum -c -\n'
                          'sha256sum -c SHA256SUMS')
    shell = shell.replace('sudo -n env M339_VARIANT=',
                          'sudo -n env M339_MANIFEST_SHA="$manifest_sha" M339_VARIANT=')
    (PACKAGE / 'run_m339_profile.sh').write_text(shell, encoding='utf-8', newline='\n')
    names = sorted(p.name for p in PACKAGE.iterdir())
    for name in names:
        if name.endswith('.py'): ast.parse((PACKAGE / name).read_text(), filename=name)
    rows = [dict(path=name, bytes=(PACKAGE / name).stat().st_size, sha256=digest(PACKAGE / name)) for name in names]
    (PACKAGE / 'SHA256SUMS').write_text(''.join(r['sha256']+'  '+r['path']+'\n' for r in rows), newline='\n')
    rows.append(dict(path='SHA256SUMS', bytes=(PACKAGE / 'SHA256SUMS').stat().st_size, sha256=digest(PACKAGE / 'SHA256SUMS')))
    manifest = dict(schema='tellme-m339-profile-v1', file_count=len(rows),
                    total_bytes=sum(r['bytes'] for r in rows), files=rows,
                    recovery_source_sha256=recovery, hardware_changed=False,
                    performance_pass=False, existing_build='0x4D395832',
                    closure='Six local trace/wrapper dependencies; unchanged release closure checked by runner')
    (PACKAGE / 'PACKAGE_MANIFEST.json').write_text(json.dumps(manifest, indent=2)+'\n', newline='\n')
    (PACKAGE.parent / 'M339_BUILD_TEST_OUTPUT.txt').write_text(test.stdout+test.stderr)
    print(json.dumps(dict(package=str(PACKAGE), files=len(rows), bytes=manifest['total_bytes'],
                         manifest_sha256=digest(PACKAGE / 'PACKAGE_MANIFEST.json'))))


if __name__ == '__main__': main()
