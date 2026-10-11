#!/usr/bin/env python3
"""Static fail-closed contract for the M310 post-label orchestration script."""

from __future__ import annotations

from pathlib import Path


def main() -> int:
    script = Path(__file__).with_name("m310_finalize_bact_after_human_review.ps1")
    text = script.read_text(encoding="utf-8")
    required_order = [
        "m304_import_human_review_workbook.mjs",
        "m308_run_one_shot_bact_evaluation.py",
        "m309_generate_bact_final_evidence_pack.py",
    ]
    positions = [text.index(value) for value in required_order]
    if positions != sorted(positions):
        raise RuntimeError("M310 stage order is not M304 -> M308 -> M309")
    required_fragments = [
        "dependencies\\node\\bin\\node.exe",
        "dependencies\\python\\python.exe",
        "PASS_HUMAN_LABELS_AND_CONDITIONS_FROZEN",
        "qcPassCount -ne 12",
        "PASS_PILOT_HELDOUT_EVALUATION_SEALED",
        "M308Seal.status -ne 'COMPLETE'",
        "M308Hash -ne $M308Seal.resultSha256",
        "PASS_FINAL_PILOT_EVIDENCE_PACK",
        "if ($LASTEXITCODE -ne 0)",
    ]
    missing = [value for value in required_fragments if value not in text]
    if missing:
        raise RuntimeError(f"M310 required fail-closed fragments missing: {missing}")
    forbidden = ["ssh.exe", "scp.exe", "plink", "COM3", "sudo", "boot", "dtb", "cma", "Invoke-Expression"]
    present = [value for value in forbidden if value.lower() in text.lower()]
    if present:
        raise RuntimeError(f"M310 contains forbidden board/deployment operations: {present}")
    print(
        "M310_POST_LABEL_PIPELINE_CONTRACT_PASS "
        "order=M304-M308-M309 exact_runtimes=true board_operations=false"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
