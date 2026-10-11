import base64
import copy
import hashlib
import json
import unittest
from m441_transfer_collection import decode
class Collection(unittest.TestCase):
    def setUp(self):
        self.rows=[dict(path='PACKAGE_MANIFEST.json',bytes=1,sha256='c'*64)]
        self.r=dict(status='PASS_M441_ARTIFACT_TRANSFER_ONLY',bootstrap_manifest_sha256='a'*64,transport_manifest_sha256='b'*64,package_manifest_sha256='c'*64,
            board_gate_executed=False,overlay_loaded=False,fpga_transactions=0,errors=[],temporary_address_restored=True,files=self.rows,
            addresses_before=[dict(addr_info=[dict(family='inet',local='10.0.0.2',prefixlen=24)])],
            addresses_after=[dict(addr_info=[dict(family='inet',local='10.0.0.2',prefixlen=24)])],default_routes_before=[],default_routes_after=[],elapsed_s=1)
    def export(self,r):
        raw=json.dumps(r).encode();parts=[raw[i:i+200] for i in range(0,len(raw),200)]
        return 'M441_TRANSFER_SHA256='+hashlib.sha256(raw).hexdigest()+'\n'+''.join('M441_TRANSFER_CHUNK='+str(i)+'/'+str(len(parts))+':'+base64.b64encode(p).decode()+'\n' for i,p in enumerate(parts))
    def read(self,text):return decode(text,'a'*64,'b'*64,'c'*64,self.rows)
    def test_original_pass_and_failure(self):
        self.assertEqual(self.read(self.export(self.r))[2],self.r)
        fail=dict(self.r,status='FAIL_M441_ARTIFACT_TRANSFER',errors=['timeout'],files=[],temporary_address_restored=False)
        self.assertEqual(self.read(self.export(fail))[2],fail)
    def test_corruption_scope_and_network_rejected(self):
        text=self.export(self.r)
        for bad in [text.replace('CHUNK=1/','CHUNK=0/'),text+text,text.replace('SHA256=','SHA256=f'),text[:text.rfind('M441_TRANSFER_CHUNK=')]]:
            with self.assertRaises((ValueError,KeyError)):self.read(bad)
        for key,value in [('overlay_loaded',True),('board_gate_executed',True),('fpga_transactions',1),('bootstrap_manifest_sha256','x'*64),('temporary_address_restored',False),('files',[]),('elapsed_s',631),('default_routes_after',[dict(dst='default',gateway='10.0.0.1')]),('addresses_after',[])]:
            bad=copy.deepcopy(self.r);bad[key]=value
            with self.subTest(key=key),self.assertRaises(ValueError):self.read(self.export(bad))
if __name__=='__main__':unittest.main()
