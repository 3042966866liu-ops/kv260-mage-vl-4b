"""Exact manifest SHA/full whitelist for modern and pinned legacy packages."""
import hashlib
import json
from pathlib import Path

def sha(path):
    h=hashlib.sha256()
    with path.open('rb') as stream:
        for part in iter(lambda:stream.read(4<<20),b''):h.update(part)
    return h.hexdigest()

def verify_frozen_package(root,expected_sha,*,legacy_manifest=False):
    root=Path(root).resolve();manifest=root/'PACKAGE_MANIFEST.json'
    if sha(manifest)!=expected_sha:raise RuntimeError('Exact manifest SHA differs')
    data=json.loads(manifest.read_text(encoding='utf-8'));items=data['files'];paths=[x['path'] for x in items]
    if not paths or len(paths)!=len(set(paths)):raise RuntimeError('Empty/duplicate whitelist')
    actual={p.relative_to(root).as_posix() for p in root.rglob('*') if p.is_file() and p!=manifest}
    if set(paths)!=actual:raise RuntimeError('Complete whitelist differs')
    total=0
    for row in items:
        p=(root/row['path']).resolve();p.relative_to(root)
        if type(row['bytes']) is not int or row['bytes']<0 or p.stat().st_size!=row['bytes'] or sha(p)!=row['sha256']:raise RuntimeError('Payload identity differs: '+row['path'])
        total+=row['bytes']
    if not legacy_manifest and (data['file_count']!=len(paths) or data['total_bytes']!=total):raise RuntimeError('Count/bytes differs')
    return dict(manifest_sha256=expected_sha,computed_file_count=len(paths),computed_total_bytes=total,legacy_manifest=legacy_manifest,full_whitelist_verified=True)
