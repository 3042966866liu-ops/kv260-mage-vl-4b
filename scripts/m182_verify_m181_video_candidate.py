#!/usr/bin/env python3
"""Fail-closed offline closure gate for the M181 M120 video candidate."""

from __future__ import annotations

import ast
import hashlib
import json
import os
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CANDIDATE = ROOT / "deployment/mage_vl4b/m181_m120_video_board_candidate"
OUTPUT = ROOT / "deployment/mage_vl4b/M182_M181_VIDEO_CANDIDATE_OFFLINE_GATE_RESULT.json"
EXPECTED_PACKAGE_SHA256 = "1596536bfe6865cb7eab5c038d8b4da8b666afc7cbd629ddc4559781727151d6"
EXPECTED_EMBEDDING_SHA256 = "ec02de7da15a1569e96e50d886a3e4532617197e7a7aa84ac7196489caab4df4"
EXPECTED_M175_RUNTIME_SHA256 = "5d53ea406e57de88f8c14d9bc4e1cb0c0049ff0b8f4bcf620e05745fcd82b201"
EXPECTED_M179_SHA256 = "3a798eafd2e66974774dcdcac39de86243830a6a4771eb182cd535220b4aacd3"
EXPECTED_BUILD_ID = "0x4D395832"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(32 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def load(path: Path) -> dict:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise RuntimeError(f"JSON root is not an object: {path}")
    return value


def atomic_json(path: Path, value: dict) -> None:
    temporary = path.with_name(path.name + f".tmp-{os.getpid()}")
    temporary.write_text(json.dumps(value, indent=2) + "\n", encoding="utf-8")
    os.replace(temporary, path)


def require_status(path: Path, status: str) -> dict:
    value = load(path)
    if value.get("status") != status:
        raise RuntimeError(f"unexpected status for {path}: {value.get('status')}")
    return value


def main() -> int:
    sys.dont_write_bytecode = True
    result: dict[str, object] = {
        "date": "2026-09-01",
        "gate": "M182-M181-M120-video-candidate-offline-closure",
        "status": "FAIL",
        "classification": "Offline clean-package, source, scheduling and numerical contract gate; not board video or Web evidence.",
        "board_state_changed": False,
        "stable_rollback_preserved": True,
    }
    try:
        package_path = CANDIDATE / "PACKAGE_MANIFEST.json"
        package_sha = sha256(package_path)
        if package_sha != EXPECTED_PACKAGE_SHA256:
            raise RuntimeError("M181 package manifest identity mismatch")
        package = load(package_path)
        ready = load(CANDIDATE / "PACKAGE_READY.json")
        if package.get("gate") != "M181-M120-clean-video-board-package":
            raise RuntimeError("M181 package gate mismatch")
        if package.get("status") != "OFFLINE_PACKAGE_PASS_BOARD_NOT_EXECUTED":
            raise RuntimeError("M181 package status mismatch")
        if package.get("build_id") != EXPECTED_BUILD_ID or ready.get("build_id") != EXPECTED_BUILD_ID:
            raise RuntimeError("M181 Build ID mismatch")
        if ready.get("status") != "READY" or ready.get("package_manifest_sha256") != package_sha:
            raise RuntimeError("M181 PACKAGE_READY mismatch")
        if package.get("m179_fixed_text_result_sha256") != EXPECTED_M179_SHA256:
            raise RuntimeError("M179 predecessor identity mismatch")
        if package.get("m175_null_safe_text_package_manifest_sha256") != "406dcca340e4604baeb761445795391c43ec26bd99fa06ffae893d597b17414f":
            raise RuntimeError("M175 predecessor identity mismatch")

        declared = {item["path"]: item for item in package["files"]}
        if len(declared) != int(package["file_count"]) or len(declared) != 48:
            raise RuntimeError("M181 package file closure mismatch")
        if sum(int(item["bytes"]) for item in declared.values()) != int(package["total_file_bytes"]):
            raise RuntimeError("M181 package declared byte total mismatch")
        for relative, item in declared.items():
            path = CANDIDATE / relative
            if not path.is_file() or path.stat().st_size != int(item["bytes"]) or sha256(path) != item["sha256"]:
                raise RuntimeError(f"M181 package member mismatch: {relative}")
        actual = {
            path.relative_to(CANDIDATE).as_posix()
            for path in CANDIDATE.rglob("*")
            if path.is_file()
        }
        expected = set(declared) | {"PACKAGE_MANIFEST.json", "PACKAGE_READY.json"}
        if actual != expected:
            raise RuntimeError(f"M181 package actual closure mismatch: extra={sorted(actual-expected)} missing={sorted(expected-actual)}")
        forbidden = [
            path.relative_to(CANDIDATE).as_posix()
            for path in CANDIDATE.rglob("*")
            if "__pycache__" in path.parts or path.suffix == ".pyc" or path.name.endswith(".partial")
        ]
        if forbidden:
            raise RuntimeError(f"M181 package cache/partial pollution: {forbidden}")

        embedding = CANDIDATE / "text_auxiliary/embedding.fp16.rowmajor.bin"
        if embedding.stat().st_size != 777_912_320 or sha256(embedding) != EXPECTED_EMBEDDING_SHA256:
            raise RuntimeError("M181 M120 W3 embedding mismatch")
        runtime_path = CANDIDATE / "text_runtime/runtime/board_runtime.py"
        if sha256(runtime_path) != EXPECTED_M175_RUNTIME_SHA256:
            raise RuntimeError("M181 did not inherit the exact M175 runtime")
        runtime_source = runtime_path.read_text(encoding="utf-8")
        ast.parse(runtime_source, filename=str(runtime_path))
        if runtime_source.count('int(chain["layer"]) if "layer" in chain else None') != 0:
            raise RuntimeError("M181 contains unsafe optional-layer conversion")
        if runtime_source.count('int(chain["layer"]) if chain.get("layer") is not None else None') != 2:
            raise RuntimeError("M181 null-safe optional-layer conversion count mismatch")
        python_files = sorted(CANDIDATE.rglob("*.py"))
        for path in python_files:
            ast.parse(path.read_text(encoding="utf-8"), filename=str(path))

        evidence_root = ROOT / "tmp/m181_video_offline"
        preprocess = require_status(evidence_root / "board_preprocess.json", "PASS")
        prompt = require_status(evidence_root / "video_prompt_splice.json", "PASS")
        request = require_status(evidence_root / "video_request.json", "PASS")
        decode = require_status(evidence_root / "vision_weight_decode.json", "PASS")
        gpu = require_status(evidence_root / "ps_vision_runtime.json", "FAIL")
        cpu = require_status(evidence_root / "ps_vision_runtime_cpu_golden.json", "PASS")
        if int(decode.get("module_count", -1)) != 98 or int(decode.get("compared_bf16_elements", -1)) != 329_252_864:
            raise RuntimeError("M181 visual W4 decode coverage mismatch")
        gpu_metrics = gpu["metrics_vs_M56_W4_BF16_golden"]
        cpu_metrics = cpu["metrics_vs_M56_W4_BF16_golden"]
        if not (float(gpu_metrics["cosine_similarity"]) < 0.999):
            raise RuntimeError("retained cross-device GPU-golden rejection drift")
        if not (float(cpu_metrics["cosine_similarity"]) >= 0.999 and float(cpu_metrics["rmse"]) <= 0.05):
            raise RuntimeError("same-method CPU-golden acceptance drift")
        if package.get("frozen_849_token_prefill_calls") != 4166 or package.get("decode_calls_per_subsequent_token") != 162:
            raise RuntimeError("M181 language schedule accounting mismatch")

        result.update({
            "status": "PASS_OFFLINE_VIDEO_CANDIDATE_BOARD_NOT_EXECUTED",
            "candidate_build_id": EXPECTED_BUILD_ID,
            "candidate_directory": str(CANDIDATE.resolve()),
            "package_manifest_sha256": package_sha,
            "file_count": len(declared),
            "total_file_bytes": int(package["total_file_bytes"]),
            "python_source_count": len(python_files),
            "embedding_bytes": embedding.stat().st_size,
            "embedding_sha256": EXPECTED_EMBEDDING_SHA256,
            "m175_null_safe_runtime_sha256": EXPECTED_M175_RUNTIME_SHA256,
            "m179_fixed_text_result_sha256": EXPECTED_M179_SHA256,
            "preprocess": preprocess,
            "prompt_splice": prompt,
            "request_envelope": request,
            "visual_w4_decode": decode,
            "cross_device_gpu_golden_result": gpu,
            "same_method_cpu_golden_result": cpu,
            "cross_device_gpu_golden_retained_as_rejected": True,
            "frozen_849_token_prefill_calls": 4166,
            "decode_calls_per_subsequent_token": 162,
            "video_board_executed": False,
            "web_deployed": False,
            "next_gate": "Prepare a hash-checked COM3-controlled transport and run only the first bounded video board gate; do not claim video/Web deployment.",
        })
    except BaseException as error:
        result["error"] = f"{type(error).__name__}: {error}"
        result["next_gate"] = "Correct and rerun only the M182 offline video candidate gate."
    atomic_json(OUTPUT, result)
    print(json.dumps(result, indent=2), flush=True)
    print("M182_M181_VIDEO_CANDIDATE_OFFLINE_PASS" if str(result["status"]).startswith("PASS") else "M182_M181_VIDEO_CANDIDATE_OFFLINE_FAIL")
    return 0 if str(result["status"]).startswith("PASS") else 1


if __name__ == "__main__":
    raise SystemExit(main())
