#!/usr/bin/env python3
"""Run the M19 residency method against the real 3B embedding without FPGA."""

from __future__ import annotations

import argparse
import gc
import json
import sys
from pathlib import Path

import numpy as np


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "deployment/qwen25_3b_directddr_chain/runtime"))
sys.path.insert(0, str(ROOT / "deployment/qwen25_3b_no_final_forward/runtime"))

from resident_chain_runtime import EMBEDDING_NAME, QwenResidentRuntime  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--model-root", type=Path, required=True)
    args = parser.parse_args()
    model_root = args.model_root.resolve()
    indexes = sorted((model_root / "model").glob("*_mixed_gs_index.json"))
    if len(indexes) != 1:
        raise RuntimeError(f"expected one model index, found {len(indexes)}")
    index = json.loads(indexes[0].read_text())
    item = next(value for value in index["aux_tensors"] if value["name"] == EMBEDDING_NAME)
    aux_blob = model_root / "model" / Path(index["aux_file"]["path"]).name
    source = np.memmap(
        aux_blob,
        dtype="<f2",
        mode="r",
        offset=int(item["offset"]),
        shape=tuple(item["shape"]),
    )
    runtime = QwenResidentRuntime.__new__(QwenResidentRuntime)
    runtime.index = index
    runtime.aux_blob = aux_blob
    runtime.embedding = source
    runtime.aux = {EMBEDDING_NAME: source}
    # WSL has no board CMA.  The real-data gate validates storage ownership,
    # full SHA and exact values; board memory floors remain separate mandatory
    # checks in the runtime and full E2E gate.
    meminfo = {
        "CmaFree": iter((800_000, 700_000)),
        "Cached": iter((800_000, 100_000)),
        "MemAvailable": iter((8_000_000, 7_000_000)),
    }
    runtime._meminfo_kib = lambda name: next(meminfo[name])
    result = runtime._materialize_tied_embedding()
    sample_rows = [0, 1, 4096, 71655, 100647, int(item["shape"][0]) - 1]
    sample_sha = []
    for row in sample_rows:
        sample_sha.append(
            {
                "row": row,
                "exact": bool(
                    np.array_equal(
                        runtime.embedding[row],
                        np.memmap(
                            aux_blob,
                            dtype="<f2",
                            mode="r",
                            offset=int(item["offset"]) + row * int(item["shape"][1]) * 2,
                            shape=(int(item["shape"][1]),),
                        ),
                    )
                ),
            }
        )
    passed = result["status"] == "PASS" and all(value["exact"] for value in sample_sha)
    output = {
        "milestone": "M19",
        "gate": "real-qwen25-3b-anonymous-tied-embedding-host-gate",
        "status": "PASS" if passed else "FAIL",
        "model_root": str(model_root),
        "residency": result,
        "sample_rows": sample_sha,
        "board_memory_values_simulated": True,
    }
    print(json.dumps(output, ensure_ascii=False, sort_keys=True))
    runtime.aux.clear()
    runtime.embedding = None
    gc.collect()
    print("QWEN_M19_REAL_EMBEDDING_HOST_PASS" if passed else "QWEN_M19_REAL_EMBEDDING_HOST_FAIL")
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
