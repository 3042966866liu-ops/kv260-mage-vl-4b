"""Prepare/send a pinned archive to the authorized board peer; never use SSH."""
import argparse
import json
from pathlib import Path
import shutil
import socket
import tarfile
from measurement import sha256, write_json
from receive_decode_one_package import MAGIC, exact

ROOT = Path(__file__).resolve().parents[2]
BASE = ROOT / 'deployment/mage_vl4b/optimization_v1'
PACKAGE = BASE / 'candidates/OP01-decode-one-minimal-board-01'
OUT = BASE / 'candidates/OP01-decode-one-transfer-01'
EXPECTED = '1fb069ab95552b1c8f20fc8f4129ed10544c1e3e91c5869d7c41472466346442'


def main():
    global PACKAGE, OUT, EXPECTED
    parser = argparse.ArgumentParser()
    parser.add_argument('action', choices=('prepare', 'send'))
    modes = parser.add_mutually_exclusive_group()
    modes.add_argument('--real-chain', action='store_true')
    modes.add_argument('--layer', action='store_true')
    modes.add_argument('--ab', action='store_true')
    modes.add_argument('--sequence', action='store_true')
    args = parser.parse_args()
    if args.real_chain:
        PACKAGE = BASE / 'candidates/OP01-decode-one-real-chain-01'
        OUT = BASE / 'candidates/OP01-decode-one-real-transfer-01'
        EXPECTED = 'fa0254f5050f251ed72cb6f417bc0860e6cf1e9eed8b64bde3f32519744ac525'
    if args.layer:
        PACKAGE = BASE / 'candidates/OP01-decode-one-layer-01'
        OUT = BASE / 'candidates/OP01-decode-one-layer-transfer-01'
        EXPECTED = '4e7226a240b8daca0c29b529910467e30f13a378bbe08a471b61d67ceaeeb5a3'
    if args.ab:
        PACKAGE = BASE / 'candidates/OP01-decode-one-ab-01'
        OUT = BASE / 'candidates/OP01-decode-one-ab-transfer-01'
        EXPECTED = '4468af81c47d58352153ffccf5158192c4eb6e8012b0202cf07930839e3edbff'
    if args.sequence:
        PACKAGE = BASE / 'candidates/OP01-decode-one-sequence-01'
        OUT = BASE / 'candidates/OP01-decode-one-sequence-transfer-01'
        EXPECTED = '21d41a9589bef5bae080ff93ff78f57658766013c076e387bdbda90a1a03d6e0'
    if args.action == 'prepare':
        manifest = PACKAGE / 'PACKAGE_MANIFEST.json'
        if sha256(manifest) != EXPECTED: raise RuntimeError('Wrong candidate manifest')
        rows = json.loads(manifest.read_text())['files']
        rows = rows + [dict(path='PACKAGE_MANIFEST.json', bytes=manifest.stat().st_size, sha256=EXPECTED)]
        expected_paths = {r['path'] for r in rows}
        if {p.relative_to(PACKAGE).as_posix() for p in PACKAGE.rglob('*') if p.is_file()} != expected_paths:
            raise RuntimeError('Candidate whitelist drift')
        for row in rows:
            path = PACKAGE / row['path']
            if path.stat().st_size != row['bytes'] or sha256(path) != row['sha256']:
                raise RuntimeError('Candidate drift: ' + row['path'])
        OUT.mkdir(exist_ok=False)
        archive = OUT / 'package.tar'
        with tarfile.open(archive, 'w:') as tar:
            for row in sorted(rows, key=lambda x: x['path']):
                tar.add(PACKAGE / row['path'], arcname=row['path'], recursive=False)
        write_json(OUT / 'TRANSFER_CONTRACT.json', dict(package_manifest_sha256=EXPECTED,
            archive_bytes=archive.stat().st_size, archive_sha256=sha256(archive), members=rows))
        receiver = Path(__file__).with_name('receive_decode_one_package.py').read_text()
        if args.real_chain or args.layer or args.ab or args.sequence:
            target = 'OP01-decode-one-layer-01' if args.layer else 'OP01-decode-one-real-chain-01'
            stem = 'decode_one_layer' if args.layer else 'decode_one_real'
            if args.ab:
                target, stem = 'OP01-decode-one-ab-01', 'decode_one_ab'
            if args.sequence:
                target, stem = 'OP01-decode-one-sequence-01', 'decode_one_sequence'
            for old, new, count in (
                ('OP01-decode-one-minimal-board-01', target, 2),
                ('1fb069ab95552b1c8f20fc8f4129ed10544c1e3e91c5869d7c41472466346442', EXPECTED, 1),
                ('decode_one_package_transfer01.json', stem+'_transfer01.json', 1),
                ('decode_one_package01.tar', stem+'_package01.tar', 1)):
                if receiver.count(old) != count: raise RuntimeError('Receiver derivation drift')
                receiver = receiver.replace(old, new)
        (OUT / 'receive_decode_one_package.py').write_text(receiver, encoding='utf-8', newline='\n')
        print(json.dumps(dict(contract_sha256=sha256(OUT/'TRANSFER_CONTRACT.json'),
                              receiver_sha256=sha256(OUT/'receive_decode_one_package.py'), archive_bytes=archive.stat().st_size)))
        return
    contract = json.loads((OUT / 'TRANSFER_CONTRACT.json').read_text())
    archive = OUT / 'package.tar'
    if contract['package_manifest_sha256'] != EXPECTED or archive.stat().st_size != contract['archive_bytes'] or sha256(archive) != contract['archive_sha256']:
        raise RuntimeError('Pinned transfer drift')
    with socket.create_connection(('192.168.0.2',8769), timeout=10) as sock:
        sock.settimeout(120)
        sock.sendall(MAGIC)
        with archive.open('rb') as f:
            for block in iter(lambda: f.read(1024*1024), b''): sock.sendall(block)
        expected = b'PINNED_PACKAGE_RECEIVED\n'
        if exact(sock, len(expected)) != expected: raise RuntimeError('Receiver rejected archive')
    print('DECODE_ONE_PINNED_PACKAGE_SENT (board cleanup/result still required)')


if __name__ == '__main__': main()
