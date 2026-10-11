#!/usr/bin/env python3
"""Fail-closed source audit and descriptor-table generator for M89.

The script deliberately refuses an older or incomplete packed checkpoint.
It is offline-only: it reads a manifest and emits an audit JSON; it never
reads model weights, emits an FPGA artifact, or communicates with a board.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from collections import defaultdict
from pathlib import Path


EXPECTED_M56_BLOB_SHA256 = "24774ce383eb8261257942bb2a7a565d75fa3961754905973759d8e58ac24e4f"
EXPECTED_LANGUAGE_PACKED = 252
LANGUAGE_PREFIX = "model.language_model.layers."


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def module_layer(name: str) -> int:
    suffix = name.removeprefix(LANGUAGE_PREFIX)
    return int(suffix.split(".", 1)[0])


def section_descriptor(entry: dict, field: str) -> dict:
    section = entry["sections"][field]
    return {"offset": int(section["offset"]), "bytes": int(section["bytes"]), "sha256": section["sha256"]}


def build_groups(entries: list[dict]) -> dict:
    by_layer: dict[int, dict[str, dict]] = defaultdict(dict)
    for entry in entries:
        by_layer[module_layer(entry["module"])][entry["module"].rsplit(".", 1)[-1]] = entry

    # A language decoder block has seven packed Linear modules.  The source
    # audit must enumerate all of them; accepting only the QKV and Gate/Up
    # fusion groups would silently omit attention output and MLP down paths
    # from a prospective full-model descriptor table.
    families = {
        "qkv": ("self_attn", ("q_proj", "k_proj", "v_proj")),
        "attention_out": ("self_attn", ("o_proj",)),
        "gate_up": ("mlp", ("gate_proj", "up_proj")),
        "mlp_down": ("mlp", ("down_proj",)),
    }
    groups = {key: [] for key in families}
    missing = {key: [] for key in families}
    for layer in range(36):
        for family, (block, projections) in families.items():
            selected = []
            for projection in projections:
                full_name = f"model.language_model.layers.{layer}.{block}.{projection}"
                entry = next((candidate for candidate in entries if candidate["module"] == full_name), None)
                if entry is None:
                    missing[family].append({"layer": layer, "projection": projection})
                else:
                    selected.append(entry)
            if len(selected) == len(projections):
                groups[family].append(
                    {
                        "layer": layer,
                        "projection_count": len(selected),
                        "activation_reuse": 1,
                        "descriptors": [
                            {
                                "module": entry["module"],
                                "bits": int(entry["bits"]),
                                "group_size": int(entry["group_size"]),
                                "shape": entry["shape"],
                                "padded_columns": int(entry["padded_columns"]),
                                "codes": section_descriptor(entry, "codes"),
                                "scales": section_descriptor(entry, "scales"),
                                "orientations": section_descriptor(entry, "orientations"),
                            }
                            for entry in selected
                        ],
                    }
                )
    return {"groups": groups, "missing": missing}


def audit_section_ranges(entries: list[dict], blob_bytes: int) -> dict:
    """Prove every descriptor range is in the hash-verified blob and disjoint."""
    intervals: list[tuple[int, int, str]] = []
    invalid: list[dict] = []
    for entry in entries:
        for field in ("codes", "scales", "orientations"):
            section = entry["sections"][field]
            offset = int(section["offset"])
            size = int(section["bytes"])
            end = offset + size
            if offset < 0 or size <= 0 or end > blob_bytes:
                invalid.append(
                    {"module": entry["module"], "field": field, "offset": offset, "bytes": size, "end": end}
                )
            else:
                intervals.append((offset, end, f"{entry['module']}:{field}"))
    intervals.sort()
    overlaps = []
    for previous, current in zip(intervals, intervals[1:]):
        if current[0] < previous[1]:
            overlaps.append({"first": previous[2], "second": current[2], "first_end": previous[1], "second_offset": current[0]})
    return {
        "section_count": len(intervals),
        "invalid_ranges": invalid,
        "overlaps": overlaps,
        "all_ranges_within_blob": not invalid,
        "ranges_disjoint": not overlaps,
    }

def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    arguments = parser.parse_args()

    manifest_path = arguments.manifest.resolve()
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    language = [
        entry
        for entry in manifest.get("entries", [])
        if entry.get("kind") == "packed" and entry.get("module", "").startswith(LANGUAGE_PREFIX)
    ]
    source_blob = manifest.get("blob", {}).get("sha256")
    blob_bytes = int(manifest.get("blob", {}).get("bytes", 0))
    descriptor_data = build_groups(language)
    section_audit = audit_section_ranges(language, blob_bytes)
    descriptor_linear_count = sum(
        len(group["descriptors"])
        for family_groups in descriptor_data["groups"].values()
        for group in family_groups
    )
    bit_width_counts: dict[str, int] = defaultdict(int)
    for entry in language:
        bit_width_counts[str(int(entry["bits"]))] += 1

    checks = {
        "blob_hash_matches_m56": source_blob == EXPECTED_M56_BLOB_SHA256,
        "language_packed_count_matches_m56": len(language) == EXPECTED_LANGUAGE_PACKED,
        "qkv_groups_complete": len(descriptor_data["groups"]["qkv"]) == 36,
        "attention_out_groups_complete": len(descriptor_data["groups"]["attention_out"]) == 36,
        "gate_up_groups_complete": len(descriptor_data["groups"]["gate_up"]) == 36,
        "mlp_down_groups_complete": len(descriptor_data["groups"]["mlp_down"]) == 36,
        "all_language_linears_covered": descriptor_linear_count == EXPECTED_LANGUAGE_PACKED,
        "all_descriptor_ranges_within_blob": section_audit["all_ranges_within_blob"],
        "descriptor_ranges_disjoint": section_audit["ranges_disjoint"],
    }
    accepted = all(checks.values())
    result = {
        "build": "M89-A",
        "scope": "offline-only fail-closed descriptor source audit",
        "manifest": {"path": str(manifest_path), "sha256": sha256(manifest_path), "blob_sha256": source_blob},
        "expected": {"m56_blob_sha256": EXPECTED_M56_BLOB_SHA256, "language_packed_count": EXPECTED_LANGUAGE_PACKED},
        "observed": {
            "language_packed_count": len(language),
            "descriptor_linear_count": descriptor_linear_count,
            "bit_width_counts": dict(sorted(bit_width_counts.items())),
            "section_ranges": section_audit,
            "qkv_group_count": len(descriptor_data["groups"]["qkv"]),
            "attention_out_group_count": len(descriptor_data["groups"]["attention_out"]),
            "gate_up_group_count": len(descriptor_data["groups"]["gate_up"]),
            "mlp_down_group_count": len(descriptor_data["groups"]["mlp_down"]),
            "missing": descriptor_data["missing"],
        },
        "checks": checks,
        "status": "PASS_FULL_M56_DESCRIPTOR_SOURCE" if accepted else "REJECTED_STALE_OR_INCOMPLETE_DESCRIPTOR_SOURCE",
        "board_safety": "offline manifest analysis only; no HLS export, bitstream, board, UART, microSD, boot, DTB, CMA or service action",
    }
    if accepted:
        result["descriptor_groups"] = descriptor_data["groups"]
        result["next_gate"] = "M89-B exact CSim for a bounded three-descriptor destination-local accumulator."
    else:
        result["next_gate"] = "Supply the hash-matched M56 manifest; do not use this input to produce an HLS or board candidate."

    arguments.output.parent.mkdir(parents=True, exist_ok=True)
    arguments.output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(result["status"])


if __name__ == "__main__":
    main()
