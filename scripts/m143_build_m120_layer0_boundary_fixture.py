#!/usr/bin/env python3
"""Extract a compact M120 Layer-0 boundary fixture from the accepted M127 golden."""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path

import numpy as np


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "deployment" / "mage_vl4b" / "artifacts" / "m127_m120_same_quantized_family_inputs.npz"
SOURCE_RESULT = ROOT / "deployment" / "mage_vl4b" / "M127_M120_SAME_QUANTIZED_GOLDEN_RESULT.json"
OUTPUT = ROOT / "deployment" / "mage_vl4b" / "artifacts" / "m143_m120_layer0_boundaries.npz"
RESULT = ROOT / "deployment" / "mage_vl4b" / "M143_M120_LAYER0_BOUNDARY_FIXTURE_RESULT.json"
EXPECTED_SOURCE_SHA256 = "16abe560e085dc9417bdea569ccf9d1799810bdc741f8f11a726417b891edd2e"
KEYS = (
    "layer00_q",
    "layer00_kv",
    "layer00_attention_out",
    "layer00_gate_up",
    "layer00_mlp_down",
    "layer01_q",
    "layer01_kv",
)


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
        "gate": "M143-M120-layer0-boundary-fixture",
        "status": "FAIL",
        "classification": "offline compact extraction from accepted M127 golden; not board evidence",
        "board_state_changed": False,
        "stable_rollback_preserved": True,
    }
    try:
        source_result = json.loads(SOURCE_RESULT.read_text(encoding="utf-8"))
        if source_result.get("status") != "PASS_M120_SAME_QUANTIZED_154_CHAIN_GOLDEN":
            raise RuntimeError("M127 status mismatch")
        if sha256(SOURCE) != EXPECTED_SOURCE_SHA256:
            raise RuntimeError("M127 golden identity mismatch")
        with np.load(SOURCE, allow_pickle=False) as archive:
            if any(key not in archive.files for key in KEYS):
                raise RuntimeError("required Layer-0/1 boundary missing")
            arrays = {key: np.asarray(archive[key], dtype="<f4") for key in KEYS}
        if not all(array.ndim == 2 and array.shape[0] == 30 for array in arrays.values()):
            raise RuntimeError("boundary geometry mismatch")
        if not all(np.isfinite(array).all() for array in arrays.values()):
            raise RuntimeError("non-finite boundary")
        OUTPUT.parent.mkdir(parents=True, exist_ok=True)
        temporary = OUTPUT.with_suffix(OUTPUT.suffix + f".tmp-{os.getpid()}")
        with temporary.open("wb") as handle:
            np.savez_compressed(handle, **arrays)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, OUTPUT)
        result.update(
            {
                "status": "PASS",
                "source_sha256": EXPECTED_SOURCE_SHA256,
                "fixture": str(OUTPUT.relative_to(ROOT).as_posix()),
                "fixture_bytes": OUTPUT.stat().st_size,
                "fixture_sha256": sha256(OUTPUT),
                "arrays": {
                    key: {
                        "shape": list(array.shape),
                        "dtype": str(array.dtype),
                        "sha256_fp32": hashlib.sha256(array.astype("<f4", copy=False).tobytes()).hexdigest(),
                    }
                    for key, array in arrays.items()
                },
                "next_gate": "Package this fixture with an M120 Layer-0 boundary diagnostic; execution remains locked behind M140 single-chain PASS.",
            }
        )
    except BaseException as error:
        result["error"] = f"{type(error).__name__}: {error}"
        result["next_gate"] = "Correct and rerun M143 offline only."
    atomic_json(RESULT, result)
    print(json.dumps(result, indent=2))
    print("M143_M120_LAYER0_BOUNDARY_FIXTURE_PASS" if result["status"] == "PASS" else "M143_M120_LAYER0_BOUNDARY_FIXTURE_FAIL")
    return 0 if result["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
