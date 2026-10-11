#!/usr/bin/env python3
"""Generate conservative application/resume wording from hash-locked BACT evidence."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path


SOURCES = {
    "selector": (
        "deployment/mage_vl4b/M288_BACT_SELECTOR_RESULT.json",
        "a7a53496933925e39193adc773692bede2d2f8543a207c58670a6a3559ed7b08",
    ),
    "board": (
        "deployment/mage_vl4b/M294R3_COUNTERBALANCED_BOUNDARY_BOARD_RESULT_05.json",
        "1a8138f92fc9340b1e5c660f886729cd725280d29877863af54cdd12aef895d1",
    ),
    "human_workbook": (
        "deployment/mage_vl4b/M296_HUMAN_REVIEW_WORKBOOK_RESULT.json",
        "4d4a9d84148fc220ba7ea70070cbbd351749ffb53cd332a25c26869bf90715f7",
    ),
    "cost_model": (
        "deployment/mage_vl4b/M297_BACT_STAIRCASE_COST_MODEL_RESULT.json",
        "74b2205f532ab63caf623c1da5af2dbf0cb7e24214bdc9650a487f794debfbb2",
    ),
    "evaluation_protocol": (
        "deployment/mage_vl4b/M299_BACT_EVALUATION_PROTOCOL_RESULT.json",
        "125c5ad99c7c02f4d5a91ba5b3f550d37ce1f283871cb4039312a1e4d6ea4201",
    ),
    "resources": (
        "deployment/mage_vl4b/M300_BACT_RESOURCE_BINDING_RESULT.json",
        "7a6e1b41a7199cf1164c02e350d637089fd471665ffc05fed79fc707d2c85e86",
    ),
    "hardware_robustness": (
        "deployment/mage_vl4b/M302_BACT_HARDWARE_ROBUSTNESS_RESULT.json",
        "2b4de170dc3d5df693d0010508e232c8d7e2c76b858003848b0284d57725fd86",
    ),
}


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def atomic_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    partial = path.with_suffix(path.suffix + ".partial")
    partial.write_text(text, encoding="utf-8")
    os.replace(partial, path)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--workspace", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--result", type=Path, required=True)
    args = parser.parse_args()
    root = args.workspace.resolve()

    data: dict[str, dict] = {}
    source_index: dict[str, dict[str, str]] = {}
    for name, (relative, expected_hash) in SOURCES.items():
        path = root / relative
        observed_hash = sha256(path)
        if observed_hash != expected_hash:
            raise RuntimeError(
                f"M303_SOURCE_HASH_FAIL name={name} expected={expected_hash} observed={observed_hash}"
            )
        data[name] = json.loads(path.read_text(encoding="utf-8"))
        source_index[name] = {"path": relative, "sha256": observed_hash}

    expected_status = {
        "selector": "PASS_ALGORITHM_AND_SYNTHETIC_CONTRACT",
        "board": "PASS_COUNTERBALANCED_PILOT",
        "human_workbook": "PASS_WORKBOOK_READY_PENDING_HUMAN_REVIEW",
        "cost_model": "PASS_REPRODUCIBLE_DESCRIPTIVE_MODEL_NOT_CAUSAL",
        "evaluation_protocol": "PASS_PROTOCOL_SYNTHETIC_REAL_LABELS_PENDING",
        "resources": "PASS_IMPLEMENTED_RESOURCES_BOUND_TO_BOARD_EXECUTED_BUILD",
        "hardware_robustness": "PASS_THREE_BOUNDARY_HARDWARE_ROBUSTNESS_PILOT_SEMANTIC_PENDING",
    }
    for name, status in expected_status.items():
        if data[name].get("status") != status:
            raise RuntimeError(f"M303_SOURCE_STATUS_FAIL name={name}")

    selected = data["selector"]["selected"]
    ratio = selected["fixed_ratio_visual_pruning"]
    bact = selected["bact"]
    count = selected["token_count_aware"]
    call_reduction = (ratio["logical_calls"] - bact["logical_calls"]) / ratio["logical_calls"] * 100.0
    retained = bact["candidate"]["total_tokens"] - count["candidate"]["total_tokens"]
    robustness = data["hardware_robustness"]["hardware_robustness"]
    implementation = data["resources"]["implementation"]
    resources = implementation["resources"]
    build_id = data["resources"]["build_id"].upper().replace("0X", "0x")
    human_complete = bool(data["human_workbook"]["human_review_complete"])
    if human_complete:
        raise RuntimeError("M303_UNEXPECTED_HUMAN_COMPLETE_REGENERATE_WITH_FINAL_ACCURACY_PIPELINE")

    lines = [
        "# BACT 申报书与简历可信表述包（M303，准确率待补）",
        "",
        "> 本文件由哈希锁定证据自动生成。标为“可立即使用”的句子只陈述已验证事实；标为",
        "> “待解锁”的句子在真实人工标签与 held-out 评测完成前不得复制到申报书、答辩或简历。",
        "",
        "## 1. 一句话项目定义",
        "",
        "面向固定执行粒度边缘加速器，研究跨模态 Token 数量与离散硬件批次不连续对应的问题，",
        "提出 BACT（Boundary-Aligned Cross-modal Token Budgeting），在任务质量约束下以尽可能小的",
        "语义信息损失跨越批边界，从而消除完整的 FPGA 逻辑调用批次。",
        "",
        "## 2. 申报书核心创新点（可立即使用）",
        "",
        "现有视觉 Token 裁剪通常以压缩率或剩余 Token 数为主要目标，但对固定 T32 执行粒度的",
        "边缘加速器，同一 32-Token 区间内继续裁剪并不会减少语言链的逻辑 FPGA 调用。项目提出",
        "跨模态 Token 批边界对齐方法，联合配置视觉视图、视觉 Token 和文本 Prompt，以",
        "`B=ceil(N/32)`、`Calls=154B+8` 建立目标硬件的阶梯成本，并按“先满足任务质量与内存",
        "约束，再最小化批次数，同批次内最小化语义损失并尽量保留信息”的规则选择配置。",
        "该创新严格限定为对固定执行粒度的跨模态预算对齐，不宣称首创 Token 裁剪、硬件感知",
        "优化或双通道监控。",
        "",
        "## 3. 已验证的关键结果（可立即使用）",
        "",
        f"- 在 KV260 Build `{build_id}`、kernel `{data['resources']['kernel']}` 上完成 27 点反平衡实板实验；",
        "  127/128/129、159/160/161、191/192/193 三个边界邻域全部获得有限输出，累计逻辑",
        f"  FPGA 调用 `{data['resources']['board_execution_binding']['observed_logical_fpga_calls_including_warmup']}/"
        f"{data['resources']['board_execution_binding']['expected_logical_fpga_calls_including_warmup']}` 精确匹配。",
        f"- 三个跨边界时延阶跃为 `{robustness['latency_step_values_ms'][0]:.3f}/"
        f"{robustness['latency_step_values_ms'][1]:.3f}/{robustness['latency_step_values_ms'][2]:.3f} ms`，",
        f"  均值 `{robustness['latency_step_mean_ms']:.3f} ms`、CV `{robustness['latency_step_cv_percent']:.4f}%`；",
        f"  每个边界的调用阶跃均为 `{robustness['exact_logical_call_step_each_boundary'][0]}`。",
        f"- `{ratio['candidate']['candidate_id']} → {bact['candidate']['candidate_id']}` 仅减少 5 Token，",
        f"  却将 T32 批次从 {ratio['batches']} 降至 {bact['batches']}，逻辑 calls 从",
        f"  {ratio['logical_calls']} 降至 {bact['logical_calls']}（结构下降 `{call_reduction:.2f}%`）。",
        f"- `{count['candidate']['candidate_id']}` 与 `{bact['candidate']['candidate_id']}` 均为",
        f"  {bact['batches']} 批/{bact['logical_calls']} calls，而 BACT 多保留 `{retained}` Token；",
        "  这证明“更少 Token”不等于“更低固定粒度硬件调用成本”，但语义优势仍待真实标签验证。",
        f"- 与实板 Build 身份绑定的实现资源为 LUT `{resources['clb_luts']['used']}/"
        f"{resources['clb_luts']['available']} ({resources['clb_luts']['reported_utilization_percent']:.2f}%)`、",
        f"  BRAM `{resources['block_ram_tiles']['used']}/{resources['block_ram_tiles']['available']} "
        f"({resources['block_ram_tiles']['reported_utilization_percent']:.2f}%)`、",
        f"  URAM `{resources['uram']['used']}/{resources['uram']['available']} "
        f"({resources['uram']['reported_utilization_percent']:.2f}%)`、",
        f"  DSP `{resources['dsps']['used']}/{resources['dsps']['available']} "
        f"({resources['dsps']['reported_utilization_percent']:.2f}%)`；",
        f"  WNS/WHS 为 `+{implementation['wns_ns']:.3f}/+{implementation['whs_ns']:.3f} ns`，",
        "  routing error 与 serious DRC 均为 0。",
        "",
        "## 4. 简历表述",
        "",
        "### 当前可直接使用的一条",
        "",
        f"- 面向 KV260 固定 T32 执行粒度设计并实现 BACT 跨模态 Token 批边界对齐策略，建立",
        f"  `ceil(N/32)` 阶梯成本模型；通过 27 点反平衡实板实验验证 3 组批边界调用阶跃均为",
        f"  154、平均时延阶跃 `{robustness['latency_step_mean_ms']/1000.0:.3f} s`（CV",
        f"  `{robustness['latency_step_cv_percent']:.3f}%`），并将资源/时序与实板 Build 哈希绑定。",
        "",
        "### 人工标签完成后才可解锁的第二条模板",
        "",
        "- 构建固定高质量、固定比例裁剪、Token-count-aware 与 BACT 四基线，在源视频级独立的",
        "  calibration/test 集上取得刀具 Recall=`[[待实测]]`、FAR=`[[待实测]]`、动作",
        "  Macro-F1=`[[待实测]]`，并完成低照度、遮挡、小目标及阈值扰动分析。",
        "",
        "该模板现在不可使用；方括号不得用文件名提示、合成标签或估算值填写。",
        "",
        "## 5. 对“优秀档次”五项标准的当前对应",
        "",
        "| 标准 | 当前判断 | 证据与缺口 |",
        "|---|---|---|",
        "| 方法/架构小创新 | 已形成可复现方法 | M288 选择器、阶梯成本模型与四基线身份已冻结；创新边界有明确限定 |",
        "| 仿真/离线 + 实物实测闭环 | 硬件成本现象已闭环 | 离线结构合同与 27 点 KV260 实板阶梯一致；目标场景语义闭环仍待人工标签 |",
        "| 正式外化成果 | 部分完成 | 代码、JSON、报告已形成；公开仓库、软著/摘要/Poster 尚未完成 |",
        "| 稳健性/灵敏度 | 硬件先导完成、语义待完成 | 三边界阶跃 CV 0.7844%；低照度/遮挡/小刀具与阈值敏感度待真实标签 |",
        "| 真实工程痛点 | 问题与原型成立、外部有效性待补 | 解决 Token 减少但硬件批次不降的浪费；AI 生成先导数据不能代表真实工厂 |",
        "",
        "目前可以可信地说：创新点和硬件阶梯验证闭环已经具备；不能说整个监控系统准确、实时、",
        "优于 GPU/CPU，或已证明真实工厂泛化。",
        "",
        "## 6. 答辩时禁止混淆的边界",
        "",
        "- `Calls` 是逻辑 FPGA 调用数，不是功耗、吞吐或总时延。",
        "- 约 20.12 秒是当前实板语言 Prefill 跨一个 T32 批边界的先导时延阶跃，不是完整 4B TTFT。",
        "- M288 JSON 中的精度字段是选择器合成测试 fixture，不是真实视频准确率，本文件不引用它们。",
        "- 12 个 AI 生成视频只能用于一周先导实验；真实工厂/真实摄像头外部有效性必须另补。",
        "- 当前 BACT 在 PS 选择配置并复用不变 T32 bitstream，因此新增 PL 资源为 0；这不表示",
        "  整个 T32 加速器资源为 0。",
        "- 没有动态功耗仪表、充分重复和真实标签时，不得写能效领先、因果提速或准确率提升。",
        "",
        "## 7. 待解锁指标与固定触发条件",
        "",
        "| 待填字段 | 解锁条件 | 当前值 |",
        "|---|---|---|",
        "| 四基线刀具 Recall/FAR | 12/12 人工复核 PASS；calibration 冻结阈值；test 只评一次 | 未解锁 |",
        "| 五类动作 Macro-F1 | test 覆盖五类动作且 logits/ID/finite 门禁 PASS | 未解锁 |",
        "| 语义稳健性 | 低照度、遮挡、小刀具、动作类别、刀具正负切片均有真实标签 | 未解锁 |",
        "| 动态功耗/能效 | 同一仪表、同一任务、空闲基线和运行功率实测 | 未解锁 |",
        "| 真实工厂泛化 | 新增真实监控源视频级独立外部测试集 | 未解锁 |",
        "",
        "## 8. 证据索引",
        "",
    ]
    for name, item in source_index.items():
        lines.append(f"- `{name}`: `{item['path']}` — SHA-256 `{item['sha256']}`")
    lines.append("")

    output = (root / args.output).resolve()
    result = (root / args.result).resolve()
    if not output.is_relative_to(root) or not result.is_relative_to(root):
        raise RuntimeError("M303_OUTPUT_PATH_ESCAPE")
    atomic_text(output, "\n".join(lines))

    result_payload = {
        "date": "2026-09-03",
        "gate": "M303-evidence-backed-application-and-resume-claim-pack",
        "status": "PASS_VERIFIED_CLAIMS_PACK_ACCURACY_FIELDS_LOCKED",
        "classification": (
            "Hash-derived application/resume wording for verified BACT method, board staircase and resource facts. "
            "Human-labelled accuracy, semantic robustness, dynamic power, powered causality, real-time and real-world "
            "external validity remain locked and are not estimated."
        ),
        "output": str(output.relative_to(root)).replace("\\", "/"),
        "output_sha256": sha256(output),
        "source_index": source_index,
        "verified_claims_available": True,
        "human_accuracy_claim_available": False,
        "semantic_robustness_claim_available": False,
        "dynamic_power_claim_available": False,
        "powered_causal_speed_claim_available": False,
        "real_time_claim_available": False,
        "real_world_external_validity_claim_available": False,
        "board_execution_run": False,
        "active_m254_m256_changed": False,
        "boot_dtb_cma_partitions_changed": False,
        "stable_rollback_preserved": True,
        "next_gate": (
            "Complete M296 human review, import immutable labels, collect all four frozen baseline predictions, "
            "freeze calibration thresholds and evaluate held-out test once before regenerating the final claim pack."
        ),
    }
    atomic_text(result, json.dumps(result_payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n")
    print(
        "M303_BACT_CLAIM_PACK_PASS "
        f"output_sha256={result_payload['output_sha256']} human_accuracy=false"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
