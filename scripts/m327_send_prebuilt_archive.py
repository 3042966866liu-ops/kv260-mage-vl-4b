#!/usr/bin/env python3
"""Send one hash-locked prebuilt archive to one KV260 peer over temporary Ethernet."""

import argparse
import hashlib
import json
from pathlib import Path
import socket


HOST = '192.168.0.10'
BOARD = '192.168.0.2'
PORT = 49328


def sha256(path):
    h = hashlib.sha256()
    with path.open('rb') as f:
        for block in iter(lambda: f.read(4 << 20), b''):
            h.update(block)
    return h.hexdigest()


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--archive', type=Path, required=True)
    p.add_argument('--expected-sha256', required=True)
    p.add_argument('--expected-bytes', type=int, required=True)
    args = p.parse_args()
    archive = args.archive.resolve()
    if archive.stat().st_size != args.expected_bytes or sha256(archive) != args.expected_sha256:
        raise RuntimeError('local prebuilt archive identity mismatch')
    with socket.socket() as server:
        server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        server.bind((HOST, PORT))
        server.listen(1)
        server.settimeout(600)
        print(f'M327_PREBUILT_SENDER_READY {HOST}:{PORT}', flush=True)
        conn, address = server.accept()
        with conn:
            if address[0] != BOARD:
                raise RuntimeError(f'unexpected peer: {address[0]}')
            conn.settimeout(600)
            with archive.open('rb') as inp:
                for block in iter(lambda: inp.read(4 << 20), b''):
                    conn.sendall(block)
    print(json.dumps({'status': 'SENT_NOT_BOARD_VERIFIED', 'archive': str(archive),
                      'bytes': args.expected_bytes, 'sha256': args.expected_sha256}), flush=True)


if __name__ == '__main__':
    main()
