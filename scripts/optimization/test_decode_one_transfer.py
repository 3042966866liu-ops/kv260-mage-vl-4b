import hashlib
import io
from pathlib import Path
import tarfile
import tempfile
import unittest
from receive_decode_one_package import unpack


class ExtractTests(unittest.TestCase):
    def test_exact_and_hash_rejection(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d); archive = root/'p.tar'
            with tarfile.open(archive, 'w') as t:
                item=tarfile.TarInfo('overlay/a.bit'); item.size=3
                t.addfile(item, io.BytesIO(b'abc'))
            rows=[dict(path='overlay/a.bit', bytes=3, sha256=hashlib.sha256(b'abc').hexdigest())]
            unpack(archive, root/'out', rows)
            self.assertEqual((root/'out/overlay/a.bit').read_bytes(), b'abc')
            rows[0]['sha256']='0'*64
            with self.assertRaisesRegex(ValueError, 'hash mismatch'): unpack(archive, root/'bad', rows)

    def test_traversal_and_symlink_rejected(self):
        for name, symbolic in (('../escape',False), ('file',True)):
            with tempfile.TemporaryDirectory() as d:
                root=Path(d); archive=root/'p.tar'
                with tarfile.open(archive, 'w') as t:
                    item=tarfile.TarInfo(name)
                    if symbolic: item.type=tarfile.SYMTYPE; item.linkname='../outside'
                    t.addfile(item)
                rows=[dict(path=name,bytes=0,sha256=hashlib.sha256(b'').hexdigest())]
                with self.assertRaises(ValueError): unpack(archive, root/'out', rows)


if __name__=='__main__': unittest.main()
