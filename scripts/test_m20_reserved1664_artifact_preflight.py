#!/usr/bin/env python3
"""Positive and tamper-negative tests for the M20 artifact lock."""

from __future__ import annotations

import importlib.util
import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CANDIDATE = ROOT / "deployment/qwen25_3b_directddr_chain"
STABLE = ROOT / "deployment/qwen25_3b_no_final_forward"
PREFLIGHT = CANDIDATE / "runtime/m20_reserved1664_artifact_preflight.py"
FULL_GATE = CANDIDATE / "run_reserved1664_m20_full_gate.sh"
SOURCE_OVERRIDES = {
    ("candidate", "overlay/qwen25_decode_directddr_chain.bit"): CANDIDATE
    / "overlay_highddr/qwen25_decode_directddr_chain_highddr.bit",
    ("candidate", "overlay/qwen25_decode_directddr_chain.hwh"): CANDIDATE
    / "overlay_highddr/qwen25_decode_directddr_chain_highddr.hwh",
    ("candidate", "overlay/qwen25_shared_l40.bit"): CANDIDATE
    / "overlay_highddr_prefill/qwen25_shared_l40_highddr.bit",
    ("candidate", "overlay/qwen25_shared_l40.hwh"): CANDIDATE
    / "overlay_highddr_prefill/qwen25_shared_l40_highddr.hwh",
    ("stable", "runtime/prefill_native.cpython-310-aarch64-linux-gnu.so"): CANDIDATE
    / "board_stable_prefill_native.cpython-310-aarch64-linux-gnu.so",
}


def load_preflight():
    spec = importlib.util.spec_from_file_location("m20_reserved1664_artifact_preflight", PREFLIGHT)
    if spec is None or spec.loader is None:
        raise RuntimeError("unable to load artifact preflight")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def invoke(candidate: Path, stable: Path, result: Path) -> tuple[int, dict]:
    completed = subprocess.run(
        [
            sys.executable,
            str(PREFLIGHT),
            "--candidate-root",
            str(candidate),
            "--stable-root",
            str(stable),
            "--result",
            str(result),
        ],
        check=False,
        stdout=subprocess.DEVNULL,
    )
    return completed.returncode, json.loads(result.read_text())


def copy_manifest_tree(module, candidate: Path, stable: Path) -> None:
    roots = {"candidate": (CANDIDATE, candidate), "stable": (STABLE, stable)}
    for scope, manifest in module.EXPECTED.items():
        source_root, target_root = roots[scope]
        for relative in manifest:
            target = target_root / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            source = SOURCE_OVERRIDES.get((scope, relative), source_root / relative)
            shutil.copy2(source, target)


def main() -> int:
    module = load_preflight()
    gate_source = FULL_GATE.read_text()
    insmod_index = gate_source.index('insmod "$MODULE"')
    identity_index = gate_source.index('"$ROOT/runtime/board_model_identity_preflight.py"')
    reclaim_index = gate_source.index("current_stage=post_identity_cma_reclaim")
    assert gate_source.index("reserved1664_artifact_preflight.py") < insmod_index
    assert identity_index < reclaim_index < insmod_index
    assert 'echo 3 > /proc/sys/vm/drop_caches' in gate_source
    assert 'cma_reclaim_minimum_kib=716800' in gate_source
    with tempfile.TemporaryDirectory(prefix="tellme-artifact-lock-") as raw:
        directory = Path(raw)
        candidate = directory / "candidate"
        stable = directory / "stable"
        copy_manifest_tree(module, candidate, stable)
        pass_rc, passed = invoke(candidate, stable, directory / "pass.json")
        assert pass_rc == 0 and passed["status"] == "PASS"
        assert passed["artifact_count"] == 23
        assert passed["milestone"] == "M20"
        assert passed["pre_hardware_action"] is True

        tampered = candidate / "runtime/chain_common.py"
        tampered.write_bytes(tampered.read_bytes() + b"\n# fault injection\n")
        fail_rc, failed = invoke(candidate, stable, directory / "fail.json")
        assert fail_rc == 1 and failed["status"] == "FAIL"
        assert failed["failed_artifacts"] == ["candidate:runtime/chain_common.py"]
    print("QWEN_M20_RESERVED1664_ARTIFACT_PREFLIGHT_UNIT_PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
