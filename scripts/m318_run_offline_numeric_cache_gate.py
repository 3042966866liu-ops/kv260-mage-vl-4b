"""Real historical packed-record dot cross-check and exact feature-cache gate.

Not Vitis CSim, not a new model forward, not a speed benchmark or board run.
"""
from __future__ import annotations

import os
os.environ.setdefault("OPENBLAS_NUM_THREADS", "1")
os.environ.setdefault("OMP_NUM_THREADS", "1")
import sys
sys.dont_write_bytecode = True
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import argparse
import hashlib
import json
import struct
import unittest
import numpy as np
from bact.exact_vision_cache import VisionIdentity, vision_key, ExactVisionCache
from m316_offline_deployment_audit import sha, write_result
from m317_test_offline_components import FeatureTests, CacheTests


def numeric_records(path: Path) -> dict:
    """Read original M128 real-record format, compare dot products two ways.

    Matmul INT32 vs elementwise product/reduce INT64 across every token/row/group.
    FP32 scaling follows M128 ordering, without changing the original HLS kernel.
    These descriptors represent sampled output rows, NOT full matrix/all-layer E2E.
    """
    blob = path.read_bytes()
    manifest_path = path.parents[1] / "PACKAGE_MANIFEST.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    entry = next(x for x in manifest["files"] if x["path"] == "reference/" + path.name)
    if len(blob) != entry["bytes"] or hashlib.sha256(blob).hexdigest() != entry["sha256"]:
        raise ValueError("M128 fixture does not match original package manifest")
    offset = 0

    def take(n):
        nonlocal offset
        part = blob[offset:offset+n]
        if len(part) != n:
            raise ValueError("truncated M128 fixture")
        offset += n
        return part

    def integers(n):
        return struct.unpack("<" + "I"*n, take(n*4))

    if take(8) != b"M128CSM1" or integers(4) != (7, 10, 32, 30):
        raise ValueError("unexpected M128 fixture header")
    results = []
    dot_count = 0
    for ordinal in range(7):
        chain, layer, family, count, groups, bits = integers(6)
        if chain != ordinal or not 1 <= count <= 10 or not 1 <= groups <= 152 or bits not in (2, 4):
            raise ValueError("invalid chain header")
        descriptors = []
        for _ in range(count):
            header = take(8)
            if tuple(header[:3]) != (bits, 1 + 4*bits, groups):
                raise ValueError("descriptor geometry mismatch")
            descriptors.append(np.frombuffer(take(4*groups*17*16), dtype=np.uint8).reshape(4, groups, 17, 16))
        activation = np.frombuffer(take(groups*32*5*16), dtype=np.uint8).reshape(groups, 32, 5, 16)
        a = activation[:, :, :4, :].copy().reshape(groups, 32, 64).view(np.int8).astype(np.int32)
        scales_a_bits = activation[:, :, 4, :2].copy().view("<u2").reshape(groups, 32)
        scales_a = scales_a_bits.view("<f2").astype(np.float32)
        if not np.isfinite(scales_a).all():
            raise ValueError("nonfinite activation scale")
        digest = hashlib.sha256()
        elements = 0
        for record in descriptors:
            for shard in range(4):
                acc = np.zeros((32, 8), dtype=np.float32)
                for group in range(groups):
                    raw = record[shard, group]
                    tags = raw[0].copy().view("<u2")
                    weight_scales = (tags & 0x7fff).view("<f2").astype(np.float32)
                    qmin = np.where(tags & 0x8000, -(1 << (bits-1)) + 1, -(1 << (bits-1)))
                    # Eight consecutive rows, each encoded in bits*8 bytes.
                    packed = raw[1:1+4*bits].reshape(8, bits*8)
                    lane = np.arange(64)
                    codes = ((packed[:, lane // (8//bits)] >> ((lane % (8//bits))*bits)) & ((1 << bits)-1)).astype(np.int32)
                    w = codes + qmin[:, None].astype(np.int32)
                    # Independent row/lane addressing, matching C++ weight_code.
                    # Check one group per descriptor/shard; dot checks cover ALL groups.
                    if group == 0:
                        decoded = np.empty((8, 64), dtype=np.int32)
                        for row in range(8):
                            tag = int.from_bytes(raw[0, 2*row:2*row+2].tobytes(), "little")
                            zero = -(1 << (bits-1)) + int(bool(tag & 0x8000))
                            for lane in range(64):
                                word_index = 1 + (row//2)*bits + (row%2)*(bits//2) + (lane//32 if bits == 4 else 0)
                                word = int.from_bytes(raw[word_index].tobytes(), "little")
                                shift = bits * (lane if bits == 2 else lane % 32)
                                decoded[row, lane] = zero + ((word >> shift) & ((1 << bits)-1))
                        if not np.array_equal(w, decoded):
                            raise ValueError("independent packed weight decode mismatch")
                    dots = a[group] @ w.T
                    independent = np.sum(a[group].astype(np.int64)[:, None, :] * w.astype(np.int64)[None, :, :], axis=2)
                    if not np.array_equal(dots.astype(np.int64), independent):
                        raise ValueError("integer dot mismatch")
                    if not np.isfinite(weight_scales).all():
                        raise ValueError("nonfinite weight scale")
                    dot_count += dots.size
                    term = (dots.astype(np.float32) * scales_a[group, :, None]) * weight_scales[None, :]
                    acc = (acc + term).astype(np.float32)
                if not np.isfinite(acc).all():
                    raise ValueError("nonfinite FP32 accumulator")
                half = acc.astype(np.float16)
                if not np.isfinite(half).all():
                    raise ValueError("nonfinite FP16 boundary")
                digest.update(half.tobytes())
                elements += half.size
        results.append({"chain": chain, "layer": layer, "family": family,
                        "bits": bits, "groups": groups, "descriptors": count,
                        "software_fp16_output_sha256": digest.hexdigest(),
                        "sampled_output_elements": elements})
    if offset != len(blob):
        raise ValueError("trailing fixture bytes")
    return {"fixture_sha256": hashlib.sha256(blob).hexdigest(),
            "original_package_manifest_sha256": sha(manifest_path),
            "fixture_original_manifest_verified": True,
            "independent_row_lane_decoder_checked": True,
            "fixture_bytes": len(blob), "integer_dot_comparisons": dot_count,
            "chains": results, "rtl_or_csim_run": False,
            "scope": "Two NumPy integer-dot implementations on historical real-record sampled rows; no new FPGA output comparison."}


def real_cache() -> dict:
    package = ROOT / "deployment/mage_vl4b/m181_m120_video_board_candidate"
    manifest = json.loads((package / "PACKAGE_MANIFEST.json").read_text(encoding="utf-8"))
    entries = {x["path"]: x for x in manifest["files"]}
    paths = ["fixtures/official_four_frame_processor.npz", "fixtures/official_vision_merged_bf16.npz"]
    for rel in paths:
        if sha(package / rel) != entries[rel]["sha256"]:
            raise ValueError("cache fixture hash mismatch")
    with np.load(package / paths[0], allow_pickle=False) as f:
        frames, positions, mask = (f[k].copy() for k in ("frames_rgb_u8", "patch_positions", "attention_mask"))
    with np.load(package / paths[1], allow_pickle=False) as f:
        features = f["merged_vision_bf16_bits"].copy()
    # Fixture-only namespace; these are provenance hashes, NOT live model keys.
    namespace = VisionIdentity(sha(package / "PACKAGE_MANIFEST.json"), sha(package / paths[1]),
                               sha(package / paths[0]), sha(ROOT / "bact/exact_vision_cache.py"))
    key = vision_key(namespace, frames, positions=positions, attention_mask=mask)
    cache = ExactVisionCache(8 << 20, max_entries=2)
    if cache.get(key) is not None or not cache.put(key, features):
        raise ValueError("unexpected initial cache state")
    hit = cache.get(key)
    if hit is None or hit.tobytes() != features.tobytes():
        raise ValueError("cache value mismatch")
    changed = frames.copy()
    changed.flat[0] ^= 1
    changed_key = vision_key(namespace, changed, positions=positions, attention_mask=mask)
    if cache.get(changed_key) is not None:
        raise ValueError("changed input incorrectly reused")
    return {"status": "PASS_EXACT_FIXTURE_CACHE", "stored_payload_bytes": cache.bytes_used,
            "value_sha256": hashlib.sha256(hit.tobytes()).hexdigest(),
            "single_pixel_change_is_miss": True, "full_window_keyed": True,
            "runtime_integrated": False, "model_forward_skipped_in_actual_runtime": False,
            "scope": "Real stored fixture insertion/readback only; namespace is not a live model identity; no speedup measured."}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--result", type=Path, required=True)
    args = parser.parse_args()
    try:
        suite = unittest.TestSuite([unittest.defaultTestLoader.loadTestsFromTestCase(cls) for cls in (FeatureTests, CacheTests)])
        test_result = unittest.TextTestRunner(verbosity=1).run(suite)
        if not test_result.wasSuccessful():
            raise ValueError("component tests failed")
        fixture = ROOT / "deployment/mage_vl4b/m120_text4b_board_candidate/reference/m128_m120_real_record_csim_fixture.bin"
        numeric = numeric_records(fixture)
        cache = real_cache()
        result = {"gate": "M318-offline-record-arithmetic-and-exact-cache",
                  "status": "PASS_OFFLINE_COMPONENTS_ONLY",
                  "tests_run": test_result.testsRun, "numeric": numeric, "cache": cache,
                  "sources": {str(p.relative_to(ROOT)): sha(p) for p in (Path(__file__).resolve(), ROOT / "bact/exact_vision_cache.py", ROOT / "scripts/m317_test_offline_components.py")},
                  "board_execution_run": False, "new_model_quality_measured": False,
                  "new_speedup_claim_allowed": False}
    except Exception as error:
        write_result(args.result, {"status": "FAIL_OFFLINE", "error": f"{type(error).__name__}: {error}", "board_execution_run": False})
        raise
    write_result(args.result, result)
    print("M318_OFFLINE_COMPONENTS_PASS", "dot_comparisons=", numeric["integer_dot_comparisons"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
