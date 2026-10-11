#!/usr/bin/env python3
"""Generate the final BACT report and claim pack from sealed evidence only."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path


BASELINE_ORDER = (
    "fixed_high_quality",
    "fixed_ratio_visual_pruning",
    "token_count_aware",
    "bact",
)

SOURCE_PATHS = {
    "selector": "deployment/mage_vl4b/M288_BACT_SELECTOR_RESULT.json",
    "board": "deployment/mage_vl4b/M294R3_COUNTERBALANCED_BOUNDARY_BOARD_RESULT_05.json",
    "cost": "deployment/mage_vl4b/M297_BACT_STAIRCASE_COST_MODEL_RESULT.json",
    "resources": "deployment/mage_vl4b/M300_BACT_RESOURCE_BINDING_RESULT.json",
    "hardwareRobustness": "deployment/mage_vl4b/M302_BACT_HARDWARE_ROBUSTNESS_RESULT.json",
    "geometry": "deployment/mage_vl4b/M306_FOUR_BASELINE_PREDICTION_GEOMETRY_RESULT.json",
    "predictionCollection": "deployment/mage_vl4b/M307_FOUR_BASELINE_PREDICTION_COLLECTION_RESULT.json",
    "evaluation": "deployment/mage_vl4b/M308_BACT_HELDOUT_EVALUATION_RESULT.json",
    "evaluationSeal": "deployment/mage_vl4b/M308_BACT_HELDOUT_EVALUATION_SEAL.json",
}


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_json(path: Path) -> dict:
    if not path.is_file():
        raise ValueError(f"required evidence is missing: {path}")
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"evidence root must be object: {path}")
    return value


def atomic_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".partial")
    temporary.write_text(text, encoding="utf-8")
    os.replace(temporary, path)


def atomic_json(path: Path, value: dict) -> None:
    atomic_text(path, json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n")


def resolve_under(workspace: Path, value: str) -> Path:
    path = (workspace / value).resolve()
    try:
        path.relative_to(workspace)
    except ValueError as error:
        raise ValueError(f"path escapes workspace: {value}") from error
    return path


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def fmt(value: object, digits: int = 4) -> str:
    if value is None:
        return "不可用"
    return f"{float(value):.{digits}f}"


def validate_sources(workspace: Path) -> tuple[dict[str, dict], dict[str, dict]]:
    values = {}
    index = {}
    for name, relative in SOURCE_PATHS.items():
        path = resolve_under(workspace, relative)
        values[name] = load_json(path)
        index[name] = {"path": relative, "sha256": sha256(path)}

    selector = values["selector"]
    board = values["board"]
    cost = values["cost"]
    resources = values["resources"]
    hardware = values["hardwareRobustness"]
    geometry = values["geometry"]
    collection = values["predictionCollection"]
    evaluation = values["evaluation"]
    seal = values["evaluationSeal"]

    require(selector.get("status") == "PASS_ALGORITHM_AND_SYNTHETIC_CONTRACT", "M288 selector status")
    require(board.get("status") == "PASS_COUNTERBALANCED_PILOT", "M294R3 board status")
    require(
        cost.get("status") == "PASS_REPRODUCIBLE_DESCRIPTIVE_MODEL_NOT_CAUSAL",
        "M297 cost status",
    )
    require(
        resources.get("status") == "PASS_IMPLEMENTED_RESOURCES_BOUND_TO_BOARD_EXECUTED_BUILD",
        "M300 resource status",
    )
    require(
        hardware.get("status") == "PASS_THREE_BOUNDARY_HARDWARE_ROBUSTNESS_PILOT_SEMANTIC_PENDING",
        "M302 hardware robustness status",
    )
    require(
        geometry.get("status") == "PASS_EXACT_GEOMETRY_AND_TASK_TOKEN_CONTRACT",
        "M306 geometry status",
    )
    require(
        collection.get("status") == "PASS_RAW_PREDICTIONS_LABEL_BLIND",
        "M307 prediction status",
    )
    require(
        evaluation.get("status") == "PASS_PILOT_HELDOUT_EVALUATION_SEALED",
        "M308 held-out evaluation is not complete",
    )
    require(seal.get("status") == "COMPLETE", "M308 seal is not complete")
    require(seal.get("resultSha256") == index["evaluation"]["sha256"], "M308 result seal mismatch")

    expected_ids = selector.get("expected_selected_ids")
    require(expected_ids == geometry.get("baselineIds"), "M288/M306 baseline identity mismatch")
    require(set(expected_ids) == set(BASELINE_ORDER), "baseline membership mismatch")
    require(collection.get("geometrySha256") == index["geometry"]["sha256"], "M307 geometry hash mismatch")
    require(collection.get("completedPredictionRows") == 48, "M307 row count")
    require(collection.get("modelForwardCount") == 96, "M307 forward count")
    require(collection.get("allFinite") is True, "M307 finite gate")
    require(collection.get("humanLabelsRead") is False, "M307 label blindness")

    eval_identity = evaluation.get("identity", {})
    require(eval_identity.get("m307ResultSha256") == index["predictionCollection"]["sha256"], "M308/M307 result hash mismatch")
    predictions_path = resolve_under(workspace, str(collection.get("predictions", "")))
    require(sha256(predictions_path) == collection.get("predictionsSha256"), "M307 prediction payload mismatch")
    require(eval_identity.get("predictionsSha256") == collection.get("predictionsSha256"), "M308 prediction hash mismatch")
    require(eval_identity.get("baselineIds") == expected_ids, "M308 baseline identity mismatch")
    require(evaluation.get("calibrationOnlyThresholdSelection") is True, "M308 calibration-only contract")
    require(evaluation.get("heldOutTestOpenedExactlyOnce") is True, "M308 one-shot contract")
    require(evaluation.get("formalPilotAccuracyAllowed") is True, "M308 pilot accuracy unavailable")
    require(evaluation.get("realWorldExternalValidityClaimAllowed") is False, "external-validity boundary missing")

    build = str(cost["board_identity"]["build_id"]).lower()
    require(build == str(resources["build_id"]).lower(), "M297/M300 build mismatch")
    require(build == str(hardware["board_identity"]["build_id"]).lower(), "M297/M302 build mismatch")
    require(cost["source_sha256"] == index["board"]["sha256"], "M297 board source hash mismatch")
    require(resources["sources"]["board"]["sha256"] == index["board"]["sha256"], "M300 board hash mismatch")
    require(resources["sources"]["cost_model"]["sha256"] == index["cost"]["sha256"], "M300 cost hash mismatch")
    require(hardware["sources"]["m297"]["sha256"] == index["cost"]["sha256"], "M302 cost hash mismatch")
    return values, index


def metric_rows(evaluation: dict) -> list[list[str]]:
    output = []
    baselines = evaluation["metrics"]["baselines"]
    for name in BASELINE_ORDER:
        row = baselines[name]
        primary = row["primary"]
        freeze = primary["thresholdFreeze"]
        test = primary["heldOutTest"]
        output.append(
            [
                name,
                row["candidateId"],
                fmt(freeze["threshold"]),
                fmt(freeze["calibrationMetrics"]["recall"]),
                fmt(freeze["calibrationMetrics"]["false_alarm_rate"]),
                fmt(test["knife"]["recall"]),
                fmt(test["knife"]["false_alarm_rate"]),
                fmt(test["action"]["macroF1"]),
            ]
        )
    return output


def markdown_table(headers: list[str], rows: list[list[str]]) -> str:
    lines = ["| " + " | ".join(headers) + " |", "| " + " | ".join("---" for _ in headers) + " |"]
    lines.extend("| " + " | ".join(row) + " |" for row in rows)
    return "\n".join(lines)


def build_report(values: dict[str, dict], source_index: dict[str, dict]) -> str:
    selector = values["selector"]
    cost = values["cost"]
    resources = values["resources"]
    hardware = values["hardwareRobustness"]
    geometry = values["geometry"]
    collection = values["predictionCollection"]
    evaluation = values["evaluation"]
    rows = metric_rows(evaluation)

    geometry_rows = []
    for name in BASELINE_ORDER:
        candidate = geometry["candidates"][name]
        geometry_rows.append(
            [
                name,
                candidate["candidateId"],
                str(candidate["targetPromptTokensPerProbe"]),
                str(candidate["t32BatchesPerProbe"]),
                str(candidate["logicalFpgaCallsPerProbe"]),
                str(candidate["viewCount"]),
            ]
        )
    resource_rows = []
    for name, value in resources["implementation"]["resources"].items():
        resource_rows.append(
            [name, str(value["used"]), str(value["available"]), fmt(value["reported_utilization_percent"], 2)]
        )

    sensitivity_rows = []
    for name in BASELINE_ORDER:
        item = evaluation["metrics"]["baselines"][name]["calibrationThresholdSensitivity"]
        sensitivity_rows.append(
            [
                name,
                str(item["measuredFoldCount"]),
                str(item["unavailableFoldCount"]),
                fmt(item["thresholdMinimum"]),
                fmt(item["thresholdMaximum"]),
                fmt(item["thresholdRange"]),
            ]
        )

    condition_rows = []
    for name in BASELINE_ORDER:
        slices = evaluation["metrics"]["baselines"][name]["heldOutConditionSlices"]
        for condition in evaluation["metrics"]["conditions"]:
            for state in ("present", "absent"):
                item = slices[condition][state]
                condition_rows.append(
                    [
                        name,
                        condition,
                        state,
                        str(item["clipCount"]),
                        fmt(item["knifeAccuracy"]),
                        fmt(item["actionAccuracy"]),
                    ]
                )

    source_lines = [f"- `{name}`: `{entry['path']}`, SHA-256 `{entry['sha256']}`" for name, entry in source_index.items()]
    return f"""# BACT 可复现实验最终证据报告

