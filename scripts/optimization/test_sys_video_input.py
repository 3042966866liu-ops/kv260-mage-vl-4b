import unittest
from sys_video_input import nearest_indices, render_prompt

class InputTests(unittest.TestCase):
    def test_nearest_real_times(self):
        self.assertEqual(nearest_indices([i/12 for i in range(48)]), [6,18,30,42])
    def test_missing_or_invented_pts_rejected(self):
        for data in ([0]*48, [0,1,2,float('nan')], [0,1,2,1], [0,1,2,3]):
            with self.assertRaises(ValueError):
                nearest_indices(data)
    def test_prompt_has_actual_four_times_and_784_positions(self):
        text = render_prompt('Which direction does the object move?', [0.5,1.5,2.5,3.5])
        self.assertEqual(text.count('<|image_pad|>'), 784)
        self.assertIn('<0.500 seconds>', text)
        self.assertIn('<3.500 seconds>', text)
        self.assertNotIn('dev-', text)
    def test_prompt_cannot_hide_frame_order(self):
        with self.assertRaises(ValueError):
            render_prompt('Q', [0.5,2.5,1.5,3.5])
