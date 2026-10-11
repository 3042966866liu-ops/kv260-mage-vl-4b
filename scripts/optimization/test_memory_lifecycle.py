import unittest
from memory_lifecycle import release_vision

class Runtime:
    def close(self): pass

class Broken:
    def close(self): raise RuntimeError('mapping busy')

class Tests(unittest.TestCase):
    def test_sole_reference(self):
        holder=[Runtime()]
        result=release_vision(holder,snapshot=lambda:{})
        self.assertTrue(result['object_released']);self.assertEqual(holder,[])
        self.assertFalse(result['trim']['called'])

    def test_external_reference_not_reported_released(self):
        runtime=Runtime();holder=[runtime]
        result=release_vision(holder,snapshot=lambda:{})
        self.assertFalse(result['object_released'])

    def test_close_error_preserves_reference(self):
        holder=[Broken()]
        with self.assertRaisesRegex(RuntimeError,'mapping busy'):
            release_vision(holder,snapshot=lambda:{})
        self.assertEqual(len(holder),1)

    def test_trim_explicit_only(self):
        calls=[]
        result=release_vision([Runtime()],snapshot=lambda:{},trim=True,
            trimmer=lambda:calls.append(1) or {'called':True})
        self.assertEqual(calls,[1]);self.assertTrue(result['trim']['called'])

if __name__=='__main__':unittest.main()
