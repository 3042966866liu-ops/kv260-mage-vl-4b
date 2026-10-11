#!/usr/bin/env python3
"""Fail-closed quoted-include closure audit for the isolated M230 T64 kernel."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
from pathlib import Path


INCLUDE_RE = re.compile(r'^\s*#\s*include\s*"([^"]+)"', re.MULTILINE)
DEFAULT_ENTRIES = (
    "hls/mage_prefill_m230_t64_reuse/mage_prefill_m230_t64_reuse.cpp",
    "hls/mage_prefill_m230_t64_reuse/mage_prefill_m230_t64_reuse.hpp",
    "hls/mage_prefill_m230_t64_reuse/tb_m230_t64_numerical.cpp",
)
PUBLIC_HEADER = "hls/mage_prefill_m230_t64_reuse/mage_prefill_m230_t64_reuse.hpp"
IMPLEMENTATION = "hls/mage_prefill_m230_t64_reuse/mage_prefill_m230_t64_reuse.cpp"


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
    parser.add_argument("--public-header", default=PUBLIC_HEADER)
    parser.add_argument("--implementation", default=IMPLEMENTATION)
    parser.add_argument("--build", default="M230-T64-header-dependency-audit-v1")
    parser.add_argument("--marker-prefix", default="M230_T64_HEADER_DEPENDENCY_AUDIT")
    args = parser.parse_args()

    workspace = args.workspace.resolve()
    result_path = (args.result or workspace / "deployment/mage_vl4b/M230_T64_HEADER_DEPENDENCY_AUDIT_RESULT.json").resolve()
    entries = tuple(args.entry) or DEFAULT_ENTRIES
    public_header = (workspace / args.public_header).resolve()

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

    implementation = (workspace / args.implementation).resolve()
    implementation_text = implementation.read_text(encoding="utf-8")
    public_header_used = f'#include "{Path(args.public_header).name}"' in implementation_text
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
        "build": args.build,
        "status": "PASS" if passed else "FAIL",
        "marker": f"{args.marker_prefix}_{'PASS' if passed else 'FAIL'}",
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
