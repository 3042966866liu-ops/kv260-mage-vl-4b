"""Read-only import closure and raw-video decode. Never constructs a model/Overlay."""
import argparse
import fcntl
import importlib
import json
import os
from pathlib import Path
import platform
import shutil
import sys
import time
from measurement import sha256, write_json

ROOT = Path('/home/ubuntu/tellme_m120_m89x2_20260901')


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--manifest-sha256', required=True)
    parser.add_argument('--result', type=Path, required=True)
    args = parser.parse_args()
    here = Path(__file__).resolve().parent
    manifest = here / 'PACKAGE_MANIFEST.json'
    if sha256(manifest) != args.manifest_sha256 or args.result.exists():
        raise RuntimeError('Manifest mismatch or immutable result already exists')
    records = json.loads(manifest.read_text())['files']
    expected = {r['path'] for r in records} | {'PACKAGE_MANIFEST.json'}
    actual = {p.relative_to(here).as_posix() for p in here.rglob('*') if p.is_file()}
    if actual != expected:
        raise RuntimeError('Candidate closure mismatch')
    for row in records:
        path = (here / row['path']).resolve()
        path.relative_to(here)
        if path.stat().st_size != row['bytes'] or sha256(path) != row['sha256']:
            raise RuntimeError('Candidate member mismatch: ' + row['path'])
    config = json.loads((here / 'probe_config.json').read_text())
    start = time.perf_counter()
    result = dict(status='FAIL', scope='OP00-imports-and-OP01-raw-video-decode-only',
                  overlay_loaded=False, imports={}, decoders={}, errors=[],
                  model_inference=False, build_id_not_read=True)
    fd = os.open('/tmp/tellme_kv260_execution.lock', os.O_RDWR | os.O_CREAT, 0o600)
    try:
        fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        if os.geteuid() != 0:
            raise RuntimeError('Authorized root session required')
        previous = ROOT / 'optimization_v1/results/model_inventory01.json'
        if sha256(previous) != config['previous_board_result_sha256']:
            raise RuntimeError('Prior full-file audit changed')
        prior = json.loads(previous.read_text())
        if len(prior['packages']) != 6 or len(prior['layouts']) != 2:
            raise RuntimeError('Prior full-file audit incomplete')
        result['reused_full_file_audit'] = dict(path=str(previous), sha256=sha256(previous),
            scope='Completed hashes only; prior import FAIL retained')
        sys.path[0:0] = [str(ROOT / p) for p in config['python_path']]
        result['python_path'] = sys.path[:len(config['python_path'])]
        for name in config['imports']:
            try:
                module = importlib.import_module(name)
                path = Path(module.__file__).resolve()
                result['imports'][name] = dict(file=str(path), sha256=sha256(path),
                    version=str(getattr(module, '__version__', 'unavailable')))
                print('IMPORT_PASS ' + name, flush=True)
            except Exception as exc:
                error = f'{type(exc).__name__}: {exc}'
                result['imports'][name] = dict(error=error)
                result['errors'].append(name + ': ' + error)
        result['runtime_imports_pass'] = not result['errors']
        for name in ('ffmpeg', 'ffprobe'):
            binary = shutil.which(name)
            result['decoders'][name] = dict(path=binary, sha256=sha256(binary) if binary else None)
        for name in ('cv2', 'av'):
            try:
                module = importlib.import_module(name)
                result['decoders'][name] = dict(file=module.__file__, version=module.__version__)
            except Exception as exc:
                result['decoders'][name] = dict(error=f'{type(exc).__name__}: {exc}')
        if 'error' not in result['decoders']['cv2']:
            from sys_video_input import decode_raw_video, render_prompt
            import hashlib
            decode_start = time.perf_counter()
            frames, evidence = decode_raw_video(here / 'dev-0001.mp4', config['video_sha256'])
            evidence.update(actual_decode_location='KV260_PS', decode_s=time.perf_counter()-decode_start,
                rgb_sha256=hashlib.sha256(frames.tobytes()).hexdigest(), rgb_dtype=str(frames.dtype))
            prompt = render_prompt(config['question'], evidence['actual_frame_times_s'])
            evidence['prompt_sha256'] = hashlib.sha256(prompt.encode()).hexdigest()
            evidence['visual_placeholders'] = prompt.count('<|image_pad|>')
            result['raw_video_decode'] = evidence
            result['raw_video_decode_pass'] = True
        else:
            result['errors'].append('Frozen raw-video adapter requires working cv2 decoder')
            result['raw_video_decode_pass'] = False
        result['python'] = sys.executable
        result['platform'] = platform.platform()
        result['status'] = 'PASS' if not result['errors'] else 'FAIL'
    except Exception as exc:
        result['errors'].append(f'{type(exc).__name__}: {exc}')
    finally:
        os.close(fd)
        result['elapsed_s'] = time.perf_counter() - start
        write_json(args.result, result)
        print('OP00_IMPORT_JSON_BEGIN', flush=True)
        print(json.dumps(result, allow_nan=False), flush=True)
        print('OP00_IMPORT_JSON_END', flush=True)
    return 0 if result['status'] == 'PASS' else 1


if __name__ == '__main__':
    raise SystemExit(main())
