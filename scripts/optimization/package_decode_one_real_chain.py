"""Reuse immutable board-tested shell; replace only new host/fixture files."""
import ast
import json
from pathlib import Path
from measurement import sha256, write_json
from decode_one_real_chain import load_real_chain, FIXTURE_SHA

ROOT = Path(__file__).resolve().parents[2]
BASE = ROOT/'deployment/mage_vl4b/optimization_v1'
OLD = BASE/'candidates/OP01-decode-one-minimal-board-01'
OUT = BASE/'candidates/OP01-decode-one-real-chain-01'


def main():
    expected = '1fb069ab95552b1c8f20fc8f4129ed10544c1e3e91c5869d7c41472466346442'
    if sha256(OLD/'PACKAGE_MANIFEST.json') != expected: raise RuntimeError('Base package drift')
    payloads = {}
    for row in json.loads((OLD/'PACKAGE_MANIFEST.json').read_text())['files']:
        path = OLD/row['path']
        if sha256(path) != row['sha256']: raise RuntimeError('Base member drift')
        payloads[row['path']] = path.read_bytes()
    for name in ('decode_one_board_transaction.py', 'decode_one_minimal_board.py', 'decode_one_real_chain.py'):
        raw = Path(__file__).with_name(name).read_bytes().replace(b'\r\n', b'\n')
        ast.parse(raw, filename=name); payloads[name] = raw
    fixture = BASE/'runs/OP01-decode-one-real-fixture/real_gate_up.bin'
    parsed = load_real_chain(fixture)
    if len(set(parsed['weight_shards'])) != 4: raise RuntimeError('Real shards must differ')
    payloads['real_gate_up.bin'] = fixture.read_bytes()
    shell = payloads['run_decode_one_minimal_board.sh']
    if shell.count(b'--result "$2"') != 1: raise RuntimeError('Runner contract changed')
    payloads['run_decode_one_minimal_board.sh'] = shell.replace(b'--result "$2"', b'--result "$2" --real-chain')
    OUT.mkdir(exist_ok=False)
    rows = []
    for name, raw in payloads.items():
        path = OUT/name; path.parent.mkdir(parents=True, exist_ok=True); path.write_bytes(raw)
        rows.append(dict(path=name, bytes=len(raw), sha256=sha256(path)))
    write_json(OUT/'PACKAGE_MANIFEST.json', dict(schema_version=1, files=rows, file_count=len(rows),
        total_bytes=sum(r['bytes'] for r in rows), base_package_sha256=expected,
        fixture_sha256=FIXTURE_SHA, build_id='0x4F503131', formal_promotion_allowed=False,
        capacity_status='STOPPED_BY_USER_NOT_PASS'))
    print(json.dumps(dict(package=str(OUT), sha256=sha256(OUT/'PACKAGE_MANIFEST.json'),
        input_bytes=len(parsed['packet']), output_bytes=parsed['output_bytes'],
        shard_bytes=[len(x) for x in parsed['weight_shards']], config=hex(parsed['config']))))


if __name__ == '__main__': main()
