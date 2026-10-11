import unittest
from full_file_scan import window,unique_bytes

class FullScanTests(unittest.TestCase):
    def test_window_and_reject_offset(self):
        layout={'modules':[{'module':'q','tiles':[dict(tile_index=0,shard_offsets=[16]*4,record_bytes_per_shard=32)]}]}
        chain={'descriptors':[dict(module='q',tile_index=0,offset_words=1)]}
        self.assertEqual(window(layout,chain),(16,48))
        chain['descriptors'][0]['offset_words']=0
        with self.assertRaises(RuntimeError):window(layout,chain)
    def test_unique_bytes_overlap_disjoint_files(self):
        rows=[dict(path='a',offset=0,bytes=20),dict(path='a',offset=10,bytes=20),
              dict(path='a',offset=100,bytes=10),dict(path='b',offset=0,bytes=20)]
        self.assertEqual(unique_bytes(rows),60)

if __name__=='__main__':unittest.main()
