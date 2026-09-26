#!/usr/bin/env python3
"""Compile complete, status-labelled first-party Mage-VL source into one Markdown file."""

from __future__ import annotations

import hashlib
import re
from pathlib import Path


WORKSPACE = Path(__file__).resolve().parents[1]
OUTPUT = WORKSPACE / "kv260-mage-vl-4Bcode.md"
SEPARATOR = "=" * 20
SUFFIXES = {".py", ".sh", ".ps1", ".cpp", ".hpp", ".h", ".tcl", ".js", ".html", ".css"}

# These are the local source closures of the active M254 service, the measured
# M277/BACT fixed-video path, and the explicitly non-default OP01 experiment.
ROOTS = (
    ("deployment/mage_vl4b/m254_dual_path_web_candidate", "当前稳定网页服务"),
    ("deployment/mage_vl4b/m243_web_prefill_board_candidate", "当前稳定网页服务依赖"),
    ("deployment/mage_vl4b/m242_m241_fixed_text_board_candidate", "当前稳定语言链依赖"),
    ("deployment/mage_vl4b/m238_input_prefetch_board_candidate", "当前稳定预填充依赖"),
    ("deployment/mage_vl4b/m241_grouped_gqa_board_candidate", "当前稳定语言链依赖"),
    ("deployment/mage_vl4b/m231_parse_reuse_board_candidate", "当前稳定预填充依赖"),
    ("deployment/mage_vl4b/m181_m120_video_board_candidate", "当前稳定视觉与视频依赖"),
    ("deployment/mage_vl4b/m175_m120_fixed_text_candidate", "当前稳定 FPGA 板端依赖"),
    ("deployment/mage_vl4b/m246_knife_binary_board_candidate", "当前稳定二元判定依赖"),
    ("deployment/mage_vl4b/m249_ssdlite_board_candidate", "当前稳定快速通道依赖"),
    ("tmp/m218_dual_source/m218_dual_source_delta", "当前稳定网页的本地暂存依赖"),
    ("tmp/m223_realtime/m223_realtime_delta", "当前稳定网页的本地暂存依赖"),
    ("tmp/m227_runtime_base/m227_runtime_base_patch", "当前稳定网页的本地暂存依赖"),
    ("hls/mage_prefill_m89x_runtime", "稳定 T32 FPGA 设计与验证"),
    ("deployment/mage_vl4b/m277_m276_fixed_window_board_candidate", "BACT 固定视频实测路径；非网页默认"),
    ("bact", "BACT 离线选择、评测与缓存工具；非网页默认"),
    ("deployment/mage_vl4b/optimization_v1/candidates/OP01-decode-one-ab-01", "Decode-one 实验候选；未替换稳定版"),
    ("hls/mage_decode_op01_one", "Decode-one 实验 FPGA 源码；未替换稳定版"),
)

EXTRA_FILES = (
    ("scripts/m321_reproduce_bact_v2_evidence.py", "BACT 离线证据复现；非网页默认"),
    ("scripts/m323_verify_decode_one_delivery.py", "Decode-one 实验交付核验；非网页默认"),
    ("scripts/m325_full_session_runtime.py", "Decode-one 同会话实验；未替换稳定版"),
    ("scripts/m325_full_session_board.py", "Decode-one 同会话实验；未替换稳定版"),
    ("scripts/m325_run_full_session_board.sh", "Decode-one 同会话实验；未替换稳定版"),
    ("scripts/m325_resume_gate.py", "Decode-one 同会话实验；未替换稳定版"),
    ("scripts/m325_collect_full_session.py", "Decode-one 同会话实验；未替换稳定版"),
    ("scripts/test_m325_full_session_runtime.py", "Decode-one 同会话实验测试；未替换稳定版"),
    ("scripts/generate_kv260_mage_vl_codebook.py", "本代码文档的可复现生成工具"),
    ("bact/bact_v2_protocol.json", "BACT 离线协议配置；非网页默认"),
    ("bact/bact_v2_selector_config.json", "BACT 离线选择器配置；非网页默认"),
)

