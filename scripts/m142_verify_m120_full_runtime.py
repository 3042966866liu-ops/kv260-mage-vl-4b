#!/usr/bin/env python3
"""Fail-closed offline verification for the M142 M120 full-text runtime tree."""

from __future__ import annotations

import ast
import hashlib
import json
import os
import sys
from pathlib import Path


sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[1]
CANDIDATE = ROOT / "deployment" / "mage_vl4b" / "m120_text4b_full_runtime"
RESULT = ROOT / "deployment" / "mage_vl4b" / "M142_M120_FULL_RUNTIME_SOURCE_RESULT.json"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(8 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def atomic_json(path: Path, payload: dict) -> None:
    temporary = path.with_suffix(path.suffix + f".tmp-{os.getpid()}")
    temporary.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    os.replace(temporary, path)


def main() -> int:
    result = {
        "date": "2026-09-01",
        "gate": "M142-M120-full-text-runtime-source",
        "status": "FAIL",
        "classification": "offline runtime-source verification; not a board, E2E, performance, video or Web PASS",
        "board_state_changed": False,
        "stable_rollback_preserved": True,
    }
    try:
        manifest_path = CANDIDATE / "SOURCE_MANIFEST.json"
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        if manifest.get("status") != "SOURCE_PREPARED_NOT_BOARD_EXECUTED":
            raise RuntimeError("source manifest status mismatch")
        if manifest.get("build_id") != "0x4D395832":
            raise RuntimeError("build ID mismatch")
        if manifest.get("kernel") != "mage_m120_m89x2_0":
            raise RuntimeError("kernel identity mismatch")
        if manifest.get("weight_mode") != "staged-low-cma":
            raise RuntimeError("stable low-CMA mode is not the default")

        declared = {item["path"]: item for item in manifest["files"]}
        actual = {
            path.relative_to(CANDIDATE).as_posix()
            for path in CANDIDATE.rglob("*")
            if path.is_file() and path.name != "SOURCE_MANIFEST.json"
        }
        if set(declared) != actual:
            raise RuntimeError(
                f"file closure mismatch missing={sorted(set(declared)-actual)} extra={sorted(actual-set(declared))}"
            )
        for relative, item in declared.items():
            path = CANDIDATE / relative
            if path.stat().st_size != int(item["bytes"]) or sha256(path) != item["sha256"]:
                raise RuntimeError(f"file identity mismatch: {relative}")
        forbidden = [
            path.relative_to(CANDIDATE).as_posix()
            for path in CANDIDATE.rglob("*")
            if path.name == "__pycache__" or path.suffix == ".pyc"
        ]
        if forbidden:
            raise RuntimeError(f"forbidden cache files: {forbidden}")

        runtime = CANDIDATE / "runtime"
        python_files = sorted(runtime.rglob("*.py"))
        for path in python_files:
            ast.parse(path.read_text(encoding="utf-8"), filename=str(path))

        board_text = (runtime / "board_runtime.py").read_text(encoding="utf-8")
        text_gate = (runtime / "text_e2e_gate.py").read_text(encoding="utf-8")
        required_board_fragments = (
            "BUILD_ID = 0x4D395832",
            'language_contract_path, "PASS_M120_154_HOMOGENEOUS_LANGUAGE_CHAINS"',
            'head_contract_path, "PASS_M120_W4_LMHEAD_8_CHAINS"',
            "self.kernel = self.overlay.mage_m120_m89x2_0",
            'weight_mode: str = "staged-low-cma"',
        )
        if any(fragment not in board_text for fragment in required_board_fragments):
            raise RuntimeError("board runtime M120 identity closure failed")
        required_gate_fragments = (
            "if layer < 10:",
            'language_family(layer, "q", normed)',
            'language_family(layer, "kv", normed)',
            'language_family(layer, "qkv", normed)',
            "expected_calls = 154 + 8",
            'default="staged-low-cma"',
        )
        if any(fragment not in text_gate for fragment in required_gate_fragments):
            raise RuntimeError("text gate M120 scheduling closure failed")

        sys.path.insert(0, str(runtime.resolve()))
        from contract_runtime import RuntimeContract

        language = RuntimeContract.load(
            CANDIDATE / "contracts" / "M126_LANGUAGE_RUNTIME_CONTRACT_RESULT.json",
            "PASS_M120_154_HOMOGENEOUS_LANGUAGE_CHAINS",
        )
        head = RuntimeContract.load(
            CANDIDATE / "contracts" / "M126_LMHEAD_RUNTIME_CONTRACT_RESULT.json",
            "PASS_M120_W4_LMHEAD_8_CHAINS",
        )
        if len(language.chains) != 154 or len(head.chains) != 8:
            raise RuntimeError("contract chain count mismatch")
        families = {
            layer: {chain["family"] for chain in language.chains if int(chain["layer"]) == layer}
            for layer in range(36)
        }
        split = {"q", "kv", "attention_out", "gate_up", "mlp_down"}
        merged = {"qkv", "attention_out", "gate_up", "mlp_down"}
        if any(families[layer] != split for layer in range(10)):
            raise RuntimeError("layers 0..9 are not q/kv split")
        if any(families[layer] != merged for layer in range(10, 36)):
            raise RuntimeError("layers 10..35 are not merged qkv")

        aux_manifest_path = CANDIDATE / "auxiliary" / "M77_TEXT_AUX_MANIFEST.json"
        aux_path = CANDIDATE / "auxiliary" / "m77_text_aux_fp16.npz"
        aux_manifest = json.loads(aux_manifest_path.read_text(encoding="utf-8"))
        if aux_manifest.get("result") != "PASS" or aux_manifest.get("payload_sha256") != sha256(aux_path):
            raise RuntimeError("auxiliary identity mismatch")
        reference = json.loads(
            (CANDIDATE / "auxiliary" / "official_cpu_text_1token.json").read_text(encoding="utf-8")
        )
        if len(reference.get("prompt_token_ids", [])) != 30 or reference.get("generated_token_ids") != [17]:
            raise RuntimeError("frozen one-token reference mismatch")
        golden = json.loads(
            (ROOT / "deployment" / "mage_vl4b" / "M127_M120_SAME_QUANTIZED_GOLDEN_RESULT.json").read_text(encoding="utf-8")
        )
        if golden.get("status") != "PASS_M120_SAME_QUANTIZED_154_CHAIN_GOLDEN":
            raise RuntimeError("M127 golden status mismatch")
        if golden.get("prompt_token_count") != 30 or golden.get("m120_a8_token_id") != 17:
            raise RuntimeError("M127 fixed-reference token mismatch")

        result.update(
            {
                "status": "PASS",
                "source_manifest_sha256": sha256(manifest_path),
                "file_count": len(declared),
                "total_bytes": sum(int(item["bytes"]) for item in declared.values()),
                "python_file_count": len(python_files),
                "build_id": "0x4D395832",
                "kernel": "mage_m120_m89x2_0",
                "weight_mode": "staged-low-cma",
                "language_chain_count": len(language.chains),
                "head_chain_count": len(head.chains),
                "expected_logical_calls": len(language.chains) + len(head.chains),
                "split_q_kv_layers": list(range(10)),
                "reference_token_id": 17,
                "next_gate": "After M138/M139/M140 board PASS, package the M143 compact fixture and execute the predeclared M144 Layer-0 boundary gate; fixed-text E2E remains locked behind Layer-0.",
            }
        )
    except BaseException as error:
        result["error"] = f"{type(error).__name__}: {error}"
        result["next_gate"] = "Correct and rerun M142 offline only; do not load an overlay."
    atomic_json(RESULT, result)
    print(json.dumps(result, indent=2))
    print("M142_M120_FULL_RUNTIME_SOURCE_PASS" if result["status"] == "PASS" else "M142_M120_FULL_RUNTIME_SOURCE_FAIL")
    return 0 if result["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
