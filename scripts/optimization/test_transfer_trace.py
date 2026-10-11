import ast
from pathlib import Path
import tempfile
import unittest
import numpy as np
from decode_trace import DecodeTrace
from transfer_trace import instrument

ROOT=Path(__file__).resolve().parents[2]
SOURCE=ROOT/'deployment/mage_vl4b/m175_m120_fixed_text_candidate/runtime/board_runtime.py'


class Buffer:
    def __init__(self,size):self.array=np.zeros(size,np.uint8);self.syncs=0
    def __setitem__(self,index,value):self.array[index]=value
    def sync_to_device(self):self.syncs+=1


class TransferTests(unittest.TestCase):
    def setUp(self):
        text=SOURCE.read_text();tree=ast.parse(text)
        node=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='copy_window_to_buffer')
        self.source=ast.get_source_segment(text,node)
        ns={'np':np,'Path':Path};exec(self.source,ns);self.original=ns[node.name]

    def test_real_source_bytes_sync_and_short_read(self):
        with tempfile.TemporaryDirectory() as temp:
            path=Path(temp)/'weights.bin';path.write_bytes(bytes(range(256))*16)
            a,b=Buffer(128),Buffer(128);trace=DecodeTrace()
            wrapped=instrument(self.original,trace,self.source)
            self.original(path,19,128,a);wrapped(path,19,128,b)
            np.testing.assert_array_equal(a.array,b.array)
            self.assertEqual((a.syncs,b.syncs),(1,1))
            self.assertEqual([x['name'] for x in trace.report()['events']],
                             ['weight_file_read','weight_cma_copy','weight_cache_sync'])
            for call in (self.original,wrapped):
                short=Buffer(128)
                with self.assertRaisesRegex(RuntimeError,'short staged'):call(path,4096,128,short)
                self.assertEqual(short.syncs,0)

    def test_unreviewed_source_rejected(self):
        with self.assertRaisesRegex(RuntimeError,'Unreviewed'):
            instrument(self.original,DecodeTrace(),self.source.replace('16 << 20','8 << 20'))


if __name__=='__main__':unittest.main()
