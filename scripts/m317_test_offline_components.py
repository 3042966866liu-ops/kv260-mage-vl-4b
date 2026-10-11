"""Small deterministic software contracts; synthetic inputs are explicitly tests."""
from __future__ import annotations

import os
os.environ.setdefault("OPENBLAS_NUM_THREADS", "1")
os.environ.setdefault("OMP_NUM_THREADS", "1")
import sys
sys.dont_write_bytecode = True
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import unittest
from dataclasses import replace
import numpy as np
from bact.feature_budget import propose_budgets, choose_proposal, measure_subset
from bact.exact_vision_cache import VisionIdentity, vision_key, ExactVisionCache


class FeatureTests(unittest.TestCase):
    def setUp(self):
        self.x = np.random.default_rng(316).normal(size=(20, 6)).astype(np.float32)
        self.ids = np.repeat(np.arange(4), 5)

    def test_full_budget_and_independent_measure(self):
        p = propose_budgets(self.x, self.ids, [4, 8, 20], 65)
        self.assertEqual(p[-1].indices, tuple(range(20)))
        self.assertEqual(p[-1].mean_feature_distance, 0)
        self.assertGreaterEqual(p[0].mean_feature_distance, p[1].mean_feature_distance)
        independent = measure_subset(self.x, self.ids, list(p[1].indices))
        self.assertAlmostEqual(independent["mean_feature_distance"], p[1].mean_feature_distance)

    def test_deterministic_and_covers_views(self):
        a = propose_budgets(self.x, self.ids, [4, 8], 65)
        self.assertEqual(a, propose_budgets(self.x, self.ids, [4, 8], 65))
        self.assertTrue(all(n >= 1 for _, n in a[1].per_view_counts))
        self.assertEqual(list(a[1].indices), sorted(a[1].indices))

    def test_actual_features_change_selection(self):
        a = propose_budgets(self.x, self.ids, [8], 65)
        changed = np.random.default_rng(991).normal(size=self.x.shape).astype(np.float32)
        b = propose_budgets(changed, self.ids, [8], 65)
        self.assertNotEqual(a[0].indices, b[0].indices)

    def test_boundary_and_threshold(self):
        x = np.random.default_rng(0).normal(size=(200, 4)).astype(np.float32)
        p = propose_budgets(x, np.zeros(200, dtype=int), [62, 63, 64, 94, 95, 96], 65)
        self.assertEqual([r.batches for r in p], [4, 4, 5, 5, 5, 6])
        self.assertEqual([r.legacy_logical_calls for r in p], [624, 624, 778, 778, 778, 932])
        self.assertEqual(choose_proposal(p, 1).batches, 4)
        with self.assertRaises(ValueError):
            choose_proposal(p, 0)
        with self.assertRaises(ValueError):
            choose_proposal(p, float("nan"))

    def test_bad_geometry(self):
        for budgets in ([3], [21], [4.1], [True], [4, 4], []):
            with self.assertRaises(ValueError):
                propose_budgets(self.x, self.ids, budgets, 65)
        with self.assertRaises(ValueError):
            propose_budgets(self.x, self.ids[:-1], [4], 65)
        with self.assertRaises(ValueError):
            propose_budgets(self.x, self.ids, [4], 1.1)

    def test_bad_features(self):
        for value in (np.nan, np.inf):
            x = self.x.copy()
            x[0, 0] = value
            with self.assertRaises(ValueError):
                propose_budgets(x, self.ids, [4], 65)
        with self.assertRaises(ValueError):
            propose_budgets(np.zeros_like(self.x), self.ids, [4], 65)
        with self.assertRaises(ValueError):
            measure_subset(self.x, self.ids, [0, 1])


class CacheTests(unittest.TestCase):
    def setUp(self):
        self.identity = VisionIdentity("a"*64, "b"*64, "c"*64, "d"*64)
        self.frames = np.arange(48, dtype=np.uint8).reshape(2, 2, 4, 3)
        self.positions = np.arange(6).reshape(2, 3)
        self.mask = np.ones((2, 2), dtype=np.uint8)
        self.feature = np.arange(16, dtype=np.float32).reshape(4, 4)
        self.cache = ExactVisionCache(128, max_entries=2)

    def key(self, identity=None, frames=None, positions=None, mask=None):
        return vision_key(identity or self.identity, self.frames if frames is None else frames,
                          positions=self.positions if positions is None else positions,
                          attention_mask=self.mask if mask is None else mask)

    def test_hit_and_mutation_isolation(self):
        key = self.key()
        original = self.feature.copy()
        self.assertIsNone(self.cache.get(key))
        self.assertTrue(self.cache.put(key, self.feature))
        self.feature[:] = 0
        found = self.cache.get(key)
        np.testing.assert_array_equal(found, original)
        found[:] = 1
        np.testing.assert_array_equal(self.cache.get(key), original)

    def test_all_identity_changes_miss(self):
        key = self.key()
        self.cache.put(key, self.feature)
        for field in ("model_sha256", "weights_sha256", "processor_sha256", "execution_policy_sha256"):
            changed = replace(self.identity, **{field: "e"*64})
            self.assertNotEqual(key, self.key(identity=changed))
            self.assertIsNone(self.cache.get(self.key(identity=changed)))

    def test_content_shape_dtype_order_positions_mask(self):
        key = self.key()
        altered = self.frames.copy()
        altered.flat[0] += 1
        cases = [self.key(frames=altered), self.key(frames=self.frames[::-1]),
                 self.key(frames=self.frames.reshape(4, 2, 2, 3)),
                 self.key(frames=self.frames.astype(np.float32)),
                 self.key(positions=self.positions + 1), self.key(mask=1 - self.mask)]
        self.assertTrue(all(k != key for k in cases))
        self.assertEqual(key, self.key(frames=self.frames.copy()))

    def test_lru_and_budget(self):
        self.cache.put("1"*64, self.feature)
        self.cache.put("2"*64, self.feature)
        self.cache.get("1"*64)
        self.cache.put("3"*64, self.feature)
        self.assertIsNone(self.cache.get("2"*64))
        self.assertEqual(self.cache.bytes_used, 128)
        self.assertFalse(self.cache.put("3"*64, np.zeros(100, dtype=np.float32)))
        self.assertIsNone(self.cache.get("3"*64))
        self.assertEqual(self.cache.bytes_used, 64)

    def test_bad_inputs(self):
        with self.assertRaises(ValueError):
            VisionIdentity("bad", "b"*64, "c"*64, "d"*64)
        with self.assertRaises(ValueError):
            self.cache.put("bad", self.feature)
        with self.assertRaises(ValueError):
            self.cache.put("1"*64, np.array([np.nan]))
        with self.assertRaises(ValueError):
            self.key(frames=np.array([np.nan]))
        with self.assertRaises(ValueError):
            ExactVisionCache(0)


if __name__ == "__main__":
    unittest.main()
