#!/usr/bin/env python3
"""Hash-lock the complete M90 offline video board candidate without deploying it."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
from pathlib import Path


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(16 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def verify_file(path: Path, item: dict) -> dict:
    if not path.is_file() or path.stat().st_size != int(item["bytes"]) or sha256(path) != item["sha256"]:
        raise RuntimeError(f"M90_FILE_IDENTITY_FAIL path={path}")
    return {"path": path.as_posix(), "bytes": path.stat().st_size, "sha256": item["sha256"]}


def verify_layout(root: Path, expected_modules: int, expected_manifest_sha: str | None = None) -> dict:
    manifest_path = root / "SIXPORT_LAYOUT_MANIFEST.json"
    manifest_sha = sha256(manifest_path)
    if expected_manifest_sha is not None and manifest_sha != expected_manifest_sha:
        raise RuntimeError(f"M90_LAYOUT_MANIFEST_IDENTITY_FAIL path={manifest_path}")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if manifest.get("format") != "tellme-mage-vl-fourport-group-major-v1":
        raise RuntimeError(f"M90_LAYOUT_FORMAT_FAIL path={manifest_path}")
    if int(manifest.get("module_count", -1)) != expected_modules:
        raise RuntimeError(f"M90_LAYOUT_MODULE_COUNT_FAIL path={manifest_path}")
    files = [verify_file(root / item["path"], item) for item in manifest["files"]]
    return {
        "root": root.as_posix(), "manifest_sha256": manifest_sha,
        "module_count": expected_modules, "mapped_bytes": sum(item["bytes"] for item in files),
        "files": files,
    }


def atomic_json(path: Path, payload: dict) -> None:
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    os.replace(temporary, path)


def source_build_id(path: Path) -> str:
    """Extract the explicit build identity from a candidate Python source file."""
    text = path.read_text(encoding="utf-8")
    match = re.search(r'(?m)^BUILD_ID\s*=\s*["\'](0x[0-9a-fA-F]+)["\']\s*$', text)
    if match is None:
        match = re.search(r'(?m)["\']build_id["\']\s*:\s*["\'](0x[0-9a-fA-F]+)["\']', text)
    if match is None:
        raise RuntimeError(f"M90_SOURCE_BUILD_ID_MISSING path={path}")
    return match.group(1).lower()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--workspace", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--result", type=Path, required=True)
    args = parser.parse_args()
    workspace = args.workspace.resolve()
    root = workspace / "deployment/mage_vl4b"
    candidate = root / "m90_video_board_candidate"
    m89 = root / "m89x_board_candidate"
    m89_manifest_path = m89 / "PACKAGE_MANIFEST.json"
    m89_manifest = json.loads(m89_manifest_path.read_text(encoding="utf-8"))
    if m89_manifest.get("status") != "PASS_OFFLINE_BOARD_CANDIDATE_PACKAGE":
        raise RuntimeError("M90_M89_CANDIDATE_NOT_ACCEPTED")
    if m89_manifest.get("build") != "M89-X1/Z2":
        raise RuntimeError("M90_REJECTED_TEXT_BUILD")
    if m89_manifest.get("deployed") is not False or m89_manifest.get("stable_rollback_required") is not True:
        raise RuntimeError("M90_M89_ROLLBACK_BOUNDARY_FAIL")
    board_gate = json.loads((root / "BOARD_GATE_RESULT.json").read_text(encoding="utf-8"))
    expected_text_manifest = board_gate.get("latest_m89x1_attempt", {}).get("package_manifest_sha256")
    if not isinstance(expected_text_manifest, str) or sha256(m89_manifest_path) != expected_text_manifest:
        raise RuntimeError("M90_TEXT_PACKAGE_BOARD_IDENTITY_FAIL")
    norm_csim_path = root / "M89X1_NORM_QKV_CSIM_RESULT.json"
    if not norm_csim_path.is_file() or read_json(norm_csim_path).get("status") != "PASS":
        raise RuntimeError("M90_TEXT_RMSNORM_HLS_CSIM_REQUIRED")
    layer0_gate = board_gate.get("latest_m89x1_layer0_gate")
    if not isinstance(layer0_gate, dict) or layer0_gate.get("status") != "PASS":
        raise RuntimeError("M90_TEXT_LAYER0_BOARD_ACCEPTANCE_REQUIRED")
    runtime_builds = {
        "video_server.py": source_build_id(candidate / "video_server.py"),
        "vision_linear_runtime.py": source_build_id(candidate / "vision_linear_runtime.py"),
    }
    if set(runtime_builds.values()) != {"0x4d395831"}:
        raise RuntimeError(f"M90_RUNTIME_BUILD_IDENTITY_FAIL builds={runtime_builds}")
    header_gate = json.loads((root / "M89_HEADER_DEPENDENCY_AUDIT_RESULT.json").read_text(encoding="utf-8"))
    if header_gate.get("status") != "PASS" or len(header_gate.get("missing", [])) != 0:
        raise RuntimeError("M90_RECURSIVE_HEADER_CLOSURE_FAIL")

    service_gate_path = root / "M90_VIDEO_SERVICE_PREFLIGHT_RESULT.json"
    service_gate = json.loads(service_gate_path.read_text(encoding="utf-8"))
    if service_gate.get("status") != "PASS" or service_gate.get("board_state_changed") is not False:
        raise RuntimeError("M90_SERVICE_PREFLIGHT_FAIL")

    large = {item["label"]: item for item in m89_manifest["large_payloads"]}
    layouts = {
        "language": verify_layout(root / "artifacts/m89y_language_fourport", 252,
                                  large["language"]["manifest_sha256"]),
        "lm_head": verify_layout(root / "artifacts/m89z2_lmhead_w4_fourport", 1,
                                 large["lm_head"]["manifest_sha256"]),
        "vision": verify_layout(root / "artifacts/m90_vision_w4_fourport", 98),
    }

    aux_root = root / "artifacts/M79-full-text-aux"
    aux_manifest_path = aux_root / "M79_FULL_TEXT_AUX_MANIFEST.json"
    aux = json.loads(aux_manifest_path.read_text(encoding="utf-8"))
    if aux.get("result") != "PASS" or aux.get("full_text_input_coverage") is not True:
        raise RuntimeError("M90_TEXT_AUX_NOT_ACCEPTED")
    aux_files = [verify_file(aux_root / aux["embedding"]["path"], aux["embedding"]),
                 verify_file(aux_root / aux["norms"]["path"], aux["norms"])]
    aux_files.extend(verify_file(aux_root / item["path"], item) for item in aux["tokenizer_files"])

    raw_manifest_path = candidate / "auxiliary/M90_VISION_RAW_AUX_MANIFEST.json"
    raw = json.loads(raw_manifest_path.read_text(encoding="utf-8"))
    raw_file = verify_file(raw_manifest_path.parent / raw["blob"]["path"], raw["blob"])

    included = []
    for path in sorted(candidate.rglob("*")):
        if not path.is_file() or "__pycache__" in path.parts or path == args.output.resolve():
            continue
        # The 660 MiB official-BF16 extraction is a reference/fallback payload;
        # the accepted memory-bounded route uses the three model-code files,
        # the 174 MiB exact W4 layout and the 2.2 MiB raw auxiliary instead.
        if path.name == "vision_bf16.safetensors":
            continue
        included.append({"path": path.relative_to(candidate).as_posix(),
                         "bytes": path.stat().st_size, "sha256": sha256(path)})
    required_code = {
        "board_preprocess.py", "video_request.py", "video_prompt.py", "video_language_runtime.py",
        "ps_vision_runtime.py", "video_server.py", "static/index.html", "static/style.css", "static/app.js",
    }
    included_names = {item["path"] for item in included}
    if not required_code <= included_names:
        raise RuntimeError(f"M90_SOURCE_CLOSURE_FAIL missing={sorted(required_code - included_names)}")

    if board_gate.get("full_model_deployed") is not False or board_gate.get("web_deployed") is not False:
        raise RuntimeError("M90_CURRENT_BOARD_BOUNDARY_FAIL")
    if board_gate.get("stable_rollback_preserved") is not True:
        raise RuntimeError("M90_CURRENT_STABLE_ROLLBACK_FAIL")
    if board_gate.get("candidate_build_id") != "0x4D395831":
        raise RuntimeError("M90_TEXT_BUILD_IDENTITY_FAIL")
    qkv_gate = board_gate.get("latest_m89x1_qkv_gate")
    if not isinstance(qkv_gate, dict) or qkv_gate.get("status") != "PASS":
        raise RuntimeError("M90_TEXT_SINGLE_CHAIN_BOARD_GATE_REQUIRED")

    forbidden_cache = [path for path in candidate.rglob("*")
                       if path.is_file() and ("__pycache__" in path.parts or path.suffix == ".pyc")]
    if forbidden_cache:
        raise RuntimeError(f"M90_CLEAN_STAGING_REQUIRED count={len(forbidden_cache)}")

    payload = {
        "date": "2026-08-31",
        "build": "M90-video",
        "status": "PASS_OFFLINE_VIDEO_BOARD_CANDIDATE",
        "marker": "M90_VIDEO_OFFLINE_BOARD_CANDIDATE_PASS",
        "deployed": False,
        "web_deployed": False,
        "board_state_changed": False,
        "stable_rollback_preserved": True,
        "fpga_build_id": "0x4d395831",
        "architecture": "aarch64 Cortex-A53 + KV260 PL",
        "route": {
            "browser": "decode and center-crop 0/1/2/3-second frames to four RGB 448x448 arrays",
            "ps_vision": "exact M56 W4 weights decoded one Linear at a time; BF16 activations; visual A8 disabled",
            "pl_language": "M89-X1 T32 all 36 language layers plus untied LM Head",
            "transport": "bounded binary frame envelope in; SSE token stream out",
        },
        "verified_call_schedule": {
            "fixed_prompt_tokens": 849,
            "prefill_pl_chain_calls": 3896,
            "decode_pl_chain_calls_per_token_after_first": 152,
        },
        "m89_candidate_manifest": {"path": m89_manifest_path.as_posix(), "sha256": sha256(m89_manifest_path)},
        "runtime_build_ids": runtime_builds,
        "rmsnorm_hls_csim": {"path": norm_csim_path.as_posix(), "sha256": sha256(norm_csim_path)},
        "text_layer0_board_gate": layer0_gate,
        "text_single_chain_board_gate": qkv_gate,
        "recursive_header_gate": {"path": (root / "M89_HEADER_DEPENDENCY_AUDIT_RESULT.json").as_posix(),
                                  "sha256": sha256(root / "M89_HEADER_DEPENDENCY_AUDIT_RESULT.json"),
                                  "missing_count": 0},
        "layouts": layouts,
        "text_auxiliary": {"manifest_sha256": sha256(aux_manifest_path), "files": aux_files},
        "raw_vision_auxiliary": {"manifest_sha256": sha256(raw_manifest_path), "file": raw_file},
        "candidate_files": included,
        "service_preflight": {"path": service_gate_path.as_posix(), "sha256": sha256(service_gate_path)},
        "runtime_dependencies": ["Python >=3.10 aarch64", "numpy", "torch with CPU BF16", "transformers",
                                 "tokenizers", "pynq", "zocl", "/dev/tellme_reserved1664"],
        "rejected_attempts": [
            "M62 visual A8: only 2/3 semantic cases passed; excluded from primary route",
            "M90 lazy visual with FP32 RoPE/BF16 weights: cross-backend and same-backend gates below threshold",
            "M90 first BF16 lazy visual: RoPE buffers incorrectly retained FP32; corrected to official BF16 behavior",
            "M90 first Decode adapter: fixed 32-row hardware output could broadcast one token; all families now crop through _family",
            "M90 attention host-test expectation used 2560 instead of actual pre-o_proj width 4096; harness corrected",
        ],
        "next_gate": "Copy this immutable candidate and exact payloads to a new board directory, run dependency/hash preflight, then one reversible board smoke; do not modify boot/DTB/CMA or stable rollback.",
    }
    atomic_json(args.output, payload)
    result = {
        "gate": "M90-complete-video-offline-board-candidate",
        "status": payload["status"],
        "candidate_manifest": args.output.resolve().as_posix(),
        "candidate_manifest_sha256": sha256(args.output.resolve()),
        "candidate_file_count": len(included),
        "large_payload_bytes": sum(item["mapped_bytes"] for item in layouts.values()) + sum(item["bytes"] for item in aux_files) + raw_file["bytes"],
        "deployed": False,
        "board_state_changed": False,
        "stable_rollback_preserved": True,
    }
    atomic_json(args.result, result)
    print("M90_VIDEO_OFFLINE_BOARD_CANDIDATE_PASS")
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
