#!/usr/bin/env python3
"""Read-only structural comparison of two packed-weight layout manifests."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path


def load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("expected", type=Path, help="Manifest required by the stable runtime")
    parser.add_argument("candidate", type=Path, help="Older or alternate layout manifest")
    args = parser.parse_args()
    stable, other = load(args.expected), load(args.candidate)
    stable_modules = {m["module"]: m for m in stable["modules"]}
    other_modules = {m["module"]: m for m in other["modules"]}
    shared = stable_modules.keys() & other_modules.keys()
    shape_changes = sorted(k for k in shared if stable_modules[k].get("shape") != other_modules[k].get("shape"))
    bit_changes = sorted(k for k in shared if stable_modules[k].get("bits") != other_modules[k].get("bits"))
    tile_changes = sorted(k for k in shared if stable_modules[k].get("tiles") != other_modules[k].get("tiles"))
    file_changes = []
    for left, right in zip(stable.get("files", []), other.get("files", [])):
        if (left.get("path"), left.get("bytes"), left.get("sha256")) != (
            right.get("path"), right.get("bytes"), right.get("sha256")
        ):
            file_changes.append({"path": left.get("path"), "stable_bytes": left.get("bytes"),
                                 "candidate_bytes": right.get("bytes"),
                                 "stable_sha256": left.get("sha256"),
                                 "candidate_sha256": right.get("sha256")})
    result = {
        "stable": {"path": str(args.expected), "sha256": sha256(args.expected),
                   "source": stable.get("source"), "modules": len(stable_modules),
                   "tiles": sum(len(m.get("tiles", [])) for m in stable_modules.values())},
        "candidate": {"path": str(args.candidate), "sha256": sha256(args.candidate),
                      "source": other.get("source"), "modules": len(other_modules),
                      "tiles": sum(len(m.get("tiles", [])) for m in other_modules.values())},
        "parameters_equal": stable.get("parameters") == other.get("parameters"),
        "only_stable_modules": sorted(stable_modules.keys() - other_modules.keys()),
        "only_candidate_modules": sorted(other_modules.keys() - stable_modules.keys()),
        "shape_changes": {"count": len(shape_changes), "examples": shape_changes[:5]},
        "bit_changes": {"count": len(bit_changes), "examples": bit_changes[:5]},
        "tile_changes": {"count": len(tile_changes), "examples": tile_changes[:5]},
        "file_changes": file_changes,
        "conclusion": "layout-or-payload-differs" if (shape_changes or bit_changes or tile_changes or file_changes)
                      else "same-layout-and-payload-metadata; inspect formatting/other fields",
    }
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
