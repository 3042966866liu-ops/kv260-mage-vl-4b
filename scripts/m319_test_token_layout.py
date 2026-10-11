"""Local unit gates; no torch, board, or semantic claims."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import unittest
import numpy as np
from bact.token_layout import select_layout


class LayoutTests(unittest.TestCase):
    def setUp(self):
        self.ids = np.array([[10, 99, 99, 11, 99, 99, 12]])
        self.mask = np.ones_like(self.ids)

    def layout(self, keep, **kw):
        return select_layout(self.ids, self.mask, keep, image_token_id=99,
                             frame_counts=kw.get('counts', [2, 2]))

    def test_identity(self):
        x = self.layout([0, 1, 2, 3])
        np.testing.assert_array_equal(x.input_ids, self.ids)
        np.testing.assert_array_equal(x.sequence_indices, np.arange(7))
        np.testing.assert_array_equal(x.position_ids[0], x.cache_position)

    def test_text_and_special_preserved(self):
        x = self.layout([1, 2])
        np.testing.assert_array_equal(x.sequence_indices, [0, 2, 3, 4, 6])
        np.testing.assert_array_equal(x.input_ids, [[10, 99, 11, 99, 12]])
        np.testing.assert_array_equal(self.ids, [[10, 99, 99, 11, 99, 99, 12]])

    def test_invalid(self):
        for bad in ([0, 0, 2], [2, 0], [-1, 2], [0, 4], [0, 1], [], [0.0, 2.0]):
            with self.subTest(bad=bad), self.assertRaises(ValueError):
                self.layout(bad)

    def test_wrong_counts(self):
        with self.assertRaises(ValueError):
            self.layout([0, 2], counts=[2, 3])

    def test_padding(self):
        self.mask[0, 0] = 0
        with self.assertRaises(ValueError):
            self.layout([0, 2])


if __name__ == '__main__':
    unittest.main()