DESCRIPTIONS = (
    ("m254_video_server", "提供当前双通道网页的 HTTP 接口、会话状态与前后端事件交互。"),
    ("m254_dual_path_core", "协调快速安全检测与较慢的 4B 语义复核，并管理最新窗口调度。"),
    ("fast_frame_pipeline", "处理输入帧与快速检测链的预处理和结果传递。"),
    ("fast_safety_monitor", "实现快速安全检测通道的判定与状态更新。"),
    ("immediate_safety_monitor", "组织即时安全监测和告警输出。"),
    ("latest_fast_stream", "维护只处理最新帧的有界实时输入流。"),
    ("temporal_action_adapter", "把时序人物动作结果适配为网页监控输出。"),
    ("knife_alarm", "实现刀具风险事件和告警状态的业务规则。"),
    ("m253_board_latest_stream", "连接板端快速通道与最新帧流。"),
    ("m243_video_server", "将网页请求连接到 FPGA 预填充和视频语言运行时。"),
    ("m241_video_language_runtime", "执行 Mage-VL 语言层、GQA 注意力和视觉语言衔接。"),
    ("m238_prefill_runtime", "执行 T32 预填充的输入打包、预取、FPGA 调用和结果收集。"),
    ("m231_prefill_runtime", "复用预填充输出解析与运行时缓冲区。"),
    ("m230_prefill_runtime", "提供预填充运行时基础实现和 FPGA 描述符调度。"),
    ("board_runtime", "通过 PYNQ/XRT 调用 KV260 FPGA、配置 DMA、搬运权重并收集执行证据。"),
    ("contract_runtime", "读取语言矩阵与 LM Head 合同，校验权重布局和调用描述符。"),
    ("reserved_ddr_pool", "管理为板端低地址/保留 DDR 路径使用的缓冲区。"),
    ("board_preprocess", "把视频画面整理为视觉塔要求的像素与位置张量。"),
    ("ps_vision_runtime", "在 PS 上加载视觉塔并运行视觉特征提取。"),
    ("modeling_mage_vl", "定义 Mage-VL 模型视觉/语言模块及前向结构。"),
    ("configuration_mage_vl", "定义 Mage-VL 模型配置及结构参数。"),
    ("video_language_runtime", "衔接视觉特征、文本 embedding、Prefill 和增量 Decode。"),
    ("video_prompt", "构造多模态视频提示与视觉占位符。"),
    ("video_request", "校验视频请求并组织固定帧输入。"),
    ("m246_knife_binary", "以受限 0/1 logits 输出执行刀具二元判定。"),
    ("m276_prompt_contract", "冻结 BACT 视频二元任务提示、预处理与 Token 预算合同。"),
    ("m276_video_runtime", "将固定视图视觉特征接入 159-token 语言输入。"),
    ("m277_fixed_window_gate", "在 KV260 上验证固定视频窗口的身份、输出和时延。"),
    ("m273_latest_vision_runtime", "运行末帧两视图、98 视觉 Token 的 PS 视觉塔。"),
    ("m261_budgeted_w4_runtime", "实现有界 W4 视觉权重缓存与计算预算。"),
    ("m325_full_session_board", "同一板端会话测量固定视频首 Token 和连续增量 Decode。"),
    ("m325_full_session_runtime", "在实验核中区分 T32 Prefill 与 Decode-one 配置。"),
    ("m325_resume_gate", "核对已通过固定文本门禁后只重跑失败的视频级别。"),
    ("m325_collect_full_session", "从 COM3 日志提取同会话性能并严格校验数值与恢复标记。"),
    ("selector_v2", "按固定 T32 批边界与质量代理选择跨模态 Token 预算。"),
    ("exact_vision_cache", "对图像身份和视觉特征进行精确缓存校验。"),
    ("feature_budget", "根据视觉特征选择保留 Token 并计算压缩预算。"),
    ("token_layout", "定义与核对视觉、文本 Token 的布局和边界。"),
    ("decode_one", "实现并测试单 Token FPGA Decode 实验算术路径。"),
    ("mage_prefill_m89x_runtime", "实现稳定 T32 FPGA 预填充算术核与链式输出接口。"),
)

