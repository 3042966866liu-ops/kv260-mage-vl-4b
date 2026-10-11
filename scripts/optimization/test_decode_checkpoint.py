from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
import numpy as np
from decode_checkpoint import save_checkpoint,load_checkpoint
from measurement import sha256


class CheckpointTests(unittest.TestCase):
    def test_exact_fresh_replay_and_tamper(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp)/'checkpoint'
            cache=SimpleNamespace(keys=[np.arange(12,dtype=np.float32).reshape(3,2,2)],
                                  values=[np.ones((3,2,2),np.float32)])
            identity={'model':'fixture','video':'fixed'}
            save_checkpoint(root,cache,2,identity);digest=sha256(root/'manifest.json')
            factory=lambda k,v:SimpleNamespace(keys=k,values=v)
            token,restored=load_checkpoint(root,digest,identity,factory)
            self.assertEqual(token,2)
            np.testing.assert_array_equal(restored.keys[0],cache.keys[0])
            restored.keys[0][:]=0
            _,fresh=load_checkpoint(root,digest,identity,factory)
            np.testing.assert_array_equal(fresh.keys[0],cache.keys[0])
            with self.assertRaises(ValueError):load_checkpoint(root,digest,{},factory)
            with self.assertRaises(FileExistsError):save_checkpoint(root,cache,2,identity)
            path=root/'layer00_key.npy';data=bytearray(path.read_bytes());data[-1]^=1;path.write_bytes(data)
            with self.assertRaisesRegex(ValueError,'hash/size'):load_checkpoint(root,digest,identity,factory)


if __name__=='__main__':unittest.main()