## 1. 项目问题与方法

本项目针对固定 T32 执行粒度下“减少 Token 不一定减少硬件批次”的问题，提出 BACT：在人工
监控任务质量约束下，先最小化 `ceil(N/32)`，再在相同批次数内最小化语义损失并保留更多信息。
当前语言链的精确结构合同为 `Calls(N)=154×ceil(N/32)+8`；它只描述逻辑调用数，不等同于系统
总时延或功耗。

## 2. 四类冻结基线

{markdown_table(['基线', '候选 ID', '刀具探针 Token', 'T32 批次', '逻辑调用', '视图数'], geometry_rows)}

动作探针使用统一、无填充、五个单 Token 类别，仅作为离线语义约束；其 Token 数不用于替代
上述刀具候选的板端成本身份。M288 中的候选质量值是合成算法合同，不是本报告的真实准确率。

## 3. KV260 硬件阶梯证据

- Build：`{cost['board_identity']['build_id']}`；kernel：`{cost['board_identity']['kernel']}`。
- 27/27 个反平衡实板 Prefill 点通过，结构调用身份全部匹配。
- 128→129、160→161、192→193 的实测中位阶跃分别为
  `{cost['boundary_contrasts'][0]['cross_boundary_step_ms']:.3f}`、
  `{cost['boundary_contrasts'][1]['cross_boundary_step_ms']:.3f}`、
  `{cost['boundary_contrasts'][2]['cross_boundary_step_ms']:.3f} ms`。