LANGUAGE = {".py": "python", ".sh": "bash", ".ps1": "powershell", ".cpp": "cpp",
            ".hpp": "cpp", ".h": "cpp", ".tcl": "tcl", ".js": "javascript",
            ".html": "html", ".css": "css", ".json": "json"}


def safe_path(path: Path) -> Path:
    resolved = path.resolve(strict=True)
    if not resolved.is_relative_to(WORKSPACE):
        raise RuntimeError(f"source escapes workspace: {path}")
    if not resolved.is_file():
        raise RuntimeError(f"not a source file: {path}")
    return resolved


def collect() -> dict[Path, str]:
    chosen: dict[Path, str] = {}
    for relative, state in ROOTS:
        folder = (WORKSPACE / relative).resolve(strict=True)
        if not folder.is_relative_to(WORKSPACE):
            raise RuntimeError("source root escapes workspace")
        for path in folder.rglob("*"):
            if (path.is_file() and path.suffix.lower() in SUFFIXES and
                    "__pycache__" not in path.parts):
                chosen[safe_path(path)] = state
    for relative, state in EXTRA_FILES:
        chosen[safe_path(WORKSPACE / relative)] = state

    # HLS source uses quoted relative includes across sibling directories.
    pending = [path for path in chosen if path.suffix.lower() in {".cpp", ".hpp", ".h"}]
    while pending:
        parent = pending.pop()
        source = parent.read_text(encoding="utf-8-sig")
        for include in re.findall(r'^\s*#\s*include\s*"([^"]+)"', source, re.MULTILINE):
            target = parent.parent / include
            if not target.is_file():
                raise RuntimeError(f"missing quoted HLS include: {parent}: {include}")
            target = safe_path(target)
            if target not in chosen:
                chosen[target] = "稳定/实验 HLS 的递归本地头文件与算术依赖"
                if target.suffix.lower() in {".cpp", ".hpp", ".h"}:
                    pending.append(target)
    return chosen


def explanation(path: Path, state: str) -> str:
    name = path.stem.lower()
    for marker, description in DESCRIPTIONS:
        if marker in name:
            return f"状态：{state}。功能：{description}"
    if path.suffix.lower() == ".json":
        detail = "保存算法协议或选择器的固定配置与约束。"
    elif path.suffix.lower() == ".tcl":
        detail = "定义 HLS 仿真、综合、导出或资源门禁的工具命令。"
    elif name.startswith("test_") or name.startswith("tb_"):
        detail = "为同目录实现提供数值、接口或硬件行为回归测试。"
    elif "verify" in name or "preflight" in name or "probe" in name:
        detail = "在运行前验证包身份、依赖闭包和环境条件，并拒绝不满足门禁的输入。"
    elif "gate" in name or "accept" in name:
        detail = "执行该阶段的固定验收门禁并保存结果证据。"
    elif "runtime" in name:
        detail = "提供该阶段运行时的数据准备、算子执行及输出处理。"
    elif "video_server" in name:
        detail = "提供视频网页服务的请求处理和结果推送。"
    elif path.suffix.lower() == ".js":
        detail = "实现网页端的视频采集、请求和状态更新逻辑。"
    elif path.suffix.lower() == ".html":
        detail = "定义网页界面结构及监控信息区域。"
    elif path.suffix.lower() == ".css":
        detail = "定义网页配色、布局与状态样式。"
    elif path.suffix.lower() in {".sh", ".ps1"}:
        detail = "按固定顺序执行打包、环境检查、板端门禁或恢复流程。"
    elif path.suffix.lower() in {".cpp", ".hpp", ".h"}:
        detail = "实现 FPGA 计算核、接口定义或相应测试夹具。"
    else:
        detail = "实现该模块的算法、数据处理或调度逻辑。"
    return f"状态：{state}。功能：{detail}文件名：{path.name}。"


