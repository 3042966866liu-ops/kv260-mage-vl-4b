#!/usr/bin/env python3
"""Synchronize verified M218 dual-source board/public control-plane evidence."""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
BOARD = ROOT / "deployment/mage_vl4b/BOARD_GATE_RESULT.json"
CURRENT = ROOT / "CURRENT_STATE.md"
MILESTONES = ROOT / "docsMILESTONES.md"
OFFLINE = ROOT / "deployment/mage_vl4b/M218_DUAL_SOURCE_FILE_REPLAY_OFFLINE_RESULT.json"
DELTA = ROOT / "deployment/mage_vl4b/M218_DUAL_SOURCE_BOARD_DELTA_RESULT.json"
BOARD_RESULT = ROOT / "deployment/mage_vl4b/M218_DUAL_SOURCE_SERVICE_BOARD_RESULT_01.json"
HTTP_RESULT = ROOT / "deployment/mage_vl4b/M220_M218_DUAL_SOURCE_HTTP_RESULT.json"
START = "<!-- M206_M209_OPTIMIZATION_STREAM_CORE_START -->"
END = "<!-- M206_M209_OPTIMIZATION_STREAM_CORE_END -->"


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def atomic(path: Path, text: str) -> None:
    temporary = path.with_name(path.name + ".partial")
    temporary.write_text(text, encoding="utf-8")
    os.replace(temporary, path)


def update_section(path: Path, section: str) -> None:
    text = path.read_text(encoding="utf-8")
    if text.count(START) != 1 or text.count(END) != 1:
        raise RuntimeError(f"M221 section markers invalid in {path}")
    before, rest = text.split(START, 1)
    _old, after = rest.split(END, 1)
    atomic(path, before + section + after)


