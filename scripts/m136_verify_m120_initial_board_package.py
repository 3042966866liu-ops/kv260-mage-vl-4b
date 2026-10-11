#!/usr/bin/env python3
"""Fail-closed independent verifier for the M136 initial board package."""

from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path


# This verifier imports a packaged fixture module.  Never let the verification
# itself mutate the hash-locked candidate with __pycache__/pyc files.
sys.dont_write_bytecode = True


ROOT = Path(__file__).resolve().parents[1]
PACKAGE = ROOT / "deployment/mage_vl4b/m120_text4b_board_candidate"
RESULT = ROOT / "deployment/mage_vl4b/M136_M120_INITIAL_BOARD_PACKAGE_RESULT.json"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(16 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def require(condition: bool, message: str) -> None:
    if not condition:
        raise RuntimeError(message)


def main() -> int:
    manifest_path = PACKAGE / "PACKAGE_MANIFEST.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    require(manifest.get("status") == "PASS_OFFLINE_INITIAL_BOARD_GATE_PACKAGE", "status")
    require(manifest.get("allowed_gate_order") == ["build-id", "single-descriptor", "single-chain"], "order")
    expected = {item["path"]: item for item in manifest["files"]}
    observed = {
        path.relative_to(PACKAGE).as_posix(): path
        for path in PACKAGE.rglob("*")
        if path.is_file() and path.name != "PACKAGE_MANIFEST.json"
    }
    require(set(observed) == set(expected), "path whitelist mismatch")
    require(not any("__pycache__" in path.parts or path.suffix == ".pyc" for path in observed.values()), "cache")
    for relative, path in observed.items():
        item = expected[relative]
        require(path.stat().st_size == int(item["bytes"]), f"size {relative}")
        require(sha256(path) == item["sha256"], f"hash {relative}")
    require(sum(path.stat().st_size for path in observed.values()) == int(manifest["total_bytes"]), "bytes")
    require(len(observed) == int(manifest["file_count"]) == 19, "file count")

    for relative in sorted(name for name in observed if name.endswith(".py")):
        source = observed[relative].read_text(encoding="utf-8")
        compile(source, relative, "exec")
    runner = observed["runtime/run_m120_gate.sh"].read_text(encoding="utf-8")
    for token in (
        "set -euo pipefail", "m120_board_env_preflight.py", "m120_build_id_gate.py",
        "m120_fixture_gate.py", "build-id|single-descriptor|single-chain",
    ):
        require(token in runner, f"runner token {token}")

    sys.path.insert(0, str(PACKAGE / "runtime"))
    from m120_fixture import build_case, load_fixture

    fixture = PACKAGE / "reference/m128_m120_real_record_csim_fixture.bin"
    fixture_result = json.loads((PACKAGE / "contracts/M128_M120_CSIM_FIXTURE_RESULT.json").read_text(encoding="utf-8"))
    require(sha256(fixture) == fixture_result["fixture_sha256"], "fixture identity")
    cases = load_fixture(fixture)
    require(len(cases) == 7, "fixture cases")
    single = build_case(cases[0], 1)
    chain = build_case(cases[0], len(cases[0].descriptors))
    require(sha256_bytes(single["expected"]) == "28bf653102885387d67be746eb1b417c999fe128d7c95af6bbc7635af0768350", "descriptor reference")
    require(sha256_bytes(chain["expected"]) == "c03f51cc7cd6d157e04bd0da674ee59652168b58473d6d3b2070f58fe30ec3a0", "chain reference")

    result = {
        "date": "2026-09-01",
        "gate": "M136-M120-initial-board-package-verification",
        "status": "PASS",
        "classification": "offline package, syntax, fixture and reference verification; board not yet run",
        "package_manifest_sha256": sha256(manifest_path),
        "file_count": len(observed),
        "total_bytes": int(manifest["total_bytes"]),
        "fixture_sha256": sha256(fixture),
        "single_descriptor_expected_sha256": sha256_bytes(single["expected"]),
        "single_chain_expected_sha256": sha256_bytes(chain["expected"]),
        "board_state_changed": False,
        "next_gate": "COM3 Build-ID gate only; do not run the single-descriptor gate before it passes.",
    }
    RESULT.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print("M136_M120_INITIAL_BOARD_PACKAGE_VERIFY_PASS")
    print(json.dumps(result, indent=2))
    return 0


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


if __name__ == "__main__":
    raise SystemExit(main())
