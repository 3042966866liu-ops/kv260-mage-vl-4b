import unittest
import numpy as np
from m120_group_reference import group_reference


class GroupReferenceTests(unittest.TestCase):
    def test_extremes_tail_zero_and_tiny_scales(self):
        rng=np.random.default_rng(20260924)
        for tokens,groups,rows in ((1,1,1),(30,3,7),(32,5,32)):
            a=rng.integers(-128,128,(tokens,groups,64),dtype=np.int16)
            w=rng.integers(-8,9,(groups,rows,64),dtype=np.int16)
            a[0]=127;w[0,0]=-8
            sa=np.full((tokens,groups),np.float16(0.003))
            sw=np.full((groups,rows),np.float16(0.007))
            sa[-1,-1]=np.nextafter(np.float16(0),np.float16(1))
            baseline=group_reference(a,sa,w,sw)
            faster=group_reference(a,sa,w,sw,dot_mode='fp32_exact')
            np.testing.assert_array_equal(baseline.view('u2'),faster.view('u2'))
            np.testing.assert_array_equal(group_reference(np.zeros_like(a),sa,w,sw),0)

    def test_invalid_and_nonfinite_rejected(self):
        a=np.ones((1,1,64),np.int8);w=np.ones((1,1,64),np.int8);s=np.ones((1,1),np.float16)
        with self.assertRaises(ValueError):group_reference(a,s,w*9,s)
        with self.assertRaises(ValueError):group_reference(a,s.astype(np.float32),w,s)
        with self.assertRaises(ValueError):group_reference(a,s*np.float16(np.inf),w,s)

    def test_overflow_preserved_for_retry(self):
        a=np.full((1,1,64),127,np.int8);w=np.full((1,1,64),8,np.int8)
        s=np.full((1,1),2,np.float16)
        self.assertTrue(np.isinf(group_reference(a,s,w,s)).all())


if __name__=='__main__':unittest.main()
