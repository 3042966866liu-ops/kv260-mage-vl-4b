"""Content-driven proposals on existing hash-verified vision features, no forward."""
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
from dataclasses import asdict
import json
import time
import numpy as np
from bact.feature_budget import propose_budgets, choose_proposal, measure_subset
from m316_offline_deployment_audit import sha, write_result


def run(maximum_feature_distance: float) -> dict:
    package = ROOT / "deployment/mage_vl4b/m181_m120_video_board_candidate"
    manifest_path = package / "PACKAGE_MANIFEST.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    # Verify the two consumed fixtures, NOT the whole historic board package.
    consumed = ("fixtures/official_four_frame_processor.npz", "fixtures/official_vision_merged_bf16.npz")
    files = {record["path"]: record for record in manifest["files"]}
    evidence = {}
    for rel in consumed:
        path = package / rel
        if sha(path) != files[rel]["sha256"] or path.stat().st_size != files[rel]["bytes"]:
            raise ValueError(f"fixture integrity mismatch: {rel}")
        evidence[rel] = sha(path)
    with np.load(package / consumed[0], allow_pickle=False) as data:
        grid = data["image_grid_thw"].copy()
        total_input = int(data["input_ids"].shape[1])
    with np.load(package / consumed[1], allow_pickle=False) as data:
        bits = data["merged_vision_bf16_bits"].copy()
    if bits.dtype != np.uint16 or bits.shape != (784, 2560):
        raise ValueError("unexpected historical feature geometry")
    if grid.shape != (4, 3) or not np.array_equal(grid, np.tile([1, 28, 28], (4, 1))) or total_input != 849:
        raise ValueError("cannot infer view boundaries from this processor fixture")
    features = (bits.astype(np.uint32) << 16).view(np.float32)
    views = np.repeat(np.arange(4, dtype=np.int64), 196)
    text_tokens = total_input - len(features)  # 65; preserve every existing text/special token.
    budgets = [62, 63, 64, 94, 95, 96, 126, 127, 128, 784]
    begin = time.perf_counter()
    proposals = propose_budgets(features, views, budgets, text_tokens)
    elapsed = (time.perf_counter() - begin) * 1000
    # This rerun is cheap local selection only, not CSim or model computation.
    again = propose_budgets(features, views, budgets, text_tokens)
    if proposals != again:
        raise ValueError("nondeterministic proposal")
    rows = []
    for proposal in proposals:
        independent = measure_subset(features, views, list(proposal.indices))
        if abs(independent["mean_feature_distance"] - proposal.mean_feature_distance) > 1e-12:
            raise ValueError("independent coverage verification failed")
        # Same counts in each view isolates selection from allocation differences.
        uniform = []
        for view, count in proposal.per_view_counts:
            group = np.flatnonzero(views == view)
            uniform.extend(int(i) for i in group[np.linspace(0, len(group)-1, count, dtype=int)])
        record = asdict(proposal)
        record["uniform_same_view_budget_comparator"] = measure_subset(features, views, uniform)
        rows.append(record)
    selected = choose_proposal(proposals, maximum_feature_distance)
    return {
        "gate": "M317-feature-driven-budget-offline",
        "status": "PASS_OFFLINE_FEATURE_SELECTION_NOT_SEMANTIC_ACCEPTANCE",
        "input_provenance": "Existing M181 official BF16 visual-output fixture; no new model forward, no labels, no held-out data.",
        "consumed_fixture_hashes": evidence,
        "package_manifest_sha256": sha(manifest_path),
        "sources": {str(p.relative_to(ROOT)): sha(p) for p in (Path(__file__).resolve(), ROOT / "bact/feature_budget.py")},
        "original_visual_tokens": 784, "preserved_text_and_special_tokens": text_tokens,
        "input_stage": "after visual encoder/projector; vision cost NOT reduced",
        "candidate_rows": rows,
        "selected_under_explicit_uncalibrated_threshold": asdict(selected),
        "maximum_feature_distance": maximum_feature_distance,
        "threshold_calibrated_for_quality": False,
        "selection_wall_ms_windows_only": elapsed,
        "logical_calls_are_legacy_geometry_projection_not_observed": True,
        "legacy_cost_scope": "154*ceil(N/32)+8 assumes unchanged language chain/head; not valid automatically for a new generative head or pruned layers.",
        "deterministic_rerun": True,
        "model_position_mask_adapter_implemented": False,
        "model_quality_measured": False,
        "board_execution_run": False,
        "deployment_speedup_claim_allowed": False,
        "next_gate": "Offline position/mask/visual-placeholder adapter and full forward quality against uncompressed model; do not deploy raw indices.",
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--maximum-feature-distance", type=float, required=True)
    parser.add_argument("--result", type=Path, required=True)
    args = parser.parse_args()
    try:
        result = run(args.maximum_feature_distance)
    except Exception as error:
        write_result(args.result, {"status": "FAIL_OFFLINE", "error": f"{type(error).__name__}: {error}", "board_execution_run": False})
        raise
    write_result(args.result, result)
    chosen = result["selected_under_explicit_uncalibrated_threshold"]
    print("M317_FEATURE_PROPOSALS_PASS", "tokens=", chosen["total_tokens"],
          "proxy=", chosen["mean_feature_distance"], "NOT_SEMANTIC_PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
