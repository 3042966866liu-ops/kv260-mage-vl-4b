"""Fail-closed local evidence/compilation verifier for the M316-M318 batch."""
from __future__ import annotations
import json
from pathlib import Path
import sys
sys.dont_write_bytecode = True
from m316_offline_deployment_audit import sha, write_result

ROOT = Path(__file__).resolve().parents[1]


def local(path: str) -> Path:
    p = (ROOT / path).resolve()
    if not p.is_relative_to(ROOT) or not p.is_file():
        raise ValueError("invalid evidence path")
    return p


def main() -> int:
    out = ROOT / "deployment/mage_vl4b/M318_OFFLINE_BUNDLE_VERIFICATION.json"
    try:
        sources = ["bact/feature_budget.py", "bact/exact_vision_cache.py",
                   "scripts/m316_offline_deployment_audit.py", "scripts/m317_run_feature_budget_offline.py",
                   "scripts/m317_test_offline_components.py", "scripts/m318_run_offline_numeric_cache_gate.py",
                   "scripts/m318_verify_offline_evidence.py"]
        for path in sources:
            p = local(path)
            compile(p.read_text(encoding="utf-8"), str(p), "exec")  # no .pyc writes
        paths = ["deployment/mage_vl4b/M316_OFFLINE_DEPLOYMENT_AUDIT_RESULT.json",
                 "deployment/mage_vl4b/M317_FEATURE_BUDGET_OFFLINE_RESULT.json",
                 "deployment/mage_vl4b/M318_NUMERIC_CACHE_OFFLINE_RESULT.json"]
        results = [json.loads(local(p).read_text(encoding="utf-8")) for p in paths]
        expected = ["PASS_OFFLINE_AUDIT_NOT_NEW_PERFORMANCE", "PASS_OFFLINE_FEATURE_SELECTION_NOT_SEMANTIC_ACCEPTANCE",
                    "PASS_OFFLINE_COMPONENTS_ONLY"]
        for value, status in zip(results, expected):
            if value["status"] != status or value["board_execution_run"] is not False:
                raise ValueError("invalid offline result status")
            for path, expected_hash in value["sources"].items():
                if sha(local(path)) != expected_hash:
                    raise ValueError(f"stale source/evidence: {path}")
        if results[2]["numeric"]["integer_dot_comparisons"] != 1589248 or results[2]["tests_run"] != 11:
            raise ValueError("numeric/test count mismatch")
        feature = results[1]
        rows = feature["candidate_rows"]
        if len(rows) != 10 or feature["model_quality_measured"] is not False:
            raise ValueError("feature evidence scope mismatch")
        for row in rows:
            if row["visual_tokens"] != len(row["indices"]) or row["total_tokens"] != len(row["indices"]) + 65:
                raise ValueError("feature token identity mismatch")
            if row["legacy_logical_calls"] != 154*((row["total_tokens"]+31)//32)+8:
                raise ValueError("conditional call identity mismatch")
        selected = feature["selected_under_explicit_uncalibrated_threshold"]
        if selected["mean_feature_distance"] > feature["maximum_feature_distance"]:
            raise ValueError("selected candidate violates explicit proxy constraint")
        board = json.loads(local("deployment/mage_vl4b/BOARD_GATE_RESULT.json").read_text(encoding="utf-8"))
        entry = board["latest_m316_m318_offline_components"]
        if entry["board_execution_run"] is not False or entry["new_speedup_or_quality_claim_allowed"] is not False:
            raise ValueError("offline entry incorrectly promoted")
        report = "OFFLINE_OPTIMIZATION_M316_M318.md"
        manifest_paths = sources + paths + [report]
        result = {"status": "PASS_LOCAL_EVIDENCE_CLOSURE_ONLY", "board_execution_run": False,
                  "python_sources_compiled_without_bytecode": len(sources),
                  "result_source_hashes_verified": True,
                  "files": [{"path": p, "bytes": local(p).stat().st_size, "sha256": sha(local(p))} for p in manifest_paths],
                  "notes": "Not a board package, no full runtime dependency or HLS closure claimed; only local offline Python components."}
    except Exception as error:
        write_result(out, {"status": "FAIL_OFFLINE_CLOSURE", "error": f"{type(error).__name__}: {error}"})
        raise
    write_result(out, result)
    print("M318_OFFLINE_EVIDENCE_CLOSURE_PASS", f"files={len(manifest_paths)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