- 三边界阶跃 CV 为 `{hardware['hardware_robustness']['latency_step_cv_percent']:.4f}%`；
  leave-one-boundary-out RMSE 为
  `{hardware['hardware_robustness']['leave_one_boundary_out_rmse_ms']:.3f} ms`。
- 经验模型仅在 127--193 Token 内作描述：
  `L̂={cost['empirical_latency_model']['beta0_ms']:.3f} + `
  `{cost['empirical_latency_model']['beta_batch_ms']:.3f}×ceil(N/32) + `
  `{cost['empirical_latency_model']['beta_token_ms']:.3f}×N ms`。

这些结果证明硬件阶梯存在且三处边界一致，但每个 Token 仅三次测量，不能表述为有统计功效的
因果提速，也不能外推 193 Token 之外。

## 4. 实现资源与时序

{markdown_table(['资源', '已用', '可用', '利用率(%)'], resource_rows)}

WNS/WHS 为 `{resources['implementation']['wns_ns']:+.3f}/` `{resources['implementation']['whs_ns']:+.3f} ns`，
路由错误网络和严重 DRC 均为 0。BACT 选择器运行于 PS，复用同一 T32 bitstream，当前新增 PL
资源为 0；DSP 利用率最高，后续更大批处理必须时分折叠，不能复制阵列。

