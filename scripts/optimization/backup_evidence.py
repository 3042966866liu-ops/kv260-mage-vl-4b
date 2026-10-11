"""Immutable local evidence snapshots; never a simulator checkpoint or gate PASS."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
from datetime import datetime, timezone
import uuid

ROOT = Path(__file__).resolve().parents[2]
BASE = ROOT / 'deployment/mage_vl4b/optimization_v1'

def digest(path):
    h = hashlib.sha256()
    with path.open('rb') as f:
        for block in iter(lambda: f.read(1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()

def snapshot(reason):
    files = set()
    def add(p):
        p = p.resolve()
        p.relative_to(ROOT)
        if p.is_file() and not p.is_symlink():
            files.add(p)
    for name in ['CURRENT_STATE.md', 'docsMILESTONES.md',
                 'DEPLOYMENT_OPERATION_MISTAKES_REVIEW.md', 'AGENTS.md',
                 'deployment/mage_vl4b/BOARD_GATE_RESULT.json']:
        add(ROOT / name)
    for folder in ['reports', 'gates', 'baselines', 'contracts', 'runs']:
        for p in (BASE / folder).rglob('*'):
            if p.suffix.lower() in {'.md', '.json', '.log', '.rpt'}:
                add(p)
    for p in BASE.glob('*'):
        if p.suffix in {'.json', '.md'}:
            add(p)
    for folder in ['scripts/optimization', 'hls/mage_decode_op01_one']:
        for p in (ROOT / folder).rglob('*'):
            if p.suffix in {'.py', '.ps1', '.tcl', '.cpp', '.hpp', '.h', '.cmd', '.sh'}:
                add(p)
    # Exact local recursive source closure recorded by the dependency audits.
    for audit in (BASE / 'runs').glob('OP01-decode-one-*header/result.json'):
        value = json.loads(audit.read_text(encoding='utf-8-sig'))
        for entry in value.get('files', []):
            add(ROOT / entry['path'])
        for edge in value.get('edges', []):
            add(ROOT / edge['resolved'])
    add(ROOT / 'scripts/run_vitis_hls_2026_1.cmd')
    # Preserve logs and reports outside tmp; do not copy simulator executables/large TV.
    for folder in (ROOT / 'tmp').glob('op01_decode_one*'):
        for p in folder.rglob('*'):
            if p.suffix.lower() in {'.log', '.rpt', '.json', '.tcl'}:
                add(p)
    stamp = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S.%fZ')
    name = stamp + '-' + uuid.uuid4().hex[:8]
    parent = BASE / 'backups'
    parent.mkdir(exist_ok=True)
    partial = parent / (name + '.partial')
    if os.name == 'nt':
        partial = Path('\\\\?\\' + str(partial.resolve()))
    partial.mkdir()
    entries = []
    for src in sorted(files):
        rel = src.relative_to(ROOT)
        dst = partial / 'files' / rel
        dst.parent.mkdir(parents=True, exist_ok=True)
        before = digest(src)
        shutil.copyfile(src, dst)
        copied, after = digest(dst), digest(src)
        live = rel.parts[0] == 'tmp'
        if not live and not (before == copied == after):
            raise RuntimeError(f'Source changed during snapshot: {rel}; partial retained')
        entries.append(dict(path=rel.as_posix(), bytes=dst.stat().st_size,
                            sha256=copied, source_sha_before=before,
                            source_sha_after=after, live_log_snapshot=live,
                            stable_during_copy=(before == copied == after)))
    manifest = dict(schema=1, created_utc=stamp, reason=reason,
                    scope='local report/source/log snapshot, not full model or simulator checkpoint',
                    independent_disk_backup=False, file_count=len(entries),
                    total_bytes=sum(x['bytes'] for x in entries), files=entries)
    manifest_path = partial / 'MANIFEST.json'
    with manifest_path.open('x', encoding='utf-8') as f:
        json.dump(manifest, f, ensure_ascii=False, indent=2)
        f.flush()
        os.fsync(f.fileno())
    verify(partial)
    final = parent / name
    partial.rename(final)
    print(json.dumps(dict(status='BACKUP_VERIFIED', path=str(final),
                         files=len(entries), bytes=manifest['total_bytes']), ensure_ascii=False))

def verify(folder):
    folder = folder.resolve()
    if os.name == 'nt' and not str(folder).startswith('\\\\?\\'):
        folder = Path('\\\\?\\' + str(folder))
    manifest = json.loads((folder / 'MANIFEST.json').read_text(encoding='utf-8'))
    for entry in manifest['files']:
        p = (folder / 'files' / entry['path']).resolve()
        p.relative_to(folder / 'files')
        if p.stat().st_size != entry['bytes'] or digest(p) != entry['sha256']:
            raise RuntimeError(f'Backup verification failed: {p}')
    if len(manifest['files']) != manifest['file_count']:
        raise RuntimeError('Manifest count mismatch')
    return manifest

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--reason', default='evidence checkpoint')
    parser.add_argument('--verify', type=Path)
    args = parser.parse_args()
    if args.verify:
        m = verify(args.verify)
        print(f"BACKUP_REVERIFY_PASS files={m['file_count']}")
    else:
        snapshot(args.reason)
