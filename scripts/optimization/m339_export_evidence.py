"""Bounded, read-only COM3 export of whitelisted evidence files."""
import base64
import hashlib
import io
import json
from pathlib import Path
import sys
import tarfile

sys.dont_write_bytecode = True


def main():
    mode, expected = sys.argv[1:]
    if hashlib.sha256(Path(__file__).read_bytes()).hexdigest() != expected:
        raise RuntimeError('Exporter source hash mismatch')
    if mode not in ('preflight', 'results'): raise ValueError('Unknown mode')
    root = Path('/home/ubuntu/m339_prefill_profile_04') / mode / 'baseline'
    names = ('result.json', 'environment.json') if mode == 'preflight' else (
        'result.json', 'environment.json', 'm277_fixed_video.json', 'prefill_trace.json', 'video_forward.log')
    rows, stream = [], io.BytesIO()
    with tarfile.open(fileobj=stream, mode='w:gz') as archive:
        for name in names:
            path = root / name
            if not path.is_file(): continue
            payload = path.read_bytes()
            if len(payload) > 20 << 20: raise RuntimeError('Evidence bound exceeded')
            rows.append(dict(path=name, bytes=len(payload), sha256=hashlib.sha256(payload).hexdigest()))
            item = tarfile.TarInfo(name)
            item.size = len(payload)
            archive.addfile(item, io.BytesIO(payload))
    if 'result.json' not in {row['path'] for row in rows}: raise RuntimeError('Result absent')
    payload = stream.getvalue()
    if len(payload) > 4 << 20: raise RuntimeError('Archive export bound exceeded')
    print('M339_EXPORT_META='+json.dumps(dict(mode=mode, bytes=len(payload),
          sha256=hashlib.sha256(payload).hexdigest(), files=rows)), flush=True)
    encoded = base64.b64encode(payload).decode()
    for i in range(0, len(encoded), 2400): print('M339_EXPORT_DATA='+encoded[i:i+2400], flush=True)
    print('M339_EXPORT_COMPLETE', flush=True)


if __name__ == '__main__': main()