def decode_source(raw: bytes, path: Path) -> str:
    if raw.startswith(b"\xff\xfe"):
        text = raw.decode("utf-16")
    elif raw.startswith(b"\xef\xbb\xbf"):
        text = raw.decode("utf-8-sig")
    else:
        text = raw.decode("utf-8")
    if "\x00" in text:
        raise RuntimeError(f"NUL in source: {path}")
    return text


def main() -> None:
    selected = collect()
    if len(selected) < 150:
        raise RuntimeError(f"unexpectedly small source closure: {len(selected)}")
    if OUTPUT.exists():
        raise RuntimeError("output exists; do not overwrite without an explicit revision")
    ordered = sorted(selected, key=lambda path: path.relative_to(WORKSPACE).as_posix().lower())
    preface = (
        "# KV260 Mage-VL 4B 代码汇编\n\n"
        "范围：当前稳定 M254/M120/T32 网页部署链、BACT 固定视频与离线算法、"
        "以及明确标注为未替换稳定版的 Decode-one 实验代码。"
        "只收录本工作区可核对的第一方源文件和少量协议配置；"
        "不收录模型权重、bitstream、生成 RTL、第三方库、缓存或历史废弃候选。"
        "因此本文件不是可直接运行的整机镜像。\n\n"
        "当前网页默认 Build：`0x4D395832`；Decode-one `0x4F503131` 未晋级。"
        "每块的代码均为对应路径的完整原文，功能块为中文说明并附源文件 SHA-256。\n\n"
        f"代码文件数：**{len(ordered)}**。分隔线固定为 20 个等号。\n\n"
    )
    parts: list[bytes] = [preface.encode("utf-8")]
    slices: list[tuple[int, int, bytes, Path]] = []
    offset = len(parts[0])
    for index, path in enumerate(ordered):
        raw = path.read_bytes()
        content = decode_source(raw, path)
        relative = path.relative_to(WORKSPACE).as_posix()
        fence = "`" * max(3, max((len(x) for x in re.findall(r"`+", content)), default=0) + 1)
        opening = (f"代码路径头：`{relative}`\n\n代码块：\n{fence}{LANGUAGE[path.suffix.lower()]}\n")
        code = content.encode("utf-8")
        footer_newline = "" if content.endswith("\n") else "\n"
        closing = (f"{footer_newline}{fence}\n\n功能块：{explanation(path, selected[path])} "
                   f"源文件 SHA-256：`{hashlib.sha256(raw).hexdigest()}`。\n")
        if index:
            between = ("\n" + SEPARATOR + "\n\n").encode("utf-8")
            parts.append(between)
            offset += len(between)
        opener = opening.encode("utf-8")
        parts.append(opener)
        offset += len(opener)
        slices.append((offset, offset + len(code), code, path))
        parts.append(code)
        offset += len(code)
        closer = closing.encode("utf-8")
        parts.append(closer)
        offset += len(closer)
    output_bytes = b"".join(parts)
    OUTPUT.write_bytes(output_bytes)
    observed = OUTPUT.read_bytes()
    if observed != output_bytes or observed.count(b"\n" + SEPARATOR.encode() + b"\n") != len(ordered) - 1:
        raise RuntimeError("generated Markdown verification failed")
    for start, end, code, path in slices:
        if observed[start:end] != code:
            raise RuntimeError(f"incomplete code block: {path}")
    print(f"CODEBOOK_PASS files={len(ordered)} bytes={len(observed)} "
          f"sha256={hashlib.sha256(observed).hexdigest()} output={OUTPUT}")


if __name__ == "__main__":
    main()
