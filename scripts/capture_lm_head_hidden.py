#!/usr/bin/env python3
"""Capture real final hidden states while preserving the normal FP16 LM head."""

from __future__ import annotations

import argparse
import json
import types
from pathlib import Path

import numpy as np

from qwen_fpga_runtime import QwenRuntime


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--output", type=Path, default=Path("/dev/shm/qwen_lm_head_hidden.npy"))
    args = parser.parse_args()

    model = QwenRuntime(args.root)
    captured: list[np.ndarray] = []
    original = model._lm_head

    def capture(self: QwenRuntime, hidden: np.ndarray) -> np.ndarray:
        captured.append(np.asarray(hidden, dtype=np.float32).copy())
        return original(hidden)

    model._lm_head = types.MethodType(capture, model)
    try:
        answer, proof = model.generate("3+26等于多少", max_new_tokens=4, sampling="argmax")
        hidden = np.stack(captured)
        np.save(args.output, hidden)
        print(
            json.dumps(
                {
                    "status": "PASS",
                    "answer": answer,
                    "shape": list(hidden.shape),
                    "output": str(args.output),
                    "build_id": proof["build_id"],
                },
                ensure_ascii=False,
                sort_keys=True,
            )
        )
    finally:
        model.engine.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
