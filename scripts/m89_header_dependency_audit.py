#!/usr/bin/env python3
"""Fail-closed local include audit for the M89-X board candidate.

This gate exists because a CSim can pass from the development tree even when
the staged source package is missing a required .h/.hpp file.  It resolves the
complete quoted-include closure, requires the public kernel header, hashes every
dependency, and can copy the exact closure into a self-contained staging tree.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
from pathlib import Path


INCLUDE_RE = re.compile(r'^\s*#\s*include\s*"([^"]+)"', re.MULTILINE)
DEFAULT_ENTRIES = (
    "hls/mage_prefill_m89x_runtime/mage_prefill_m89x_runtime.cpp",
    "hls/mage_prefill_m89x_runtime/mage_prefill_m89x_runtime.hpp",
    "hls/mage_prefill_m89x_runtime/tb_m89x_w3_lmhead.cpp",
    "hls/mage_prefill_m89x_runtime/tb_m89x_w4_lifted_lmhead.cpp",
    "hls/mage_prefill_m89x_runtime/tb_m89x_w2w4_regression.cpp",
    "hls/mage_prefill_m89x_runtime/tb_mage_prefill_m89x_runtime.cpp",
)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def relative_to_workspace(path: Path, workspace: Path) -> str:
    try:
        return path.relative_to(workspace).as_posix()
    except ValueError as exc:
        raise RuntimeError(f"dependency escapes workspace: {path}") from exc


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--workspace", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--result", type=Path)
    parser.add_argument("--stage", type=Path)
    parser.add_argument("--entry", action="append", default=[])
    args = parser.parse_args()

    workspace = args.workspace.resolve()
    result_path = (args.result or workspace / "deployment/mage_vl4b/M89_HEADER_DEPENDENCY_AUDIT_RESULT.json").resolve()
    entries = tuple(args.entry) or DEFAULT_ENTRIES
    public_header = (workspace / "hls/mage_prefill_m89x_runtime/mage_prefill_m89x_runtime.hpp").resolve()

    queue = [(workspace / item).resolve() for item in entries]
    visited: set[Path] = set()
    edges: list[dict[str, str]] = []
    missing: list[dict[str, str]] = []

    while queue:
        source = queue.pop(0)
        if source in visited:
            continue
        if not source.is_file():
            missing.append({"included_by": "<entry>", "include": relative_to_workspace(source, workspace)})
            continue
        relative_to_workspace(source, workspace)
        visited.add(source)
        text = source.read_text(encoding="utf-8", errors="strict")
        for include in INCLUDE_RE.findall(text):
            target = (source.parent / include).resolve()
            edge = {
                "included_by": relative_to_workspace(source, workspace),
                "include": include,
                "resolved": relative_to_workspace(target, workspace),
            }
            edges.append(edge)
            if not target.is_file():
                missing.append(edge)
            elif target not in visited:
                queue.append(target)

    implementation = (workspace / DEFAULT_ENTRIES[0]).read_text(encoding="utf-8")
    public_header_used = '#include "mage_prefill_m89x_runtime.hpp"' in implementation
    header_in_closure = public_header in visited
    headers = sorted(
        relative_to_workspace(path, workspace)
        for path in visited
        if path.suffix.lower() in {".h", ".hh", ".hpp", ".hxx"}
    )

    staged_files: list[str] = []
    if args.stage is not None and not missing and public_header_used and header_in_closure:
        stage = args.stage.resolve()
        stage.mkdir(parents=True, exist_ok=True)
        for source in sorted(visited):
            relative = Path(relative_to_workspace(source, workspace))
            destination = stage / relative
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, destination)
            if sha256(source) != sha256(destination):
                raise RuntimeError(f"staged hash mismatch: {relative.as_posix()}")
            staged_files.append(relative.as_posix())

    passed = not missing and public_header_used and header_in_closure and bool(headers)
    payload = {
        "build": "M89-X-header-dependency-audit-v1",
        "status": "PASS" if passed else "FAIL",
        "marker": "M89_HEADER_DEPENDENCY_AUDIT_PASS" if passed else "M89_HEADER_DEPENDENCY_AUDIT_FAIL",
        "workspace": str(workspace),
        "entries": list(entries),
        "public_header": relative_to_workspace(public_header, workspace),
        "public_header_used_by_implementation": public_header_used,
        "public_header_in_dependency_closure": header_in_closure,
        "dependency_count": len(visited),
        "header_count": len(headers),
        "headers": headers,
        "missing": missing,
        "edges": edges,
        "files": [
            {
                "path": relative_to_workspace(path, workspace),
                "bytes": path.stat().st_size,
                "sha256": sha256(path),
            }
            for path in sorted(visited)
        ],
        "staged_files": staged_files,
        "board_state_changed": False,
    }
    result_path.parent.mkdir(parents=True, exist_ok=True)
    result_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(payload["marker"])
    print(f"dependencies={len(visited)} headers={len(headers)} missing={len(missing)}")
    print(f"result={result_path}")
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
