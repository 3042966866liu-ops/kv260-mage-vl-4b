#!/usr/bin/env python3
"""Synchronize the verified M148 extraction and M182 video offline PASS."""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
M148_REL = "deployment/mage_vl4b/M148_M120_W3_FULL_EMBEDDING_EXTRACTION_RESULT.json"
M182_REL = "deployment/mage_vl4b/M182_M181_VIDEO_CANDIDATE_OFFLINE_GATE_RESULT.json"
M179_SHA = "3a798eafd2e66974774dcdcac39de86243830a6a4771eb182cd535220b4aacd3"
PACKAGE_SHA = "1596536bfe6865cb7eab5c038d8b4da8b666afc7cbd629ddc4559781727151d6"


def digest(path: Path) -> str:
    value = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(32 << 20), b""):
            value.update(block)
    return value.hexdigest()


def atomic_json(path: Path, value: dict) -> None:
    temporary = path.with_name(path.name + f".partial-{os.getpid()}")
    temporary.write_text(json.dumps(value, indent=2) + "\n", encoding="utf-8")
    os.replace(temporary, path)


def replace_marker(path: Path, start: str, end: str, body: str) -> None:
    text = path.read_text(encoding="utf-8")
    block = f"{start}\n{body.rstrip()}\n{end}\n\n"
    if start in text:
        before, rest = text.split(start, 1)
        _, after = rest.split(end, 1)
        text = before + block + after.lstrip("\r\n")
    else:
        lines = text.splitlines(keepends=True)
        insert = 1 if lines and lines[0].startswith("# ") else 0
        text = "".join(lines[:insert]) + ("\n" if insert else "") + block + "".join(lines[insert:])
    temporary = path.with_name(path.name + f".partial-{os.getpid()}")
    temporary.write_text(text, encoding="utf-8")
    os.replace(temporary, path)


