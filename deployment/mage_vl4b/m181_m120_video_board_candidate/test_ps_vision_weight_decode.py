#!/usr/bin/env python3
"""Bit-exact audit of the lazy four-port decoder against canonical M56."""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

import numpy as np
import torch

from ps_vision_runtime import FourPortW4Store


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--layout", type=Path, required=True)
    parser.add_argument("--m56", type=Path, required=True)
    parser.add_argument("--helpers", type=Path, required=True)
    parser.add_argument("--result", type=Path, required=True)
    args = parser.parse_args()
    sys.path.insert(0, str(args.helpers.resolve()))
    from mixed_bit_checkpoint import (  # type: ignore[import-not-found]
        reconstruct_full_range_rows_from_storage,
        unpack_orientation_bits,
        unpack_unsigned_codes,
    )

    manifest = json.loads((args.m56 / "CHECKPOINT_MANIFEST.json").read_text(encoding="utf-8"))
    selected = {entry["name"]: entry for entry in manifest["entries"]
                if entry["kind"] == "packed" and entry["name"].startswith("model.visual.")}
    store = FourPortW4Store(args.layout)
    mismatched = []
    compared = 0
    try:
        with (args.m56 / manifest["blob"]["path"]).open("rb") as blob:
            for short, layout_entry in store.entries.items():
                source = selected[layout_entry["source_name"]]
                sections = source["sections"]
                rows, columns = map(int, source["shape"])
                groups = int(source["padded_columns"]) // int(source["group_size"])
                blob.seek(int(sections["codes"]["offset"]))
                codes = unpack_unsigned_codes(blob.read(int(sections["codes"]["bytes"])), 4,
                                              rows * int(source["padded_columns"]))
                blob.seek(int(sections["scales"]["offset"]))
                scales = np.frombuffer(blob.read(int(sections["scales"]["bytes"])), dtype="<u2").copy()
                blob.seek(int(sections["orientations"]["offset"]))
                orientations = unpack_orientation_bits(blob.read(int(sections["orientations"]["bytes"])),
                                                       rows * groups)
                expected = reconstruct_full_range_rows_from_storage(
                    torch, codes, scales, orientations, 4, rows, columns, int(source["group_size"]),
                    output_dtype=torch.bfloat16, scale_format=manifest["scale_format"],
                )
                observed = torch.from_numpy(store.decode(short)).to(torch.bfloat16)
                errors = int(torch.count_nonzero(observed.view(torch.uint16) != expected.view(torch.uint16)).item())
                compared += int(expected.numel())
                if errors:
                    mismatched.append({"module": short, "errors": errors, "elements": int(expected.numel())})
    finally:
        store.close()
    result = {
        "gate": "M90-lazy-fourport-visual-weight-decode",
        "status": "PASS" if not mismatched and len(selected) == 98 else "FAIL",
        "module_count": len(selected),
        "compared_bf16_elements": compared,
        "mismatched_modules": mismatched,
        "board_state_changed": False,
    }
    args.result.parent.mkdir(parents=True, exist_ok=True)
    temporary = args.result.with_suffix(args.result.suffix + ".tmp")
    temporary.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    os.replace(temporary, args.result)
    print("M90_PS_VISION_WEIGHT_DECODE_PASS" if result["status"] == "PASS" else "M90_PS_VISION_WEIGHT_DECODE_FAIL")
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
