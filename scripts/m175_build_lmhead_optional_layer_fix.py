#!/usr/bin/env python3
"""Build a clean M120 text candidate fixing null LM-head layer bookkeeping."""

from __future__ import annotations

import hashlib
import json
import os
import py_compile
import shutil
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "deployment/mage_vl4b/m165_m120_layer0_board_candidate"
OUTPUT = ROOT / "deployment/mage_vl4b/m175_m120_fixed_text_candidate"
RESULT = ROOT / "deployment/mage_vl4b/M175_M120_LMHEAD_OPTIONAL_LAYER_FIX_RESULT.json"
M168_LOG = ROOT / "tmp/m168_fixed_text/run_01_uart.log"
SOURCE_PACKAGE_SHA = "34662ca90cb45b9a1d34903538b030f28b1f9f70ece3f35e7ccbbaf6eb3bbf97"
OLD_OPTIONAL_LAYER = '"layer": int(chain["layer"]) if "layer" in chain else None,'
NEW_OPTIONAL_LAYER = '"layer": int(chain["layer"]) if chain.get("layer") is not None else None,'


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def atomic_json(path: Path, value: dict) -> None:
    temporary = path.with_name(path.name + f".partial-{os.getpid()}")
    temporary.write_text(json.dumps(value, indent=2) + "\n", encoding="utf-8")
    os.replace(temporary, path)


def verify_source() -> tuple[dict, dict]:
    package_path = SOURCE / "PACKAGE_MANIFEST.json"
    if digest(package_path) != SOURCE_PACKAGE_SHA:
        raise RuntimeError("M175 source package-manifest identity mismatch")
    package = json.loads(package_path.read_text(encoding="utf-8"))
    declared = {item["path"] for item in package["files"]}
    actual = {
        path.relative_to(SOURCE).as_posix()
        for path in SOURCE.rglob("*")
        if path.is_file() and path.name != "PACKAGE_MANIFEST.json"
    }
    if actual != declared:
        raise RuntimeError(f"M175 source closure mismatch missing={sorted(declared-actual)} extra={sorted(actual-declared)}")
    for item in package["files"]:
        path = SOURCE / item["path"]
        if path.stat().st_size != item["bytes"] or digest(path) != item["sha256"]:
            raise RuntimeError(f"M175 source member mismatch: {item['path']}")
    source_manifest = json.loads((SOURCE / "SOURCE_MANIFEST.json").read_text(encoding="utf-8"))
    return package, source_manifest