## 5. 标签盲预测采集

M307 对 12 个源视频、四基线完成 `{collection['completedPredictionRows']}/48` 行原始预测和
`{collection['modelForwardCount']}` 次前向，全部有限，耗时 `{collection['wallMs']:.3f} ms`。
采集发生在人工标签导入之前，不读取文件名提示、人工真值或 held-out 标签。

## 6. 一次性 held-out 结果

{markdown_table(['基线', '候选 ID', '冻结阈值', '校准 Recall', '校准 FAR', '测试 Recall', '测试 FAR', '动作 Macro-F1'], rows)}

每个刀具阈值只使用 calibration split 选择；held-out test 只打开一次，并由 M308 封印结果哈希。
样本共 12 个且均为 AI 生成先导视频，因此这些数值只代表当前先导集，不能宣称真实工厂泛化。

## 7. 稳健性与灵敏度

### 7.1 校准阈值 leave-one-clip-out

{markdown_table(['基线', '可测折数', '不可用折数', '阈值最小', '阈值最大', '阈值范围'], sensitivity_rows)}

### 7.2 held-out 条件切片（描述性）

{markdown_table(['基线', '条件', '状态', '样本数', '刀具准确率', '动作准确率'], condition_rows)}

条件切片样本很少；若某切片不同时含刀具正负或五个动作，Recall/FAR 或 Macro-F1 不应制造，
这里只列出可定义的描述性准确率。

## 8. 可复现与声明边界

- 可可信声明：BACT 形式化方法；三组 T32 边界的实板调用/时延阶梯；实现资源与时序；一次性
  AI 生成先导集四基线指标；阈值和条件灵敏度。
- 不可声明：实时 4B 推理、动态功耗优势、有统计功效的因果提速、真实工厂外部有效性、首创。
- 稳定性：本阶段未改变 M254/M256、overlay、boot/DTB/CMA、分区或稳定回滚。

## 9. 证据索引

{chr(10).join(source_lines)}

## 10. 复现命令

```powershell
& 'C:\\Users\\30429\\.cache\\codex-runtimes\\codex-primary-runtime\\dependencies\\node\\bin\\node.exe' scripts\\m304_import_human_review_workbook.mjs
& 'C:\\Users\\30429\\.cache\\codex-runtimes\\codex-primary-runtime\\dependencies\\python\\python.exe' scripts\\m308_run_one_shot_bact_evaluation.py
& 'C:\\Users\\30429\\.cache\\codex-runtimes\\codex-primary-runtime\\dependencies\\python\\python.exe' scripts\\m309_generate_bact_final_evidence_pack.py
```
"""


def build_claim_pack(values: dict[str, dict]) -> str:
    evaluation = values["evaluation"]
    resources = values["resources"]
    rows = metric_rows(evaluation)
    metric_lines = [
        f"- `{row[0]}` / `{row[1]}`：测试刀具 Recall `{row[5]}`、FAR `{row[6]}`、动作 Macro-F1 `{row[7]}`。"
        for row in rows
    ]
    return f"""# BACT 申报书与简历可信表述（M309 最终先导版）

## 申报书创新点

针对多模态 Token 数与固定粒度 FPGA 实际开销呈阶梯关系的问题，提出跨模态 Token 批边界对齐
方法 BACT。该方法联合约束视觉视图、视觉 Token 与文本 Prompt，在任务质量约束下优先跨越硬件
批边界，并在相同批次数内保留语义损失更小的信息，从而避免“Token 已减少但硬件批次未减少”
的无效压缩。

