"""Read-only fixed WSL identity probe; no model load, download or board access."""
from importlib import metadata
import json
from pathlib import Path
import sys
import time
sys.dont_write_bytecode = True
from measurement import sha256, write_json

ROOT = Path(__file__).resolve().parents[2]
BASE = ROOT / 'deployment/mage_vl4b/optimization_v1'
config = json.loads((BASE / 'contracts/config.json').read_text())
checkpoint = Path(config['checkpoint'])
manifest_path = checkpoint / 'CHECKPOINT_MANIFEST.json'
manifest = json.loads(manifest_path.read_text())
blob = checkpoint / manifest['blob']['path']
blob.resolve().relative_to(checkpoint.resolve())
print('OP00_WSL_VERIFY_CHECKPOINT_BEGIN', flush=True)
start = time.monotonic()
model_files = []
for name in ('config.json', 'tokenizer_config.json', 'tokenizer.json', 'model.safetensors.index.json'):
    p = Path(config['model']) / name
    model_files.append({'path': str(p), 'exists': p.is_file(),
                        'sha256': sha256(p) if p.is_file() else None,
                        'bytes': p.stat().st_size if p.is_file() else None})
observed = sha256(blob)
versions = {}
for name in ('torch', 'transformers', 'numpy', 'Pillow', 'safetensors', 'av'):
    try:
        versions[name] = metadata.version(name)
    except metadata.PackageNotFoundError:
        versions[name] = None
passed = (sha256(manifest_path) == config['checkpoint_manifest_sha256']
          and observed == config['checkpoint_blob_sha256'] == manifest['blob']['sha256']
          and blob.stat().st_size == manifest['blob']['bytes']
          and all(x['exists'] for x in model_files))
result = {'status': 'PASS' if passed else 'FAIL', 'scope': 'WSL_READONLY_IDENTITY',
          'python': sys.executable, 'model_files': model_files,
          'checkpoint_manifest_sha256': sha256(manifest_path),
          'checkpoint_blob_path': str(blob), 'checkpoint_blob_sha256': observed,
          'checkpoint_blob_bytes': blob.stat().st_size, 'packages': versions,
          'elapsed_s': time.monotonic() - start, 'board_accessed': False}
out = BASE / 'baselines/OP00_WSL_IDENTITY.json'
if out.exists():
    raise RuntimeError('Identity result exists; use a new versioned attempt, do not overwrite')
write_json(out, result)
print(json.dumps(result, allow_nan=False), flush=True)
raise SystemExit(0 if passed else 1)