def main() -> int:
    offline, delta, board_result, http = map(read, (OFFLINE, DELTA, BOARD_RESULT, HTTP_RESULT))
    if offline.get("status") != "PASS" or not all(offline.get("checks", {}).values()):
        raise RuntimeError("M218 offline evidence is not complete PASS")
    if delta.get("status") != "PASS":
        raise RuntimeError("M218 delta build is not PASS")
    if board_result.get("status") != "PASS":
        raise RuntimeError("M218 board service is not PASS")
    if http.get("status") != "PASS" or not all(http.get("checks", {}).values()):
        raise RuntimeError("M220 local/public HTTP evidence is not complete PASS")
    if board_result.get("package_manifest_sha256") != delta.get("package_manifest_sha256"):
        raise RuntimeError("M218 board/delta manifest identity mismatch")
    if http.get("health") != board_result.get("local_health"):
        raise RuntimeError("M218 board/HTTP health identity mismatch")

    hashes = {
        "offline": sha(OFFLINE),
        "delta": sha(DELTA),
        "board": sha(BOARD_RESULT),
        "http": sha(HTTP_RESULT),
    }
    board = read(BOARD)
    previous = board.get("latest_m212_live_stream_service", {})
    if previous.get("formal_result_sha256") != "60b739b83ab1730132a0517142164113e8ceb53b4508045d55c294a1bda0fafc":
        raise RuntimeError("M212 rollback predecessor identity mismatch")
    latest = {
        "date": "2026-09-01",
        "gate": "M218-real-KV260-dual-source-public-HTTPS-control-plane",
        "status": "PUBLIC_HTTPS_CONTROL_PLANE_PASS_REAL_FRAMES_PENDING",
        "classification": "Real-KV260 hash-verified camera/local-file-loop latest-only HTTP/SSE service and public HTTPS control plane; no browser video selection, real frame transmission, runtime load, FPGA complete window, or latency acceptance yet.",
        "candidate_build_id": "0x4D395832",
        "input_modes": ["browser-camera", "uploaded-file-loop"],
        "file_replay_semantics": "finite local content decoded and looped in the browser into a continuing sampled-frame source; not a live camera",
        "transport_semantics": "the full video file is not uploaded; only 448x448 RGB sampled frames are POSTed",
        "package_manifest_sha256": delta["package_manifest_sha256"],
        "service_pid": board_result["service_pid"],
        "local_health": board_result["local_health"],
        "board_url": http["board_url"],
        "public_url": http["public_url"],
        "cloudflared_pid": http["cloudflared_pid"],
        "http_checks": http["checks"],
        "offline_result": "deployment/mage_vl4b/M218_DUAL_SOURCE_FILE_REPLAY_OFFLINE_RESULT.json",
        "offline_result_sha256": hashes["offline"],
        "delta_result": "deployment/mage_vl4b/M218_DUAL_SOURCE_BOARD_DELTA_RESULT.json",
        "delta_result_sha256": hashes["delta"],
        "board_result": "deployment/mage_vl4b/M218_DUAL_SOURCE_SERVICE_BOARD_RESULT_01.json",
        "board_result_sha256": hashes["board"],
        "http_result": "deployment/mage_vl4b/M220_M218_DUAL_SOURCE_HTTP_RESULT.json",
        "http_result_sha256": hashes["http"],
        "actual_test_video": offline["video_evidence"],
        "web_control_plane_deployed": True,
        "video_selected": False,
        "video_frames_transmitted": False,
        "board_runtime_loaded": False,
        "continuous_stream_inference_executed": False,
        "web_deployed": False,
        "temporary_runtime_state_changed": True,
        "persistent_boot_dtb_cma_partitions_services_changed": False,
        "stable_m212_rollback_preserved": True,
        "rejected_attempts": [
            "First COM3 controller invocation stopped before upload because sudo -n required a password; no board state changed.",
            "Windows PowerShell 5.1 UTF-8 parser and nested parser-command attempts were rejected locally; fixed PowerShell 7 -File execution passed without board impact.",
        ],
        "next_gate": http["next_gate"],
    }
    board["latest_m218_dual_source_service"] = latest
    board["status"] = "M218_DUAL_SOURCE_PUBLIC_HTTPS_CONTROL_PLANE_PASS_REAL_FRAMES_PENDING"
    board["next_gate"] = http["next_gate"]
    board["stable_rollback_preserved"] = True
    atomic(BOARD, json.dumps(board, ensure_ascii=False, indent=2) + "\n")

    section = f"""{START}
## M218--M221：KV260 摄像头与本地 MP4 循环双源网页已发布（2026-09-01）

- M218 保留两种输入：`browser-camera` 是持续到来的真实现场源；`uploaded-file-loop` 是浏览器
  本地解码并循环的有限内容。后者会持续产生采样帧，但不能冒充实时摄像头。完整视频文件不会
  上传，网页只把 448x448 RGB 帧送入同一个容量 16、最新四帧、单窗口积压的 M209 调度器。
- 实际 MP4 为 `{offline['video_evidence']['filename']}`，时长 `{offline['video_evidence']['duration_seconds']:.2f}` 秒，
  `{offline['video_evidence']['bytes']}` 字节，H.264 `{offline['video_evidence']['video_sample_entry']}`，SHA-256
  `{offline['video_evidence']['sha256']}`。离线 64 帧压力门禁覆盖 48 帧、最终追到序号 63、Runtime
  只加载一次；结果 SHA-256 `{hashes['offline']}`。
- 12 成员、78,771 字节的 M218 delta（manifest `{delta['package_manifest_sha256']}`）经 manifest-first
  分块 COM3 上传、板端逐文件哈希、root/XRT/PYNQ 和 M179/M198/M208/M209 前序门禁后，临时网页
  服务切换为 PID `{board_result['service_pid']}`。旧 M212 目录保留，runner 失败路径具备自动回滚。
- 局域网与公网 HTTPS 均 PASS：[{http['public_url']}]({http['public_url']})；公网与板端 HTML/JS
  完全一致，摄像头、本地文件循环、SSE、Build `0x4D395832`、kernel `mage_m120_m89x2_0` 合同通过。
  M220 结果 SHA-256 `{hashes['http']}`。
- 边界：尚未在浏览器选择视频、未传输真实帧、Runtime 未加载、未出现 FPGA-backed complete
  window，也没有新的首 Token 或吞吐证据；当前只可称“双源 Web 控制面已部署”。下一步必须在
  用户操作时确认后，选择本地 MP4 并启动一次会话，保留首个完整窗口证据。
- 被拒绝的无板端影响尝试：首次 `sudo -n` 过期时在上传前停止；M220 的 Windows PowerShell 5.1
  UTF-8 解析与嵌套 parser 命令均在本地停止，已固定改用 PowerShell 7 `-File`。
{END}"""
    update_section(CURRENT, section)
    update_section(MILESTONES, section)
    print("M221_M218_DUAL_SOURCE_STATE_SYNC_PASS")
    print(json.dumps(hashes, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
