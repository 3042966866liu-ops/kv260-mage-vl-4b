"""Clean, immutable minimal board package. Never builds or accesses hardware."""
import argparse
import ast
import json
from pathlib import Path
from measurement import sha256, write_json

ROOT = Path(__file__).resolve().parents[2]
BASE = ROOT / 'deployment/mage_vl4b'
SCRIPTS = ROOT / 'scripts/optimization'
ARTIFACTS = BASE / 'optimization_v1/candidates/OP01-decode-one-experimental-artifacts'


def source_payloads():
    names = ('decode_one_minimal_board.py', 'decode_one_board_transaction.py',
             'decode_one_board_protocol.py', 'op00_stable_probe.py', 'board_safety.py',
             'measurement.py', 'run_decode_one_minimal_board.sh')
    sources = {name: SCRIPTS / name for name in names}
    sources['m120_board_common.py'] = BASE / 'm120_text4b_board_candidate/runtime/m120_board_common.py'
    sources['m120_board_env_preflight.py'] = BASE / 'm175_m120_fixed_text_candidate/runtime/m120_board_env_preflight.py'
    payloads = {name: path.read_bytes().replace(b'\r\n', b'\n') for name, path in sources.items()}
    candidate = payloads['m120_board_env_preflight.py']
    for old, new, count in (
        (b'overlay/m120_m89x2_t32.bit', b'overlay/op01_decode_one.bit', 1),
        (b'overlay/m120_m89x2_t32.hwh', b'overlay/op01_decode_one.hwh', 1),
        (b'M136-M120-board-environment', b'OP01-decode-one-board-environment', 2),
        (b'M136_M120_BOARD_ENV_', b'OP01_DECODE_ONE_BOARD_ENV_', 2)):
        if candidate.count(old) != count:
            raise RuntimeError('Preflight source changed; refuse ambiguous derivation: ' + repr(old))
        candidate = candidate.replace(old, new)
    payloads['decode_one_env_preflight.py'] = candidate
    # Complete recursive local module set; external modules remain target-runtime prerequisites.
    allowed = {'__future__', 'argparse', 'ast', 'fcntl', 'hashlib', 'json', 'math', 'os',
               'pathlib', 'shutil', 'statistics', 'subprocess', 'sys', 'tempfile', 'time',
               'contextlib', 'numpy', 'pynq'}
    local = {Path(name).stem for name in payloads if name.endswith('.py')}
    for name, payload in payloads.items():
        if not name.endswith('.py'):
            continue
        tree = ast.parse(payload.decode('utf-8'), filename=name)
        for node in ast.walk(tree):
            modules = ([x.name for x in node.names] if isinstance(node, ast.Import)
                       else [node.module] if isinstance(node, ast.ImportFrom) else [])
            for module in modules:
                if module is None or module.split('.')[0] not in allowed | local:
                    raise RuntimeError(f'Unclosed import in {name}: {module}')
    return payloads, sources


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--check-source-only', action='store_true')
    args = parser.parse_args()
    payloads, sources = source_payloads()
    if args.check_source_only:
        print('DECODE_ONE_MINIMAL_SOURCE_CLOSURE_PASS_NOT_BOARD_IMPORT')
        return
    manifest_path = ARTIFACTS / 'ARTIFACT_MANIFEST.json'
    manifest = json.loads(manifest_path.read_text())
    if (manifest['build_id'] != '0x4F503131' or manifest['formal_promotion_allowed'] is not False
            or manifest['capacity_status'] != 'STOPPED_BY_USER_NOT_PASS'):
        raise RuntimeError('Candidate identity or experimental scope changed')
    for row in manifest['files']:
        source = (ARTIFACTS / row['path']).resolve()
        source.relative_to(ARTIFACTS.resolve())
        if source.stat().st_size != row['bytes'] or sha256(source) != row['sha256']:
            raise RuntimeError('Artifact identity mismatch: ' + row['path'])
        if row['path'] in payloads:
            raise RuntimeError('Duplicate package path')
        payloads[row['path']] = source.read_bytes()
    payloads['ARTIFACT_MANIFEST.json'] = manifest_path.read_bytes()
    output = BASE / 'optimization_v1/candidates/OP01-decode-one-minimal-board-01'
    output.mkdir(exist_ok=False)
    items = []
    for name, data in payloads.items():
        destination = output / name
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes(data)
        items.append(dict(path=name, bytes=len(data), sha256=sha256(destination)))
    write_json(output / 'PACKAGE_MANIFEST.json', dict(schema_version=1,
        build_id='0x4F503131', capacity_status='STOPPED_BY_USER_NOT_PASS',
        formal_promotion_allowed=False, file_count=len(items),
        total_bytes=sum(x['bytes'] for x in items), files=items,
        preflight_derivation='Only candidate gate label and two required overlay paths changed',
        source_hashes={name: sha256(path) for name, path in sources.items()}))
    print(json.dumps(dict(package=str(output), manifest_sha256=sha256(output / 'PACKAGE_MANIFEST.json'))))


if __name__ == '__main__': main()
