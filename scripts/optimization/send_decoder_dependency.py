import json
from pathlib import Path
import socket
import struct
from decoder_dependency import NAME,SHA,SIZE,MAGIC,exact
from measurement import sha256

path=Path(__file__).resolve().parents[2]/'deployment/mage_vl4b/optimization_v1/dependencies'/NAME
if path.stat().st_size!=SIZE or sha256(path)!=SHA:
    raise RuntimeError('Pinned wheel changed')
payload=json.dumps(dict(name=NAME,bytes=SIZE,sha256=SHA)).encode()
with socket.create_connection(('192.168.0.2',8769),timeout=10) as sock:
    sock.settimeout(120)
    sock.sendall(MAGIC+struct.pack('!I',len(payload))+payload)
    with path.open('rb') as stream:
        for data in iter(lambda:stream.read(1024*1024),b''):sock.sendall(data)
    expected=b'PINNED_WHEEL_RECEIVED\n'
    if exact(sock,len(expected))!=expected:raise RuntimeError('Receiver rejected wheel')
print('OP00_PINNED_DECODER_TRANSFER_PASS (installation and decode pending)')
