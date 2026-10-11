#!/usr/bin/env python3
"""Generate the evidence-backed BACT experiment report without inventing gaps."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path


SOURCES = {
    "selector": "deployment/mage_vl4b/M288_BACT_SELECTOR_RESULT.json",
    "board_staircase": "deployment/mage_vl4b/M294R3_COUNTERBALANCED_BOUNDARY_BOARD_RESULT_05.json",
    "cost_model": "deployment/mage_vl4b/M297_BACT_STAIRCASE_COST_MODEL_RESULT.json",
    "human_import": "deployment/mage_vl4b/M298_HUMAN_REVIEW_IMPORT_RESULT.json",
    "evaluation_protocol": "deployment/mage_vl4b/M299_BACT_EVALUATION_PROTOCOL_RESULT.json",
    "resource_binding": "deployment/mage_vl4b/M300_BACT_RESOURCE_BINDING_RESULT.json",
}


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load(root: Path, relative: str) -> dict:
    return json.loads((root / relative).read_text(encoding="utf-8"))


def f3(value: float) -> str:
    return f"{value:.3f}"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--workspace", type=Path, required=True)
    parser.add_argument("--report", type=Path, required=True)
    parser.add_argument("--result", type=Path, required=True)
    args = parser.parse_args()
    root = args.workspace.resolve()
    data = {name: load(root, relative) for name, relative in SOURCES.items()}
    source_hashes = {name: digest(root / relative) for name, relative in SOURCES.items()}

    if data["selector"]["status"] != "PASS_ALGORITHM_AND_SYNTHETIC_CONTRACT":
        raise RuntimeError("M301_SELECTOR_SOURCE_FAIL")
    if data["board_staircase"]["status"] != "PASS_COUNTERBALANCED_PILOT":
        raise RuntimeError("M301_BOARD_SOURCE_FAIL")
    if data["cost_model"]["status"] != "PASS_REPRODUCIBLE_DESCRIPTIVE_MODEL_NOT_CAUSAL":
        raise RuntimeError("M301_COST_SOURCE_FAIL")
    if data["evaluation_protocol"]["status"] != "PASS_PROTOCOL_SYNTHETIC_REAL_LABELS_PENDING":
        raise RuntimeError("M301_EVAL_PROTOCOL_SOURCE_FAIL")
    if data["resource_binding"]["status"] != "PASS_IMPLEMENTED_RESOURCES_BOUND_TO_BOARD_EXECUTED_BUILD":
        raise RuntimeError("M301_RESOURCE_SOURCE_FAIL")

    selected = data["selector"]["selected"]
    boundary_rows = data["cost_model"]["boundary_contrasts"]
    model = data["cost_model"]["empirical_latency_model"]
    resources = data["resource_binding"]["implementation"]["resources"]
    human_ready = data["human_import"]["formalAccuracyAllowed"]

    lines = [
        "# BACT 可复现实验报告（证据锁定草案）",
        "",
        "> 版本：M301，2026-09-03。本文只陈述当前文件能够证明的事实；人工准确率、动态功耗、",
        "> 有统计功效的因果加速和实时性尚无证据时均明确标为未完成。",
        "",
        "## 1. 项目问题与方法",
        "",
        "固定执行粒度 FPGA 的实际开销不是 Token 数量的连续函数。对当前 KV260 T32 语言链，",
        "少量裁剪只有跨过 32-Token 批边界时，才会消除一个完整权重扫描/逻辑调用批次；同一批次",
        "内继续删 Token 可能损失语义信息，却不减少这部分硬件调用。",
        "",
        "BACT（Boundary-Aligned Cross-modal Token Budgeting）联合选择视觉视图、视觉 Token 与",
        "文本 Prompt 预算，在冻结的任务质量与内存约束下采用字典序目标：",
        "",
        "1. 最小化固定粒度批次数；",
        "2. 同批次数内最小化语义损失；",
        "3. 再最大化保留的信息量，并以较低内存打破后续平局。",
        "",
        "当前方法的区别限定为“跨模态预算对齐目标加速器的固定批边界”，不宣称首创所有硬件感知",
        "Token 裁剪，也不把双通道监控结构本身当作核心创新。",
        "",
        "## 2. 正式成本模型",
        "",
        "结构模型对当前冻结链是精确恒等式：",
        "",
        "```text",
        "B(N)     = ceil(N / 32)",
        "Calls(N) = 154 * B(N) + 8",
        "```",
        "",
        "其中 `Calls` 是语言 Prefill 逻辑 FPGA 调用数，不等于总时延、功耗或系统全部开销。",
        "M297 基于一次 runtime/vision 加载下的 27 个真实 KV260 点，拟合描述性模型：",
        "",
        "```text",
        f"L_hat_ms(N) = {f3(model['beta0_ms'])} + {f3(model['beta_batch_ms'])} * ceil(N/32)",
        f"              + {model['beta_token_ms']:.6f} * N",
        "```",
        "",
        f"九个 Token 中位数点 `R²={model['r_squared_on_nine_token_medians']:.9f}`，RMSE "
        f"`{f3(model['rmse_ms_on_nine_token_medians'])} ms`；留一边界 RMSE "
        f"`{f3(data['cost_model']['leave_one_boundary_out']['rmse_ms'])} ms`。该式只允许在实测 "
        "`127–193 Token` 范围内做描述，不允许外推到 284 Token。",
        "",
        "## 3. 四类冻结基线",
        "",
        "| 方法 | 冻结配置 | 总 Token | T32 批次 | 逻辑 FPGA Calls | 选择原则 |",
        "|---|---:|---:|---:|---:|---|",
    ]
    baseline_order = ["fixed_high_quality", "fixed_ratio_visual_pruning", "token_count_aware", "bact"]
    names = {
        "fixed_high_quality": "固定高质量",
        "fixed_ratio_visual_pruning": "固定比例裁剪",
        "token_count_aware": "Token-count-aware",
        "bact": "BACT",
    }
    for key in baseline_order:
        row = selected[key]
        c = row["candidate"]
        lines.append(
            f"| {names[key]} | `{c['candidate_id']}` | {c['total_tokens']} | {row['batches']} | "
            f"{row['logical_calls']} | {row['reason']} |"
        )
    lines += [
        "",
        "`count-144` 与 `bact-159` 都是 5 批、778 calls；BACT 在结构成本相同的条件下多保留",
        "15 Token。`ratio-164 → bact-159` 仅减少 5 Token，却跨过 160 边界，使 calls 从 932",
        "降至 778（结构下降 16.52%）。这仍需人工标注集证明语义质量没有越过门槛。",
        "",
        "## 4. 三组实板批边界",
        "",
        "| 邻域 | 同批平台变化 (ms) | 跨边界阶梯 (ms) | 同批 MAD 噪声底 (ms) | 结论 |",
        "|---:|---:|---:|---:|---|",
    ]
    for row in boundary_rows:
        lines.append(
            f"| {row['boundary']-1}/{row['boundary']}/{row['boundary']+1} | "
            f"{f3(row['same_batch_delta_ms'])} | {f3(row['cross_boundary_step_ms'])} | "
            f"{f3(row['same_batch_mad_noise_floor_ms'])} | 阶梯大于同批 MAD |"
        )
    step = data["cost_model"]["cross_boundary_step_summary"]
    lines += [
        "",
        f"三个跨边界阶梯中位数为 `{f3(step['median_ms'])} ms`，均值为 `{f3(step['mean_ms'])} ms`。",
        "每个 Token 长度只有 3 次，故这是 counterbalanced pilot distribution，只支持结构阶梯和",
        "先导时延阶梯表述，不支持有统计功效的因果加速结论。",
        "",
        "## 5. FPGA 实现与实板身份",
        "",
        f"Vivado full-shell 与实板运行均为 Build `{data['resource_binding']['build_id']}`、kernel "
        f"`{data['resource_binding']['kernel']}`。WNS/WHS 为 "
        f"`+{data['resource_binding']['implementation']['wns_ns']:.3f}/+{data['resource_binding']['implementation']['whs_ns']:.3f} ns`，",
        "routing error 和 serious DRC 均为 0。",
        "",
        "| 资源 | 使用 | 可用 | 利用率 | 余量 |",
        "|---|---:|---:|---:|---:|",
    ]
    resource_names = {
        "clb_luts": "CLB LUT",
        "clb_registers": "CLB Register",
        "block_ram_tiles": "BRAM Tile",
        "uram": "URAM",
        "dsps": "DSP",
    }
    for key in ("clb_luts", "clb_registers", "block_ram_tiles", "uram", "dsps"):
        value = resources[key]
        lines.append(
            f"| {resource_names[key]} | {value['used']} | {value['available']} | "
            f"{value['reported_utilization_percent']:.2f}% | {value['headroom']} |"
        )
    lines += [
        "",
        "DSP 85.74% 是最紧约束，因此后续 T64/T128 只能做时分复用/循环重排，不应复制 MAC 阵列。",
        "当前 BACT 选择器在 PS 上运行并复用同一 bitstream，所以相对 Build 0x4D395832 的新增 PL",
        "资源为 0。动态功耗尚未实测。",
        "",
        "## 6. 目标场景数据与评测协议",
        "",
        "M296 已锁定 12 个互不重复的 AI 生成先导视频：6 个 calibration、6 个 held-out test，",
        "共抽样 300 帧。文件名提示不是 ground truth；每个视频必须由人完整观看并确认动作、刀具",
        "状态及全片恒定性。当前人工复核状态：",
        "",
        f"- QC PASS：`{data['human_import']['qcPassCount']}/12`",
        f"- 待复核：`{data['human_import']['pendingCount']}`",
        f"- 真实准确率允许计算：`{str(human_ready).lower()}`",
        "- 数据外部有效性：仅 AI-generated pilot，不代表真实工厂分布",
        "",
        "M299 已实现但尚未对真实标签开放：",
        "",
        "- 每个 baseline 只用 calibration 冻结刀具阈值；",
        "- held-out test 只打开一次；",
        "- 刀具指标：`Recall = TP/(TP+FN)`、`FAR = FP/(FP+TN)`；",
        "- 动作指标：WORKING/IDLE/WALKING/FALLING/FIGHTING 五类 Macro-F1；",
        "- 错误 baseline ID、缺少正负刀具、缺失任一动作或非有限输出均 fail-closed。",
        "",
        "## 7. 当前证据与声明边界",
        "",
        "| 主张 | 当前状态 | 证据/缺口 |",
        "|---|---|---|",
        "| BACT 正式选择算法 | 已实现 | M288 selector + 合成合同 |",
        "| T32 调用阶梯 | 已实板证明 | M294R3，27/27 点、23170/23170 calls |",
        "| 先导时延阶梯 | 已量化 | M297，约 20.14 s/跨批边界 |",
        "| 实现资源与时序 | 已绑定实板 Build | M300 |",
        "| 四基线准确率 | 未完成 | M296 仍需 12 个视频人工复核 |",
        "| 有统计功效的因果加速 | 未完成 | 每 Token 仅 3 次 |",
        "| 动态功耗/能效 | 未完成 | 无板端功率仪表数据 |",
        "| 秒级 4B 实时推理 | 不成立 | 当前证据不支持 |",
        "| 真实工厂泛化 | 未完成 | 目前只有 AI 生成先导视频 |",
        "",
        "## 8. 可复现入口",
        "",
        "Windows 必须使用固定 Python，不得调用不存在的裸 `python/python3`：",
        "",
        "```powershell",
        "$py = 'C:\\Users\\30429\\.cache\\codex-runtimes\\codex-primary-runtime\\dependencies\\python\\python.exe'",
        "& $py .\\scripts\\m297_test_bact_staircase_cost_model.py",
        "& $py .\\scripts\\m299_gate_bact_evaluation_protocol.py --workspace . --result .\\deployment\\mage_vl4b\\M299_BACT_EVALUATION_PROTOCOL_RESULT.json",
        "& $py .\\scripts\\m300_consolidate_bact_resource_evidence.py --workspace . --result .\\deployment\\mage_vl4b\\M300_BACT_RESOURCE_BINDING_RESULT.json",
        "```",
        "",
        "人工复核完成后运行（Node 路径同样固定）：",
        "",
        "```powershell",
        "$node = 'C:\\Users\\30429\\.cache\\codex-runtimes\\codex-primary-runtime\\dependencies\\node\\bin\\node.exe'",
        "& $node .\\scripts\\m298_import_human_review_workbook.mjs",
        "```",
        "",
        "## 9. 下一步固定顺序",
        "",
        "1. 人工完整观看并复核 12 个视频，使全部 QC=PASS；",
        "2. 导入不可变标签，确认 calibration/test 覆盖；",
        "3. 对四个冻结配置采集原始刀具分数与五类动作 logits；",
        "4. 仅用 calibration 冻结阈值；",
        "5. held-out test 只评一次，输出 Recall、FAR、Macro-F1；",
        "6. 做光照、遮挡、刀具尺寸、Prompt 长度和批边界灵敏度分析；",
        "7. 将最终指标、失败边界和声明范围写入申报书、Poster 和简历。",
        "",
        "## 10. 证据索引",
        "",
    ]
    for name, relative in SOURCES.items():
        lines.append(f"- `{relative}` — SHA-256 `{source_hashes[name]}`")
    lines.append("")

    report = "\n".join(lines)
    report_path = (root / args.report).resolve()
    if not report_path.is_relative_to(root):
        raise RuntimeError("M301_REPORT_PATH_ESCAPE")
    report_path.parent.mkdir(parents=True, exist_ok=True)
    partial_report = report_path.with_suffix(report_path.suffix + ".partial")
    partial_report.write_text(report, encoding="utf-8")
    os.replace(partial_report, report_path)

    result = {
        "date": "2026-09-03",
        "gate": "M301-evidence-backed-BACT-reproducible-report",
        "status": "PASS_REPORT_DRAFT_ACCURACY_PENDING",
        "classification": (
            "Deterministic evidence-backed report covering the formal method, four baselines, three board "
            "boundaries, cost model, implemented resources, evaluation protocol and explicit claim gaps. "
            "Human-labelled accuracy, dynamic power, powered causality and real-world validity remain pending."
        ),
        "report": str(report_path.relative_to(root)).replace("\\", "/"),
        "report_sha256": digest(report_path),
        "source_hashes": source_hashes,
        "human_accuracy_complete": human_ready,
        "dynamic_power_complete": False,
        "causal_speed_complete": False,
        "real_world_external_validity_complete": False,
        "board_execution_run": False,
        "active_m254_m256_changed": False,
        "boot_dtb_cma_partitions_changed": False,
        "stable_rollback_preserved": True,
        "next_gate": "Complete M296 human review, then regenerate this report after the one-shot held-out evaluation.",
    }
    result_path = (root / args.result).resolve()
    if not result_path.is_relative_to(root):
        raise RuntimeError("M301_RESULT_PATH_ESCAPE")
    result_path.parent.mkdir(parents=True, exist_ok=True)
    partial_result = result_path.with_suffix(result_path.suffix + ".partial")
    partial_result.write_text(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    os.replace(partial_result, result_path)
    print(f"M301_BACT_REPORT_PASS report_sha256={result['report_sha256']} accuracy_complete={str(human_ready).lower()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