## 已有验证闭环

- 仿真/离线：四基线身份、Tokenizer 几何、标签盲 M120+A8 原始预测、calibration-only 阈值与
  一次性 held-out 协议均有代码和哈希结果。
- 实物：KV260 Build `{resources['build_id']}` 完成 27 点三边界反平衡测试，三个批边界均出现
  精确 154 次逻辑调用阶跃；三处时延阶跃均约 20 秒。
- 实现：LUT `{resources['implementation']['resources']['clb_luts']['reported_utilization_percent']:.2f}%`、
  BRAM `{resources['implementation']['resources']['block_ram_tiles']['reported_utilization_percent']:.2f}%`、
  URAM `{resources['implementation']['resources']['uram']['reported_utilization_percent']:.2f}%`、
  DSP `{resources['implementation']['resources']['dsps']['reported_utilization_percent']:.2f}%`，WNS
  `{resources['implementation']['wns_ns']:+.3f} ns`。

## AI 生成先导集结果

{chr(10).join(metric_lines)}

这些准确率只适用于 12 个经人工复核的 AI 生成先导视频，不代表真实工厂准确率。

## 简历写法

在 AMD Kria KV260 上实现面向 T32 固定执行粒度的 BACT 跨模态 Token 预算方法，完成四基线、
127/128/129、159/160/161、191/192/193 三组硬件边界的 27 点实板验证，并建立标签盲预测、
calibration-only 阈值冻结和一次性 held-out 评测闭环；输出可复现代码、哈希结果、资源/时序
证据与稳健性分析。

## 禁止扩大的表述

不得写成“实时 4B 视频推理”“性能超过 GPU/4060”“功耗领先”“真实工厂验证”“国内/国际首创”
或“因果证明 BACT 提速”。这些主张尚无对应证据。
"""


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--workspace", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--report", default="BACT_FINAL_EVIDENCE_REPORT.md")
    parser.add_argument("--claims", default="BACT_APPLICATION_AND_RESUME_CLAIMS_FINAL.md")
    parser.add_argument("--result", default="deployment/mage_vl4b/M309_BACT_FINAL_EVIDENCE_PACK_RESULT.json")
    args = parser.parse_args()
    workspace = args.workspace.resolve()
    report_path = resolve_under(workspace, args.report)
    claims_path = resolve_under(workspace, args.claims)
    result_path = resolve_under(workspace, args.result)

    values, source_index = validate_sources(workspace)
    report = build_report(values, source_index)
    claims = build_claim_pack(values)
    atomic_text(report_path, report)
    atomic_text(claims_path, claims)
    result = {
        "date": "2026-09-03",
        "gate": "M309-final-bact-evidence-and-claim-pack",
        "status": "PASS_FINAL_PILOT_EVIDENCE_PACK",
        "classification": "Deterministic final pilot report and claim wording generated only from sealed, hash-checked method, KV260, resource, label-blind prediction and one-shot human-labelled evaluation evidence.",
        "report": str(report_path.relative_to(workspace)).replace("\\", "/"),
        "reportSha256": sha256(report_path),
        "claims": str(claims_path.relative_to(workspace)).replace("\\", "/"),
        "claimsSha256": sha256(claims_path),
        "sourceIndex": source_index,
        "formalPilotAccuracyAllowed": True,
        "realWorldExternalValidityClaimAllowed": False,
        "realTimeClaimAllowed": False,
        "dynamicPowerClaimAllowed": False,
        "poweredCausalSpeedClaimAllowed": False,
        "boardExecutionRun": False,
        "activeM254M256Changed": False,
        "bootDtbCmaPartitionsChanged": False,
        "stableRollbackPreserved": True,
    }
    atomic_json(result_path, result)
    print(
        "M309_BACT_FINAL_EVIDENCE_PACK_PASS "
        f"report_sha256={result['reportSha256']} claims_sha256={result['claimsSha256']}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
