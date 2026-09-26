#!/usr/bin/env python3
"""Small no-board release check. Use --write-manifest after all edits."""

from __future__ import annotations

import argparse
import ast
import hashlib
import json
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[1]
SOURCE_ROOT = ROOT.parents[1]
MANIFEST = ROOT / "manifests/release_files.json"
EXCLUDE = {"manifests/release_files.json", "RELEASE_READINESS.md", "reports/backups/RELEASE_READINESS_2026-09-26.md", "reports/backups/STABLE_ASSET_PROVENANCE_2026-09-26.md", "manifests/check_result.json"}
TEXT_EXT = {".md", ".py", ".json", ".sh", ".ps1", ".tcl", ".cpp", ".hpp", ".h", ".html", ".js", ".css", ".yml", ".yaml", ".txt", ".xdc"}


def sha(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for part in iter(lambda: f.read(4 << 20), b""):
            h.update(part)
    return h.hexdigest()


def files() -> list[Path]:
    result = []
    for p in ROOT.rglob("*"):
        if not p.is_file():
            continue
        rel = p.relative_to(ROOT).as_posix()
        if rel in EXCLUDE or rel.startswith("external_assets/") or "__pycache__" in p.parts or p.suffix == ".pyc" or ".git" in p.parts:
            continue
        result.append(p)
    return sorted(result)


def entry(p: Path) -> dict:
    rel = p.relative_to(ROOT).as_posix()
    origin = SOURCE_ROOT / ("scripts/" + p.name if rel.startswith("model_tools/") and p.suffix == ".py" else rel)
    copied = origin.is_file() and sha(origin) == sha(p)
    family = ("experimental" if "OP01" in rel or "decode_op01" in rel or "m325" in rel.lower()
              else "bact" if rel.startswith(("bact/", "data/bact", "experiments/bact")) or "m277_m276" in rel or "m321_" in rel
              else "stable" if rel.startswith(("deployment/mage_vl4b/m", "hls/mage_prefill", "tmp/", "model_tools/"))
              else "support")
    purpose = ("HLS design, test or Tcl" if rel.startswith("hls/")
               else "historical result or runtime contract" if p.suffix == ".json" and rel.startswith(("deployment/", "data/", "experiments/"))
               else "runtime or research source" if p.suffix in (".py", ".sh", ".cpp", ".hpp", ".h", ".tcl")
               else "Web static asset" if p.suffix in (".js", ".html", ".css")
               else "release documentation or configuration")
    return {"path": rel, "type": p.suffix.lower().lstrip(".") or "text", "purpose": purpose,
            "bytes": p.stat().st_size, "sha256": sha(p),
            "origin_path": origin.relative_to(SOURCE_ROOT).as_posix() if copied else None,
            "origin_sha256": sha(origin) if copied else None,
            "change": "byte-identical copy" if copied else "release-only file or adapted copy", "entry": family}


def markdown_links(path: Path) -> list[str]:
    text = path.read_text(encoding="utf-8")
    issues = []
    for target in re.findall(r"\]\(([^)]+)\)", text):
        target = target.split("#", 1)[0]
        if not target or "://" in target or target.startswith(("mailto:", "#", "/")):
            continue
        if not (path.parent / target).exists():
            issues.append(f"broken link: {path.relative_to(ROOT)} -> {target}")
    return issues


def check() -> dict:
    problems = []
    inventory = files()
    for p in inventory:
        rel = p.relative_to(ROOT).as_posix()
        if p.is_symlink():
            problems.append("symlink: " + rel)
        if p.suffix == ".py":
            try:
                ast.parse(p.read_text(encoding="utf-8"), filename=rel)
            except (SyntaxError, UnicodeError) as exc:
                problems.append(f"Python syntax: {rel}: {exc}")
        if p.suffix == ".json":
            try:
                json.loads(p.read_text(encoding="utf-8"))
            except (ValueError, UnicodeError) as exc:
                problems.append(f"JSON parse: {rel}: {exc}")
        if p.suffix == ".md":
            problems.extend(markdown_links(p))
        if p.suffix in TEXT_EXT and p.stat().st_size < 2_000_000:
            text = p.read_text(encoding="utf-8", errors="replace")
            if re.search(r"(?i)(?:ghp_|github_pat_|sk-proj-|AKIA)[A-Za-z0-9_-]{12,}", text):
                problems.append("possible credential (content omitted): " + rel)
    if not MANIFEST.is_file():
        problems.append("missing release manifest")
    else:
        listed = json.loads(MANIFEST.read_text(encoding="utf-8"))
        by_path = {x["path"]: x for x in listed["files"]}
        for p in inventory:
            rel = p.relative_to(ROOT).as_posix()
            if rel not in by_path:
                problems.append("not manifested: " + rel)
            elif by_path[rel]["sha256"] != sha(p):
                problems.append("manifest hash drift: " + rel)
        for rel in by_path:
            if not (ROOT / rel).is_file():
                problems.append("manifest missing file: " + rel)
    return {"status": "PASS" if not problems else "FAIL", "files_checked": len(inventory), "problems": problems,
            "board_execution_run": False}


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--write-manifest", action="store_true")
    args = p.parse_args()
    if args.write_manifest:
        MANIFEST.parent.mkdir(parents=True, exist_ok=True)
        result = {"schema": "kv260-mage-vl-release-files-v1", "self_excluded": sorted(EXCLUDE),
                  "files": [entry(x) for x in files()]}
        MANIFEST.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    result = check()
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["status"] == "PASS" else 1


if __name__ == "__main__":
    sys.exit(main())
