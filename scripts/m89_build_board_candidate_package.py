#!/usr/bin/env python3
"""Build a fail-closed, not-deployed M89-X board-candidate bundle."""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
from pathlib import Path


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(8 << 20), b""):
            h.update(block)
    return h.hexdigest()


def copy(source: Path, destination: Path) -> None:
    if not source.is_file():
        raise RuntimeError(f"required candidate file missing: {source}")
    destination.parent.mkdir(parents=True, exist_ok=True)
    # The full-shell collector already writes bit/hwh/XSA into the package.
    # Accept an identity copy only after resolving both paths; shutil.copy2
    # would otherwise raise SameFileError and turn a valid staged artifact into
    # a packaging retry.
    if source.resolve() != destination.resolve():
        shutil.copy2(source, destination)
    if sha256(source) != sha256(destination):
        raise RuntimeError(f"candidate copy hash mismatch: {destination}")


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--workspace", type=Path, default=Path(__file__).resolve().parents[1])
    p.add_argument("--overlay-bit", type=Path, required=True)
    p.add_argument("--overlay-hwh", type=Path, required=True)
    p.add_argument("--xsa", type=Path, required=True)
    p.add_argument("--implementation-result", type=Path, required=True)
    args = p.parse_args()
    root = args.workspace.resolve()
    package = root / "deployment/mage_vl4b/m89x_board_candidate"
    audit_path = root / "deployment/mage_vl4b/M89_HEADER_DEPENDENCY_AUDIT_RESULT.json"
    audit = json.loads(audit_path.read_text(encoding="utf-8"))
    if audit.get("status") != "PASS" or audit.get("missing") or int(audit.get("header_count", 0)) < 1:
        raise RuntimeError("header dependency audit is not passing")
    public_header = package / "source/hls/mage_prefill_m89x_runtime/mage_prefill_m89x_runtime.hpp"
    if not public_header.is_file():
        raise RuntimeError("staged public .hpp is missing")
    implementation = json.loads(args.implementation_result.read_text(encoding="utf-8"))
    if implementation.get("status") != "PASS_FULL_KV260_SHELL_IMPLEMENTATION":
        raise RuntimeError("full-shell implementation result is not passing")

    runtime_files = (
        "contract_runtime.py", "board_runtime.py", "single_chain_smoke.py", "single_chain_reference.py", "text_e2e_gate.py",
        "offline_contract_gate.py", "test_contract_runtime.py", "test_text_e2e_wiring.py",
        "test_wait_transaction.py", "board_env_preflight.py", "run_m89x1_minimal_gate.sh",
        "run_m89x1_single_chain_gate.sh",
        "support/reserved_ddr_pool.py",
    )
    for relative in runtime_files:
        source = root / "deployment/mage_vl4b/m89x_t32_runtime" / relative
        copy(source, package / "runtime" / relative)
        if source.suffix == ".py":
            compile(source.read_text(encoding="utf-8"), str(source), "exec")
    minimal_gate = root / "scripts/m89x_minimal_kernel_board_smoke.py"
    copy(minimal_gate, package / "runtime/m89x_minimal_kernel_board_smoke.py")
    compile(minimal_gate.read_text(encoding="utf-8"), str(minimal_gate), "exec")
    identity_gate = root / "scripts/m89x_verify_staged_board_candidate.py"
    copy(identity_gate, package / "runtime/m89x_verify_staged_board_candidate.py")
    compile(identity_gate.read_text(encoding="utf-8"), str(identity_gate), "exec")
    copy(root / "deployment/mage_vl4b/m89x_t32_runtime/layer0_qkv_reference.json",
         package / "reference/layer0_qkv_reference.json")
    contracts = (
        "M89X_MERGED_RUNTIME_CONTRACT_RESULT.json",
        "M89Z2_LMHEAD_RUNTIME_CONTRACT_RESULT.json",
        "M89X_ALL152_HOST_CONTRACT_RESULT.json",
        "M89_HEADER_DEPENDENCY_AUDIT_RESULT.json",
    )
    for filename in contracts:
        copy(root / "deployment/mage_vl4b" / filename, package / "contracts" / filename)
    copy(root / "deployment/mage_vl4b/artifacts/m89x_runtime_descriptor_table.bin",
         package / "contracts/m89x_runtime_descriptor_table.bin")
    copy(root / "deployment/mage_vl4b/artifacts/m89z2_lmhead_runtime_descriptor_table.bin",
         package / "contracts/m89z2_lmhead_runtime_descriptor_table.bin")
    copy(root / "artifacts/M77-mage-text-e2e/fixed_text_aux/m77_text_aux_fp16.npz",
         package / "auxiliary/m77_text_aux_fp16.npz")
    copy(root / "artifacts/M77-mage-text-e2e/fixed_text_aux/M77_TEXT_AUX_MANIFEST.json",
         package / "auxiliary/M77_TEXT_AUX_MANIFEST.json")
    copy(root / "artifacts/M77-mage-text-e2e/official_cpu_text_1token.json",
         package / "auxiliary/official_cpu_text_1token.json")
    copy(args.overlay_bit.resolve(), package / "overlay/m89x_t32.bit")
    copy(args.overlay_hwh.resolve(), package / "overlay/m89x_t32.hwh")
    copy(args.xsa.resolve(), package / "overlay/mage_m89x_t32_highddr.xsa")
    copy(args.implementation_result.resolve(), package / "contracts/M89X_FULL_SHELL_IMPLEMENTATION_RESULT.json")

    payloads = []
    for label, payload_root, expected_modules in (
        ("language", root / "deployment/mage_vl4b/artifacts/m89y_language_fourport", 252),
        ("lm_head", root / "deployment/mage_vl4b/artifacts/m89z2_lmhead_w4_fourport", 1),
    ):
        manifest = payload_root / "SIXPORT_LAYOUT_MANIFEST.json"
        content = json.loads(manifest.read_text(encoding="utf-8"))
        if int(content.get("module_count", -1)) != expected_modules:
            raise RuntimeError(f"large payload module count mismatch: {label}")
        for item in content["files"]:
            path = payload_root / item["path"]
            if path.stat().st_size != int(item["bytes"]) or sha256(path) != item["sha256"]:
                raise RuntimeError(f"large payload identity mismatch: {path}")
        payloads.append({"label": label, "workspace_path": str(payload_root),
                         "manifest_sha256": sha256(manifest),
                         "module_count": expected_modules,
                         "mapped_bytes": sum(int(item["bytes"]) for item in content["files"])})
    large_path = package / "LARGE_PAYLOADS.json"
    large_path.write_text(json.dumps({"status": "PASS_HASH_LOCKED_EXTERNAL_PAYLOADS",
                                      "payloads": payloads}, indent=2) + "\n", encoding="utf-8")

    readme = "# M89-X1 KV260 board candidate (NOT DEPLOYED)\n\n"
    readme += "This package is prepared for the first fixed 30-token/one-token Linux board gate. " \
              "It has not been loaded onto the KV260 and is not board-correctness or performance evidence.\n\n"
    readme += "The stable rollback must remain the default. Load `overlay/m89x_t32.bit` only in the authorized " \
              "one-shot gate; do not modify boot, DTB, SD partitions or CMA settings. Linux remains responsible " \
              "for networking/Web while the PL kernel executes all 252 language Linears and the untied LM head.\n\n"
    readme += "On the stable `cma=800M` boot, use `--weight-mode staged-low-cma`. The runtime stages one exact " \
              "four-shard chain window at a time, rewrites only the packet-local descriptor offset, and reuses " \
              "four bounded CMA buffers; it must not raw-map unreserved high DDR. The legacy " \
              "`resident-high-ddr` mode is accepted only when the verified reserved-memory device exists.\n\n"
    readme += "Before transfer, copy both hash-locked directories listed in `LARGE_PAYLOADS.json`. First run only " \
              "`runtime/run_m89x1_single_chain_gate.sh`, which compares real layer-0 QKV output to the packaged " \
              "independent reference. Only after that numeric gate passes may `runtime/text_e2e_gate.py` run. Web routing " \
              "remains prohibited until the generated token, build ID, 152 calls and macro totals all pass.\n\n"
    readme += "The source package includes the public `.hpp` and its full recursive dependency closure. Missing " \
              "headers are a hard package failure.\n"
    readme += "Every PYNQ board gate must run through `runtime/run_m89x1_minimal_gate.sh`, which fail-closes on " \
              "root authorization, `XILINX_XRT=/usr`, `TMPDIR=/dev/shm`, the PYNQ-venv `xclbinutil`, one XRT " \
              "device, one PYNQ device, and the exact package-manifest hash before it loads the overlay.\n"
    (package / "README.md").write_text(readme, encoding="utf-8")

    # A board candidate is an immutable payload, not a Python build tree.
    # Remove caches left by earlier local validation before hashing the package.
    for cache in sorted(package.rglob("__pycache__"), reverse=True):
        if cache.is_dir():
            shutil.rmtree(cache)

    files = []
    for path in sorted(p for p in package.rglob("*")
                       if p.is_file() and p.name != "PACKAGE_MANIFEST.json"
                       and "__pycache__" not in p.parts and p.suffix != ".pyc"):
        files.append({"path": path.relative_to(package).as_posix(), "bytes": path.stat().st_size,
                      "sha256": sha256(path)})
    result = {
        "date": "2026-08-31", "build": "M89-X1/Z2",
        "status": "PASS_OFFLINE_BOARD_CANDIDATE_PACKAGE",
        "marker": "M89X_OFFLINE_BOARD_CANDIDATE_PACKAGE_PASS",
        "deployed": False, "board_state_changed": False,
        "stable_rollback_required": True,
        "file_count": len(files), "headers": audit["headers"],
        "large_payloads": payloads, "files": files,
        "next_gate": "authorized one-shot layer-0 QKV numeric KV260 gate; no E2E or Web before exact pass",
    }
    manifest_path = package / "PACKAGE_MANIFEST.json"
    manifest_path.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(result["marker"])
    print(json.dumps({"files": len(files), "deployed": False}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
