"""Offline transfer framing/path/network-cleanup checks; no board connection."""
import copy
import hashlib
import json
from pathlib import Path
import socket
import struct
import tempfile
import threading
import time
import types
import unittest
from unittest.mock import patch
import m357_transfer as t

class TransferTest(unittest.TestCase):
    def test_actual_local_stream_complete_multiblock_and_empty_member(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);pkg=root/'package';pkg.mkdir()
            data=bytes(range(256))*8192+b'nonaligned-tail'
            (pkg/'data.bin').write_bytes(data);(pkg/'empty.bin').write_bytes(b'')
            entries=[dict(path=n,bytes=(pkg/n).stat().st_size,sha256=t.sha(pkg/n)) for n in ['data.bin','empty.bin']]
            manifest=dict(file_count=len(entries),total_bytes=sum(r['bytes'] for r in entries),files=entries)
            (pkg/'PACKAGE_MANIFEST.json').write_bytes(t.encoded(manifest));digest=t.sha(pkg/'PACKAGE_MANIFEST.json')
            rows=[dict(path='PACKAGE_MANIFEST.json',bytes=(pkg/'PACKAGE_MANIFEST.json').stat().st_size,sha256=digest)]+entries
            transport=dict(schema='m357-specific-peer-transfer-v1',package_manifest_sha256=digest,file_count=len(rows),total_bytes=sum(r['bytes'] for r in rows),files=rows)
            transport_path=root/'TRANSPORT.json';transport_path.write_bytes(t.encoded(transport))
            client,server=socket.socketpair();server.settimeout(5);errors=[];received=[]
            def read(count):
                raw=bytearray()
                while len(raw)<count:
                    block=server.recv(min(511,count-len(raw)))
                    if not block:raise EOFError('Local framing EOF')
                    raw.extend(block)
                return bytes(raw)
            def peer():
                try:
                    self.assertEqual(read(len(t.MAGIC)),t.MAGIC)
                    size=struct.unpack('!I',read(4))[0];self.assertEqual(read(size),transport_path.read_bytes())
                    for r in rows:
                        n=struct.unpack('!H',read(2))[0];name=read(n).decode('utf-8');size=struct.unpack('!Q',read(8))[0]
                        raw=read(size);self.assertEqual(name,r['path']);self.assertEqual(raw,(pkg/name).read_bytes());received.append(name)
                    self.assertEqual(read(2),b'\0\0')
                    response=t.encoded(dict(status='PASS',package_manifest_sha256=digest));server.sendall(struct.pack('!I',len(response))+response)
                except BaseException as exc:errors.append(exc)
                finally:server.close()
            thread=threading.Thread(target=peer);thread.start()
            with patch.object(t.socket,'create_connection',return_value=client):rc=t.send(pkg,digest,transport_path,root/'SENDER.json')
            thread.join(timeout=5);self.assertFalse(thread.is_alive());self.assertEqual(errors,[]);self.assertEqual(rc,0);self.assertEqual(received,[r['path'] for r in rows])
    def test_safe_paths_and_counts(self):
        row=dict(path='overlay/m120_m89x2_t32.bit',bytes=16,sha256='a'*64)
        spec=dict(file_count=1,total_bytes=16,files=[row]);self.assertEqual(t.valid_entries(spec),[row])
        for name in ['/escape','../escape','a/../../escape','a\\escape','C:/escape','a//b','a/./b','a/__pycache__/b.pyc','a.pyc']:
            bad=copy.deepcopy(spec);bad['files'][0]['path']=name
            with self.subTest(path=name),self.assertRaises(ValueError):t.valid_entries(bad)
        for field,value in [('bytes',-1),('bytes',129<<20),('sha256','a'*63),('sha256','z'*64)]:
            bad=copy.deepcopy(spec);bad['files'][0][field]=value
            with self.subTest(field=field,value=value),self.assertRaises(ValueError):t.valid_entries(bad)
        with self.assertRaises(ValueError):t.valid_entries(dict(spec,files=[row,row],file_count=2,total_bytes=32))
        with self.assertRaises(ValueError):t.valid_entries(dict(spec,total_bytes=17))
    def test_actual_short_reads_eof_and_deadline(self):
        class Short:
            def __init__(self,data):self.data=data
            def recv_into(self,view):
                n=min(2,len(view),len(self.data));view[:n]=self.data[:n];self.data=self.data[n:];return n
        self.assertEqual(t.exact(Short(b'abcdef'),6,time.monotonic()+1),b'abcdef')
        with self.assertRaises(EOFError):t.exact(Short(b'a'),2,time.monotonic()+1)
        with self.assertRaises(TimeoutError):t.exact(Short(b'a'),1,time.monotonic()-1)
        with self.assertRaises(ValueError):t.exact(Short(b''),(1<<20)+1,time.monotonic()+1)
    def test_cleanup_after_wrong_peer_never_imports(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);bootstrap=root/'bootstrap';bootstrap.mkdir()
            payload_manifest='a'*64
            transport=dict(schema='m357-specific-peer-transfer-v1',package_manifest_sha256=payload_manifest,file_count=1,total_bytes=1,files=[dict(path='PACKAGE_MANIFEST.json',bytes=1,sha256='b'*64)])
            raw=t.encoded(transport);(bootstrap/'TRANSPORT_MANIFEST.json').write_bytes(raw)
            bootstrap_manifest=dict(file_count=1,total_bytes=len(raw),files=[dict(path='TRANSPORT_MANIFEST.json',bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest())])
            (bootstrap/'PACKAGE_MANIFEST.json').write_bytes(t.encoded(bootstrap_manifest));digest=t.sha(bootstrap/'PACKAGE_MANIFEST.json')
            calls=[];added=[False]
            before=[dict(addr_info=[dict(family='inet',local='10.0.0.2',prefixlen=24)])]
            def ip_json(*args):
                if args[0]=='route':return []
                value=copy.deepcopy(before)
                if added[0]:value[0]['addr_info'].append(dict(family='inet',local=t.BOARD,prefixlen=24))
                return value
            def command(args,**kw):
                calls.append(args);added[0]=args[2]=='add';return types.SimpleNamespace(returncode=0)
            class Connection:
                def __enter__(self):return self
                def __exit__(self,*a):return False
                def settimeout(self,*a):pass
            class Listener(Connection):
                def bind(self,*a):pass
                def listen(self,*a):pass
                def accept(self):return Connection(),('203.0.113.1',1234)
            carrier=root/'carrier';carrier.write_text('1',encoding='utf-8')
            real_path=Path
            def mapped_path(value):return carrier if str(value)=='/sys/class/net/eth0/carrier' else real_path(value)
            with patch.object(t,'DESTINATION',root/'destination'),patch.object(t,'EVIDENCE',root/'evidence'),patch.object(t,'Path',mapped_path),patch.object(t,'ip_json',ip_json),patch.object(t.subprocess,'run',command),patch.object(t.os,'geteuid',return_value=0,create=True),patch.object(t.socket,'socket',return_value=Listener()),patch.object(t.shutil,'disk_usage',return_value=types.SimpleNamespace(free=1<<30)):
                rc=t.receive(bootstrap,digest)
            result=json.loads((root/'evidence/RESULT.json').read_text(encoding='utf-8'))
            self.assertEqual(rc,1);self.assertTrue(result['temporary_address_restored']);self.assertFalse(added[0]);self.assertEqual([r[2] for r in calls],['add','del']);self.assertFalse((root/'destination').exists());self.assertEqual(result['fpga_transactions'],0)

if __name__=='__main__':unittest.main()
