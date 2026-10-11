import json
from pathlib import Path
import unittest
import numpy as np
from video_contract_v2 import preprocess_raw_frames,render_raw_prompt

BASE=Path(__file__).resolve().parents[2]/'deployment/mage_vl4b/optimization_v1'

class VideoContractTests(unittest.TestCase):
    def test_exact_official_arrays(self):
        frames=np.load(BASE/'datasets/dev_bootstrap_v1/board_reference_v1/dev-0001_rgb.npy',allow_pickle=False)
        actual=preprocess_raw_frames(frames,[6,18,30,42])
        with np.load(BASE/'runs/OP01-official-input-audit-v1/official_input.npz',allow_pickle=False) as expected:
            for key in actual:
                self.assertTrue(np.array_equal(actual[key],expected[key]),key)

    def test_exact_official_prompt(self):
        sample=json.loads((BASE/'datasets/dev_bootstrap_v1/input_manifest.json').read_text())['samples'][0]
        expected=json.loads((BASE/'runs/OP01-official-input-audit-v1/prompt.json').read_text())['prompt']
        self.assertEqual(render_raw_prompt(sample['question'],[.5,1.5,2.5,3.5]),expected)

    def test_reject_reordered_or_missing_indices(self):
        frames=np.zeros((4,448,448,3),np.uint8)
        for indices in ([42,30,18,6],[6,18,30],[6,18,18,42],[6.0,18,30,42]):
            with self.assertRaises(ValueError):preprocess_raw_frames(frames,indices)

if __name__=='__main__':unittest.main()