def main() -> int:
    if OUTPUT.exists() or RESULT.exists():
        raise RuntimeError("M175 output already exists")
    source_package, source_manifest = verify_source()
    log_text = M168_LOG.read_text(encoding="utf-8", errors="replace")
    for marker in (
        "M136_M120_BOARD_ENV_PASS",
        "M168_M167_LAYER0_PREDECESSOR_PASS",
        "TypeError: int() argument must be a string, a bytes-like object or a real number, not 'NoneType'",
        "M120_FIXED_TEXT_E2E_FAIL",
    ):
        if marker not in log_text:
            raise RuntimeError(f"M175 M168 failure marker missing: {marker}")

    head_contract = json.loads((SOURCE / "contracts/M126_LMHEAD_RUNTIME_CONTRACT_RESULT.json").read_text(encoding="utf-8"))
    head_chains = head_contract["chains"]
    if len(head_chains) != 8 or any(chain.get("family") != "lm_head" or chain.get("layer") is not None for chain in head_chains):
        raise RuntimeError("M175 LM-head null-layer contract diagnosis mismatch")

    temporary = OUTPUT.with_name(OUTPUT.name + f".partial-{os.getpid()}")
    if temporary.exists():
        raise RuntimeError("M175 partial output exists")
    shutil.copytree(SOURCE, temporary, ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
    try:
        board_runtime = temporary / "runtime/board_runtime.py"
        runtime_text = board_runtime.read_text(encoding="utf-8")
        if runtime_text.count(OLD_OPTIONAL_LAYER) != 2 or NEW_OPTIONAL_LAYER in runtime_text:
            raise RuntimeError("M175 optional-layer patch precondition mismatch")
        runtime_text = runtime_text.replace(OLD_OPTIONAL_LAYER, NEW_OPTIONAL_LAYER)
        board_runtime.write_text(runtime_text, encoding="utf-8")

        text_gate = temporary / "runtime/text_e2e_gate.py"
        gate_text = text_gate.read_text(encoding="utf-8")
        if "import traceback\n" in gate_text:
            raise RuntimeError("M175 traceback import already present")
        gate_text = gate_text.replace("import time\n", "import time\nimport traceback\n", 1)
        old_except = '''    except Exception as exc:\n        result["error"] = f"{type(exc).__name__}: {exc}"\n        result["total_ms"] = (time.monotonic() - started) * 1000.0\n'''
        new_except = '''    except Exception as exc:\n        result["error"] = f"{type(exc).__name__}: {exc}"\n        result["cpu_linear_fallback"] = False\n        if runtime is not None:\n            result["partial_evidence"] = runtime.evidence()\n        result["traceback"] = traceback.format_exc()\n        result["total_ms"] = (time.monotonic() - started) * 1000.0\n'''
        if gate_text.count(old_except) != 1:
            raise RuntimeError("M175 exception-evidence patch precondition mismatch")
        text_gate.write_text(gate_text.replace(old_except, new_except), encoding="utf-8")

        for path in (board_runtime, text_gate):
            py_compile.compile(str(path), doraise=True, cfile=str(temporary / (path.name + ".compile-test.pyc")))
            (temporary / (path.name + ".compile-test.pyc")).unlink()
        corrected = board_runtime.read_text(encoding="utf-8")
        if OLD_OPTIONAL_LAYER in corrected or corrected.count(NEW_OPTIONAL_LAYER) != 2:
            raise RuntimeError("M175 optional-layer patch verification failed")

        source_manifest["gate"] = "M175-M120-fixed-text-runtime-source"
        source_manifest["status"] = "SOURCE_CORRECTED_NOT_BOARD_EXECUTED"
        source_manifest["m168_failure"] = {
            "classification": "host bookkeeping defect after an LM-head FPGA transaction",
            "uart_log": M168_LOG.relative_to(ROOT).as_posix(),
            "uart_log_sha256": digest(M168_LOG),
            "head_chain_count": 8,
            "head_layer_field": None,
        }
        source_manifest["host_runtime_fix"] = {
            "optional_layer_conversion": "convert chain.layer to int only when non-null",
            "patched_occurrences": 2,
            "failure_evidence_includes_traceback_and_partial_runtime_counters": True,
            "fpga_arithmetic_changed": False,
            "contracts_changed": False,
            "weights_changed": False,
        }
        source_entries = {item["path"]: item for item in source_manifest["files"]}
        for relative, label in (
            ("runtime/board_runtime.py", "M175 null-safe LM-head layer bookkeeping"),
            ("runtime/text_e2e_gate.py", "M175 fail-closed traceback and partial-evidence retention"),
        ):
            path = temporary / relative
            entry = source_entries[relative]
            entry.update({"bytes": path.stat().st_size, "sha256": digest(path), "source": label})
        atomic_json(temporary / "SOURCE_MANIFEST.json", source_manifest)

        package = dict(source_package)
        package["gate"] = "M175-M120-fixed-text-board-package"
        package["status"] = "OFFLINE_PACKAGE_PASS_BOARD_NOT_EXECUTED"
        package["source_package_manifest_sha256"] = SOURCE_PACKAGE_SHA
        package["source_manifest_sha256"] = digest(temporary / "SOURCE_MANIFEST.json")
        package["m168_failure_uart_sha256"] = digest(M168_LOG)
        package["host_runtime_fix"] = source_manifest["host_runtime_fix"]
        package["video_runtime_must_inherit_fix"] = True
        for item in package["files"]:
            path = temporary / item["path"]
            item["bytes"] = path.stat().st_size
            item["sha256"] = digest(path)
        atomic_json(temporary / "PACKAGE_MANIFEST.json", package)

        declared = {item["path"] for item in package["files"]} | {"PACKAGE_MANIFEST.json"}
        actual = {path.relative_to(temporary).as_posix() for path in temporary.rglob("*") if path.is_file()}
        if actual != declared:
            raise RuntimeError(f"M175 output closure mismatch missing={sorted(declared-actual)} extra={sorted(actual-declared)}")
        for item in package["files"]:
            path = temporary / item["path"]
            if path.stat().st_size != item["bytes"] or digest(path) != item["sha256"]:
                raise RuntimeError(f"M175 output member mismatch: {item['path']}")
        os.replace(temporary, OUTPUT)
    except Exception:
        if temporary.exists():
            shutil.rmtree(temporary)
        raise

    package_path = OUTPUT / "PACKAGE_MANIFEST.json"
    result = {
        "date": "2026-09-01",
        "gate": "M175-M120-LMHead-optional-layer-host-fix",
        "status": "PASS",
        "classification": "Offline clean package and host-runtime regression only; not board E2E, performance, video or Web evidence.",
        "candidate_build_id": "0x4D395832",
        "source_package_manifest_sha256": SOURCE_PACKAGE_SHA,
        "package_manifest_sha256": digest(package_path),
        "directory": OUTPUT.relative_to(ROOT).as_posix(),
        "file_count": len(json.loads(package_path.read_text(encoding="utf-8"))["files"]),
        "m168_failure_uart": M168_LOG.relative_to(ROOT).as_posix(),
        "m168_failure_uart_sha256": digest(M168_LOG),
        "diagnosis": {
            "lm_head_chain_count": 8,
            "lm_head_layer_field": None,
            "unsafe_optional_layer_conversion_occurrences_before": 2,
            "unsafe_optional_layer_conversion_occurrences_after": 0,
        },
        "changes": ["runtime/board_runtime.py", "runtime/text_e2e_gate.py", "SOURCE_MANIFEST.json", "PACKAGE_MANIFEST.json"],
        "fpga_arithmetic_changed": False,
        "contracts_changed": False,
        "weights_changed": False,
        "boot_dtb_cma_partitions_services_changed": False,
        "stable_rollback_preserved": True,
        "video_runtime_must_inherit_fix": True,
        "next_gate": "Stage this exact package delta over COM3 and rerun only fixed-text E2E.",
    }
    atomic_json(RESULT, result)
    print(json.dumps(result, indent=2))
    print("M175_LMHEAD_OPTIONAL_LAYER_FIX_PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
