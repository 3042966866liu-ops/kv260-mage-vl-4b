"""Read-only model/runtime closure, decoder discovery; never constructs Overlay."""
import argparse
import fcntl
import importlib
import importlib.metadata
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import time
from measurement import sha256, write_json

ROOT = Path('/home/ubuntu/tellme_m120_m89x2_20260901')


def verify_members(root, manifest_hash, *, manifest_name='PACKAGE_MANIFEST.json', allow_ready=False):
    path = root / manifest_name
    if sha256(path) != manifest_hash:
        raise RuntimeError('Manifest mismatch: ' + str(path))
    data = json.loads(path.read_text())
    for item in data['files']:
        file = (root / item['path']).resolve()
        file.relative_to(root.resolve())
        if file.stat().st_size != int(item['bytes']) or sha256(file) != item['sha256']:
            raise RuntimeError('Member mismatch: ' + str(file))
    expected = {item['path'] for item in data['files']} | {manifest_name}
    if allow_ready:
        ready = json.loads((root / 'PACKAGE_READY.json').read_text())
        if ready['package_manifest_sha256'] != manifest_hash:
            raise RuntimeError('Package ready identity mismatch')
        expected.add('PACKAGE_READY.json')
    actual = {p.relative_to(root).as_posix() for p in root.rglob('*') if p.is_file()
              and '__pycache__' not in p.parts and p.suffix != '.pyc'}
    if actual != expected:
        raise RuntimeError('Closure mismatch ' + str(root) + ': ' + repr(sorted(actual ^ expected)))
    return {'root': str(root), 'manifest_sha256': manifest_hash,
            'verified_files': len(data['files']), 'verified_bytes': sum(x['bytes'] for x in data['files'])}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--manifest-sha256', required=True)
    ap.add_argument('--result', type=Path, required=True)
    args = ap.parse_args()
    here = Path(__file__).resolve().parent
    verify_members(here, args.manifest_sha256)
    if args.result.exists():
        raise RuntimeError('Immutable result exists')
    targets = json.loads((here / 'inventory_targets.json').read_text())
    result = dict(status='FAIL', scope='OP00-model-runtime-identity', overlay_loaded=False,
                  packages=[], layouts=[], imports={}, decoders={}, errors=[])
    start = time.perf_counter()
    fd = os.open('/tmp/tellme_kv260_execution.lock', os.O_RDWR | os.O_CREAT, 0o600)
    try:
        fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        for item in targets['packages']:
            print('IDENTITY_PACKAGE_BEGIN ' + item['board_name'], flush=True)
            result['packages'].append(verify_members(ROOT / item['board_name'], item['sha256'],
                                                     allow_ready=item.get('allow_ready', False)))
            print('IDENTITY_PACKAGE_PASS ' + item['board_name'], flush=True)
        for item in targets['layouts']:
            print('IDENTITY_LAYOUT_BEGIN ' + item['board_path'], flush=True)
            result['layouts'].append(verify_members(ROOT / item['board_path'], item['sha256'],
                manifest_name='SIXPORT_LAYOUT_MANIFEST.json'))
            print('IDENTITY_LAYOUT_PASS ' + item['board_path'], flush=True)
        paths = [ROOT / path for path in targets['python_path']]
        sys.path[0:0] = [str(p) for p in paths]
        for name in ('numpy', 'tokenizers', 'torch', 'transformers', 'PIL',
                     'm238_prefill_runtime', 'm241_video_language_runtime', 'm222_vectorized_w4_runtime'):
            module = importlib.import_module(name)
            location = Path(module.__file__).resolve() if getattr(module, '__file__', None) else None
            result['imports'][name] = {'file': str(location),
                'sha256': sha256(location) if location and location.is_file() else None,
                'version': str(getattr(module, '__version__', 'unavailable'))}
        for name in ('ffmpeg', 'ffprobe'):
            binary = shutil.which(name)
            result['decoders'][name] = {'path': binary, 'version': None}
            if binary:
                p = subprocess.run([binary, '-version'], capture_output=True, text=True, timeout=10)
                result['decoders'][name].update(exit_code=p.returncode,
                    version=p.stdout.splitlines()[:1], sha256=sha256(binary))
        for name in ('av', 'opencv-python', 'imageio', 'Pillow'):
            try:
                value = importlib.metadata.version(name)
            except importlib.metadata.PackageNotFoundError:
                value = None
            result['decoders'][name] = value
        result['meminfo'] = Path('/proc/meminfo').read_text()
        result['platform'] = os.uname()._asdict() if hasattr(os.uname(), '_asdict') else list(os.uname())
        result['status'] = 'PASS'
    except Exception as exc:
        result['errors'].append(f'{type(exc).__name__}: {exc}')
    finally:
        os.close(fd)
        result['elapsed_s'] = time.perf_counter() - start
        write_json(args.result, result)
        print('OP00_MODEL_JSON_BEGIN', flush=True)
        print(json.dumps(result, allow_nan=False), flush=True)
        print('OP00_MODEL_JSON_END', flush=True)
    return 0 if result['status'] == 'PASS' else 1


if __name__ == '__main__':
    raise SystemExit(main())