def main() -> int:
    m148_path = ROOT / M148_REL
    m182_path = ROOT / M182_REL
    m148 = json.loads(m148_path.read_text(encoding="utf-8"))
    m182 = json.loads(m182_path.read_text(encoding="utf-8"))
    if m148.get("status") != "PASS" or m148.get("build_id_gate") != "0x4D395832":
        raise RuntimeError("M183 M148 status/build mismatch")
    if m148.get("fixed_text_formal_result_sha256") != M179_SHA:
        raise RuntimeError("M183 M148 predecessor mismatch")
    if int(m148.get("output_bytes", -1)) != 777_912_320:
        raise RuntimeError("M183 M148 output size mismatch")
    declared_embedding = str(m148["output"]).replace("\\", "/")
    expected_suffix = "/deployment/mage_vl4b/artifacts/m148_m120_w3_embedding.fp16.rowmajor.bin"
    if not declared_embedding.endswith(expected_suffix):
        raise RuntimeError("M183 M148 output path is outside the fixed artifact identity")
    embedding = ROOT / "deployment/mage_vl4b/artifacts/m148_m120_w3_embedding.fp16.rowmajor.bin"
    if not embedding.is_file() or digest(embedding) != m148.get("output_sha256"):
        raise RuntimeError("M183 M148 output identity mismatch")
    if m182.get("status") != "PASS_OFFLINE_VIDEO_CANDIDATE_BOARD_NOT_EXECUTED":
        raise RuntimeError("M183 M182 status mismatch")
    if m182.get("package_manifest_sha256") != PACKAGE_SHA or m182.get("m179_fixed_text_result_sha256") != M179_SHA:
        raise RuntimeError("M183 M182 package/predecessor mismatch")
    if m182.get("video_board_executed") is not False or m182.get("web_deployed") is not False:
        raise RuntimeError("M183 M182 scope mismatch")
    if m182["same_method_cpu_golden_result"].get("status") != "PASS" or m182["cross_device_gpu_golden_result"].get("status") != "FAIL":
        raise RuntimeError("M183 retained vision result policy mismatch")

    board_path = ROOT / "deployment/mage_vl4b/BOARD_GATE_RESULT.json"
    board = json.loads(board_path.read_text(encoding="utf-8"))
    board["status"] = "M182_M120_VIDEO_OFFLINE_CANDIDATE_PASS_BOARD_VIDEO_PENDING"
    board["full_model_deployed"] = False
    board["web_deployed"] = False
    board["stable_rollback_preserved"] = True
    board["latest_m120_full_w3_embedding"] = {
        **m148,
        "formal_result": M148_REL,
        "formal_result_sha256": digest(m148_path),
    }
    board["latest_m120_video_offline_candidate"] = {
        **m182,
        "formal_result": M182_REL,
        "formal_result_sha256": digest(m182_path),
        "scope_boundary": "Offline video package/contract PASS only; no KV260 video inference or Web proof.",
    }
    board["next_gate"] = "Prepare a hash-checked COM3-controlled large-package transport, then run only the first bounded real-board video gate."
    atomic_json(board_path, board)

    cpu = m182["same_method_cpu_golden_result"]["metrics_vs_M56_W4_BF16_golden"]
    gpu = m182["cross_device_gpu_golden_result"]["metrics_vs_M56_W4_BF16_golden"]
    body = f"""## M148/M181/M182: corrected M120 video candidate passes offline closure (2026-09-01)

- M148 extracted the accepted M120 W3-G64 embedding to FP16 row-major: `777,912,320` bytes, SHA-256 `{m148['output_sha256']}`. It is locked to the exact M179 real-board fixed-text PASS.
- M181 built a clean `48`-member, `{m182['total_file_bytes']}`-byte video candidate with package-manifest SHA-256 `{PACKAGE_SHA}`. It inherits the exact M175 null-safe board runtime, Build `0x4D395832`, M120 early split-Q/KV schedule, four-frame preprocessing, PS BF16/W4 vision and SSE sources. Fixed-prompt/Layer-0 fixtures and Python caches are excluded.
- Offline contracts pass for preprocessing, the 849-token/784-visual-token splice, the bounded request envelope, and all `98` visual W4 modules (`329,252,864` BF16 elements, zero mismatched modules). The frozen schedule remains `4166` calls for the 849-token one-token path and `162` calls for each subsequent token.
- The cross-device GPU-golden comparison is retained as FAIL (cosine `{gpu['cosine_similarity']:.9f}`, RMSE `{gpu['rmse']:.9f}`); the same-method CPU/PS reference passes the unchanged thresholds (cosine `{cpu['cosine_similarity']:.9f}`, RMSE `{cpu['rmse']:.9f}`). No threshold was relaxed.
- A WSL test generated `__pycache__` in the candidate; those exact test-only caches were removed, and M182 reverified the complete on-disk closure with no cache/partial members. No model weight, boot, DTB, CMA, partition, service or stable rollback state changed.
- Scope is offline only. Video inference has not run on the KV260 and Web is not deployed; `full_model_deployed=false` and `web_deployed=false` remain authoritative.

Evidence: `{M148_REL}` (SHA-256 `{digest(m148_path)}`) and `{M182_REL}` (SHA-256 `{digest(m182_path)}`)."""
    replace_marker(ROOT / "CURRENT_STATE.md", "<!-- M182_VIDEO_OFFLINE_PASS_START -->", "<!-- M182_VIDEO_OFFLINE_PASS_END -->", body)
    replace_marker(ROOT / "docsMILESTONES.md", "<!-- M182_VIDEO_OFFLINE_PASS_START -->", "<!-- M182_VIDEO_OFFLINE_PASS_END -->", body.replace("## M148/M181/M182:", "## M148/M181/M182："))
    print(json.dumps({
        "status": "PASS",
        "m148_result_sha256": digest(m148_path),
        "m182_result_sha256": digest(m182_path),
        "board_gate_result_sha256": digest(board_path),
    }, indent=2))
    print("M183_M148_M182_VIDEO_OFFLINE_STATE_SYNC_PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
