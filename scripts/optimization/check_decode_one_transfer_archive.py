"""Local replay of the exact archive extraction; no network or board access."""
import json
from pathlib import Path
import tempfile
from measurement import sha256, write_json
from receive_decode_one_package import unpack

root = Path(__file__).resolve().parents[2]
base = root / 'deployment/mage_vl4b/optimization_v1'
source = base / 'candidates/OP01-decode-one-transfer-01'
contract_path = source / 'TRANSFER_CONTRACT.json'
if sha256(contract_path) != 'f5e7865991c0763d5aca418428c10ff5b7ef2133470e840545c51ea0c65c7aa5':
    raise RuntimeError('Transfer contract changed')
contract = json.loads(contract_path.read_text())
archive = source / 'package.tar'
if sha256(archive) != contract['archive_sha256'] or archive.stat().st_size != contract['archive_bytes']:
    raise RuntimeError('Archive identity mismatch')
out = base / 'runs/OP01-decode-one-transfer-local-check/result.json'
if out.exists(): raise RuntimeError('Immutable local evidence exists')
with tempfile.TemporaryDirectory(prefix='decode_one_extract_', dir=root/'tmp') as temp:
    destination = Path(temp)/'package'
    unpack(archive, destination, contract['members'])
    observed = {p.relative_to(destination).as_posix() for p in destination.rglob('*') if p.is_file()}
    if observed != {x['path'] for x in contract['members']}:
        raise RuntimeError('Extracted whitelist mismatch')
    if sha256(destination/'PACKAGE_MANIFEST.json') != contract['package_manifest_sha256']:
        raise RuntimeError('Extracted package manifest mismatch')
    result = dict(status='PASS_LOCAL_ARCHIVE_EXTRACTION_ONLY', board_transferred=False,
                  board_deployed=False, archive_bytes=contract['archive_bytes'],
                  archive_sha256=contract['archive_sha256'], contract_sha256=sha256(contract_path),
                  package_manifest_sha256=contract['package_manifest_sha256'],
                  blocker='Await explicit user authorization for COM3 bootstrap receiver and contract upload after auto-review rejection')
    write_json(out, result)
print(json.dumps(result))
