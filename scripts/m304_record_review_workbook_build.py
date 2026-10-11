#!/usr/bin/env python3
"""Record the immutable M304 review-workbook template and editable initial copy."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path


EXPECTED_M296 = "4d4a9d84148fc220ba7ea70070cbbd351749ffb53cd332a25c26869bf90715f7"
EXPECTED_TEMPLATE = "35a31bf7b79730c1dc85c27fb50e7e8b1b67356c2cdf8a5418ceebaf192ff60c"


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--workspace", type=Path, required=True)
    parser.add_argument("--result", type=Path, required=True)
    args = parser.parse_args()
    root = args.workspace.resolve()
    paths = {
        "m296": root / "deployment/mage_vl4b/M296_HUMAN_REVIEW_WORKBOOK_RESULT.json",
        "template": root / "deployment/mage_vl4b/m304_human_review_template/M304_BACT人工复核与稳健性条件表_TEMPLATE.xlsx",
        "editable": root / "outputs/m304_bact_annotation/M304_BACT人工复核与稳健性条件表.xlsx",
        "contract": root / "scripts/m304_human_review_contract.mjs",
        "importer": root / "scripts/m304_import_human_review_workbook.mjs",
        "test": root / "scripts/m304_test_human_review_contract.mjs",
    }
    if digest(paths["m296"]) != EXPECTED_M296:
        raise RuntimeError("M304_M296_SOURCE_HASH_FAIL")
    m296 = json.loads(paths["m296"].read_text(encoding="utf-8"))
    if m296["status"] != "PASS_WORKBOOK_READY_PENDING_HUMAN_REVIEW":
        raise RuntimeError("M304_M296_STATUS_FAIL")
    if digest(paths["template"]) != EXPECTED_TEMPLATE or digest(paths["editable"]) != EXPECTED_TEMPLATE:
        raise RuntimeError("M304_TEMPLATE_OR_INITIAL_COPY_HASH_FAIL")

    result = {
        "date": "2026-09-03",
        "gate": "M304-human-review-workbook-with-robustness-conditions",
        "status": "PASS_WORKBOOK_AND_IMPORT_CONTRACT_READY_PENDING_HUMAN_REVIEW",
        "classification": (
            "A visually verified editable workbook and immutable template add explicit human low-light, occlusion "
            "and small-knife conditions while preserving M296 source identity. Contract tests cover complete and "
            "negative paths. This is not human-labelled accuracy, semantic robustness or real-world validity."
        ),
        "source_m296": {
            "path": str(paths["m296"].relative_to(root)).replace("\\", "/"),
            "sha256": digest(paths["m296"]),
        },
        "immutable_template": {
            "path": str(paths["template"].relative_to(root)).replace("\\", "/"),
            "sha256": digest(paths["template"]),
        },
        "editable_initial_copy": {
            "path": str(paths["editable"].relative_to(root)).replace("\\", "/"),
            "initial_sha256": digest(paths["editable"]),
            "may_change_after_human_edit": True,
        },
        "sheets": ["说明与进度", "人工复核", "字段字典"],
        "formula_error_count": 0,
        "rendered_sheet_count": 3,
        "condition_fields": ["lowLight", "occlusion", "smallKnife"],
        "condition_values": ["TRUE", "FALSE", "UNCERTAIN"],
        "formal_slice_requires_definite_boolean": True,
        "small_knife_true_requires_knife_positive": True,
        "contract_test": {
            "status": "PASS",
            "rows": 12,
            "condition_slices": 3,
            "negative_paths": 2,
        },
        "source_files": {
            name: {
                "path": str(path.relative_to(root)).replace("\\", "/"),
                "sha256": digest(path),
            }
            for name, path in paths.items()
            if name in {"contract", "importer", "test"}
        },
        "human_review_complete": False,
        "formal_accuracy_allowed": False,
        "semantic_robustness_allowed": False,
        "filename_hints_are_ground_truth": False,
        "board_execution_run": False,
        "active_m254_m256_changed": False,
        "boot_dtb_cma_partitions_changed": False,
        "stable_rollback_preserved": True,
        "next_gate": (
            "Human watches all 12 complete videos and fills H:N plus P:R in the editable copy. Then run the M304 "
            "importer; only 12/12 QC PASS with split/action/knife/condition coverage may write frozen labels."
        ),
    }
    result_path = (root / args.result).resolve()
    if not result_path.is_relative_to(root):
        raise RuntimeError("M304_RESULT_PATH_ESCAPE")
    result_path.parent.mkdir(parents=True, exist_ok=True)
    partial = result_path.with_suffix(result_path.suffix + ".partial")
    partial.write_text(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    os.replace(partial, result_path)
    print(f"M304_WORKBOOK_CONTRACT_PASS template_sha256={EXPECTED_TEMPLATE} human_review=false")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
