#!/usr/bin/env python3
"""Build a clean, reviewable M120 full-text runtime source tree.

This is a mechanical rebase of the accepted M89-X1 host runtime onto the
M120/M89X2 ABI.  It deliberately creates a new tree and never edits the
historical board candidate in place.
"""

from __future__ import annotations

import hashlib
import json
import shutil
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
OLD = ROOT / "deployment" / "mage_vl4b" / "m89x1_adaptive_scale_lmhead_board_candidate"
SMALL = ROOT / "deployment" / "mage_vl4b" / "m120_text4b_board_candidate"
DEST = ROOT / "deployment" / "mage_vl4b" / "m120_text4b_full_runtime"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(8 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def replace_exact(text: str, old: str, new: str, count: int = 1) -> str:
    observed = text.count(old)
    if observed != count:
        raise RuntimeError(
            f"exact replacement count mismatch expected={count} observed={observed} old={old!r}"
        )
    return text.replace(old, new)


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8", newline="\n")


def main() -> int:
    if DEST.exists():
        raise RuntimeError(f"destination already exists; refuse in-place mutation: {DEST}")

    runtime = DEST / "runtime"
    contracts = DEST / "contracts"
    overlay = DEST / "overlay"
    auxiliary = DEST / "auxiliary"
    for directory in (runtime, contracts, overlay, auxiliary, runtime / "support"):
        directory.mkdir(parents=True, exist_ok=False)

    board = (OLD / "runtime" / "board_runtime.py").read_text(encoding="utf-8")
    board = replace_exact(
        board,
        '"""Fail-closed PYNQ runtime for the M89-X four-port T32 candidate."""',
        '"""Fail-closed PYNQ runtime for the M120/M89X2 mixed-precision T32 candidate."""',
    )
    board = replace_exact(board, "BUILD_ID = 0x4D395831", "BUILD_ID = 0x4D395832")
    board = replace_exact(board, "class M89XBoardRuntime:", "class M120BoardRuntime:")
    board = replace_exact(
        board,
        'weight_mode: str = "resident-high-ddr"):',
        'weight_mode: str = "staged-low-cma"):',
    )
    board = replace_exact(
        board,
        'language_contract_path, "PASS_MERGED_648_TILE_RUNTIME_CONTRACT")',
        'language_contract_path, "PASS_M120_154_HOMOGENEOUS_LANGUAGE_CHAINS")',
    )
    board = replace_exact(
        board,
        'head_contract_path, "PASS_EXACT_LMHEAD_RUNTIME_CONTRACT")',
        'head_contract_path, "PASS_M120_W4_LMHEAD_8_CHAINS")',
    )
    board = replace_exact(
        board,
        'language_sha = self.language_contract.payload["source_evidence"]["fourport_layout_manifest_sha256"]',
        'language_sha = self.language_contract.payload["source_manifest_sha256"]',
    )
    board = replace_exact(
        board,
        "self.kernel = self.overlay.mage_m89x_t32_0",
        "self.kernel = self.overlay.mage_m120_m89x2_0",
    )
    board = board.replace("M89-X", "M120/M89X2")
    write_text(runtime / "board_runtime.py", board)

    text_gate = (OLD / "runtime" / "text_e2e_gate.py").read_text(encoding="utf-8")
    text_gate = replace_exact(
        text_gate,
        '"""Fixed 30-token/one-token M89-X text E2E gate for the first board run."""',
        '"""Fixed 30-token/one-token M120/M89X2 text E2E gate."""',
    )
    text_gate = text_gate.replace("M89XBoardRuntime", "M120BoardRuntime")
    text_gate = replace_exact(
        text_gate,
        "from board_runtime import M120BoardRuntime",
        "from board_runtime import M120BoardRuntime",
    )
    old_qkv = '''            qkv = self.runtime.language_family(layer, "qkv", normed)\n'''
    new_qkv = '''            if layer < 10:\n                qkv = {}\n                qkv.update(self.runtime.language_family(layer, "q", normed))\n                qkv.update(self.runtime.language_family(layer, "kv", normed))\n            else:\n                qkv = self.runtime.language_family(layer, "qkv", normed)\n'''
    text_gate = replace_exact(text_gate, old_qkv, new_qkv)
    text_gate = replace_exact(
        text_gate,
        'default="resident-high-ddr")',
        'default="staged-low-cma")',
    )
    text_gate = replace_exact(text_gate, '"gate": "M89-X-fixed-text-E2E"', '"gate": "M120-fixed-text-E2E"', 2)
    text_gate = replace_exact(text_gate, "expected_calls = 144 + 8", "expected_calls = 154 + 8")
    text_gate = replace_exact(
        text_gate,
        'runtime.head_contract.payload["total_expected_macros"]',
        'runtime.head_contract.payload["contract"]["total_expected_macros"]',
    )
    text_gate = replace_exact(
        text_gate,
        '"M89X_FIXED_TEXT_E2E_PASS" if result["status"] == "PASS" else "M89X_FIXED_TEXT_E2E_FAIL"',
        '"M120_FIXED_TEXT_E2E_PASS" if result["status"] == "PASS" else "M120_FIXED_TEXT_E2E_FAIL"',
    )
    write_text(runtime / "text_e2e_gate.py", text_gate)

    copy_sources = {
        OLD / "runtime" / "contract_runtime.py": runtime / "contract_runtime.py",
        OLD / "runtime" / "support" / "reserved_ddr_pool.py": runtime / "support" / "reserved_ddr_pool.py",
        SMALL / "runtime" / "m120_board_env_preflight.py": runtime / "m120_board_env_preflight.py",
        ROOT / "deployment" / "mage_vl4b" / "m120_text4b_runtime" / "m120_layer0_boundary_diagnostic.py": runtime / "m120_layer0_boundary_diagnostic.py",
        ROOT / "deployment" / "mage_vl4b" / "m120_text4b_runtime" / "m120_layer0_boundary_acceptance.py": runtime / "m120_layer0_boundary_acceptance.py",
        ROOT / "deployment" / "mage_vl4b" / "m120_text4b_runtime" / "run_m120_layer0_gate.sh": runtime / "run_m120_layer0_gate.sh",
        ROOT / "deployment" / "mage_vl4b" / "M126_LANGUAGE_RUNTIME_CONTRACT_RESULT.json": contracts / "M126_LANGUAGE_RUNTIME_CONTRACT_RESULT.json",
        ROOT / "deployment" / "mage_vl4b" / "M126_LMHEAD_RUNTIME_CONTRACT_RESULT.json": contracts / "M126_LMHEAD_RUNTIME_CONTRACT_RESULT.json",
        SMALL / "overlay" / "m120_m89x2_t32.bit": overlay / "m120_m89x2_t32.bit",
        SMALL / "overlay" / "m120_m89x2_t32.hwh": overlay / "m120_m89x2_t32.hwh",
        OLD / "auxiliary" / "m77_text_aux_fp16.npz": auxiliary / "m77_text_aux_fp16.npz",
        OLD / "auxiliary" / "M77_TEXT_AUX_MANIFEST.json": auxiliary / "M77_TEXT_AUX_MANIFEST.json",
        OLD / "auxiliary" / "official_cpu_text_1token.json": auxiliary / "official_cpu_text_1token.json",
    }
    copied = []
    for source, target in copy_sources.items():
        if not source.is_file():
            raise FileNotFoundError(source)
        shutil.copyfile(source, target)
        copied.append({
            "path": target.relative_to(DEST).as_posix(),
            "bytes": target.stat().st_size,
            "sha256": sha256(target),
            "source": source.relative_to(ROOT).as_posix(),
        })

    copied.extend(
        {
            "path": path.relative_to(DEST).as_posix(),
            "bytes": path.stat().st_size,
            "sha256": sha256(path),
            "source": "generated-by-m142",
        }
        for path in (runtime / "board_runtime.py", runtime / "text_e2e_gate.py")
    )
    manifest = {
        "date": "2026-09-01",
        "gate": "M142-M120-full-text-runtime-source",
        "status": "SOURCE_PREPARED_NOT_BOARD_EXECUTED",
        "build_id": "0x4D395832",
        "kernel": "mage_m120_m89x2_0",
        "weight_mode": "staged-low-cma",
        "language_contract_status": "PASS_M120_154_HOMOGENEOUS_LANGUAGE_CHAINS",
        "head_contract_status": "PASS_M120_W4_LMHEAD_8_CHAINS",
        "language_chain_count": 154,
        "head_chain_count": 8,
        "split_q_kv_layers": list(range(10)),
        "files": sorted(copied, key=lambda item: item["path"]),
        "board_state_changed": False,
        "stable_rollback_preserved": True,
    }
    write_text(DEST / "SOURCE_MANIFEST.json", json.dumps(manifest, indent=2) + "\n")
    print(json.dumps({
        "status": manifest["status"],
        "destination": str(DEST),
        "files": len(manifest["files"]),
        "bytes": sum(item["bytes"] for item in manifest["files"]),
        "manifest_sha256": sha256(DEST / "SOURCE_MANIFEST.json"),
    }, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
