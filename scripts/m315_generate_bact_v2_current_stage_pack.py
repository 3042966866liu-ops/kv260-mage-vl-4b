#!/usr/bin/env python3
"""Generate the hash-locked BACT-V2 current-stage evidence and claims pack."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def canonical_bytes(value: object) -> bytes:
    return (json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n").encode("utf-8")


def atomic_write(path: Path, data: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    partial = path.with_suffix(path.suffix + ".partial")
    partial.write_bytes(data)
    os.replace(partial, path)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--workspace", type=Path, required=True)
    parser.add_argument("--result", type=Path, required=True)
    args = parser.parse_args()
    workspace = args.workspace.resolve()
    inputs = {
        "scope": workspace / "deployment/mage_vl4b/M312R1_BACT_CURRENT_STAGE_SCOPE_RESULT.json",
        "protocol": workspace / "deployment/mage_vl4b/M312_BACT_EVALUATION_PROTOCOL_V2_RESULT.json",
        "selector": workspace / "deployment/mage_vl4b/M313_BACT_V2_SELECTOR_RESULT.json",
        "board_binding": workspace / "deployment/mage_vl4b/M314_BACT_V2_BOARD_COST_BINDING_RESULT.json",
    }
    documents = {name: json.loads(path.read_text(encoding="utf-8")) for name, path in inputs.items()}
    scope = documents["scope"]
    selector = documents["selector"]
    board = documents["board_binding"]
    assert scope["status"] == "PASS_CURRENT_STAGE_SCOPE_FROZEN_FORMAL_DATA_DEFERRED"
    assert selector["status"] == "PASS_EXECUTABLE_SELECTOR_AND_BOUNDARY_CONTRACT"
    assert board["status"] == "PASS_EXISTING_BOARD_EVIDENCE_BOUND_NO_RERUN_REQUIRED"
    assert selector["selected"]["candidate"]["candidate_id"] == "bact-159"
    assert board["identity"]["build_id"] == "0x4D395832"
    assert board["rerun_decision"]["new_board_run_required"] is False

    evidence_path = workspace / "BACT_V2_CURRENT_STAGE_EVIDENCE_REPORT.md"
    claims_path = workspace / "BACT_V2_CURRENT_STAGE_CLAIMS.md"
    input_lines = "\n".join(
        f"- `{path.relative_to(workspace).as_posix()}` — SHA-256 `{sha256(path)}`"
        for path in inputs.values()
    )
    evidence = f"""# BACT-V2 当前阶段证据报告

冻结日期：2026-09-03

## 结论

当前阶段已经完成“方法可执行 + 固定硬件成本可核查”的闭环。BACT-V2 在不读取人工标签、历史
测试统计或文件名语义提示的条件下，从 9 个跨模态配置中自动选择 `bact-159`。该配置在现有
KV260 T32 语言 Prefill 链上对应 159 Token、5 批和 778 次逻辑 FPGA 调用。

这不是准确率优势、实时性、功耗或 GPU 对比结论。正式质量结论仍需执行已预注册但延期的
100–120 个独立源视频数据闭环。

## 1. 方法与选择规则

BACT-V2 联合调整：

- 视图选择 `view_indices`；
- 每个视图的视觉 Token 预算 `visual_tokens_per_view`；
- Prompt 模板与文本 Token 预算。

候选语义损失代理为：

`D = 0.5 × visual_importance_loss + 0.3 × view_coverage_loss + 0.2 × prompt_deletion_cost`

代理权重与上限只属于冻结的 calibration/inference-time fixture，不是测试集准确率。选择器在
`D <= 0.1` 下按 `(T32 批数, D, -保留 Token 数)` 字典序最小化。B4/B5/B6 每一档均包含
`visual_only`、`visual_plus_prompt`、`view_visual_prompt_joint` 三类候选。

## 2. M313 可执行选择器结果

- 候选数：`{selector['candidate_count']}`；
- 自动选择：`{selector['selected']['candidate']['candidate_id']}`；
- 选择配置：视图 `{selector['selected']['candidate']['view_indices']}`，每视图视觉预算
  `{selector['selected']['candidate']['visual_tokens_per_view']}`，Prompt
  `{selector['selected']['candidate']['prompt_id']}`；
- 总 Token：`{selector['selected']['candidate']['total_tokens']}`；
- T32 批数 / 逻辑调用：`{selector['selected']['batches']} / {selector['selected']['logical_calls']}`；
- 重复运行确定性：`{str(selector['deterministic_rerun']).lower()}`；
- 运行接口拒绝 outcome/held-out/文件名提示字段，历史 M308 test 统计未读取。

合同测试全部通过：`127/128/129`、`159/160/161`、`191/192/193`；`159→130` 虽减少
29 Token 但仍为 5 批/778 calls；`164→159` 只减少 5 Token，却减少 1 个完整批次和 154 calls。

## 3. M314 KV260 成本证据绑定

- 实板身份：AMD Kria KV260，Build `0x4D395832`，Kernel `mage_m120_m89x2_0`；
- 固定公式：`Calls(N)=154×ceil(N/32)+8`；
- 既有实板数据：3 个边界、9 个 Token 点、每点 3 次，共 27 条；
- 27/27 条观测调用数均与公式一致；原运行只加载一次 runtime、执行一次视觉塔；
- `count-144` 与 `bact-159`：均为 5 批/778 calls，后者多保留 15 Token；
- `ratio-164` 到 `bact-159`：6→5 批，932→778 calls；
- 几何、Build、Kernel、T32 粒度和运行链未变，因此没有重复 27 点上板测试。

159 是既有 27 点实板测试的直接测量点；144 和 164 的成本身份来自在 27/27 条实板记录上验证
通过的精确阶梯公式，不把模型拟合值冒充对应配置的直接实测时延。

## 4. 证据边界

当前可以证明：

1. BACT-V2 是可运行、确定性且输入合同无标签泄漏的离散选择器；
2. `bact-159` 能由冻结规则自动产生，不是查看旧测试结果后手工指定；
3. 固定 T32 执行粒度导致 Token 数与硬件调用开销呈阶梯关系；
4. 在相同 5 批/778 calls 身份下，`bact-159` 比 `count-144` 多保留 15 Token；
5. `ratio-164→bact-159` 跨过 160 边界并消除一个完整调用批次。

当前不能证明：BACT 提高准确率或语义质量、实现实时 4B、动态功耗领先、超过 RTX 4060、真实
工厂泛化、统计因果提速或学术首创。

## 5. 延期但已冻结的下一阶段

正式质量闭环继续沿用 M312 预注册协议：100–120 个独立源视频，至少 80 个受控/许可真实样本，
双人复标与 Cohen's κ，新 calibration/held-out split，标签盲四基线预测，一次性 held-out，paired
bootstrap/McNemar 与质量消融。旧 12 个 AI 视频只保留为不可覆盖的工程回归证据。

## 6. 输入证据

{input_lines}

所有本阶段动作均未修改活动 M254/M256、overlay、boot/DTB/CMA、分区或稳定回滚。
"""
    claims = """# BACT-V2 当前阶段可信表述

## 申报书可用

本项目针对固定 T32 执行粒度下“减少 Token 不一定减少实际硬件批次”的问题，设计了跨模态
Token 批边界对齐方法 BACT-V2。该方法联合枚举视图、每视图视觉 Token 与 Prompt 预算，并在
冻结的语义损失代理约束下按硬件批数、代理损失和信息保留量进行字典序选择。可执行选择器在
不读取人工标签或测试统计的条件下自动选出 159-Token 配置。通过绑定 KV260 Build
0x4D395832 的 27 点实板边界数据，验证其 5 批/778 次逻辑调用身份：相较 144-Token 配置在
相同调用成本下多保留 15 Token，相较 164-Token 配置减少 1 个批次和 154 次逻辑调用。

## 答辩一句话

我们的重点不是盲目少删 Token，而是以尽可能小的语义代理损失跨过 FPGA 的真实批边界；现阶段
已经证明选择器可执行和成本身份成立，正式质量优势仍等待更大真实数据集验证。

## 简历可用

- 在 AMD Kria KV260 上实现 BACT-V2 跨模态 Token 批边界选择器，联合优化视图、视觉 Token
  与 Prompt 预算；以 27 点实板测量验证 T32 阶梯调用模型，使 159-Token 配置相较 164-Token
  配置减少 1 批/154 次逻辑 FPGA 调用，并在与 144-Token 配置相同的 5 批成本下多保留 15 Token。

## 禁止扩写

不得改写成“提高了准确率”“实时运行 4B”“功耗领先”“超过 4060”“已在真实工厂验证”或
“国内/国际首创”。旧 12 个 AI 视频不承担新的质量优势或泛化证明。
"""
    atomic_write(evidence_path, evidence.encode("utf-8"))
    atomic_write(claims_path, claims.encode("utf-8"))

    result = {
        "date": "2026-09-03",
        "gate": "M315-BACT-V2-current-stage-evidence-and-claims-pack",
        "status": "PASS_CURRENT_STAGE_METHOD_AND_COST_CLOSED_FORMAL_QUALITY_DEFERRED",
        "classification": (
            "Current-stage method/cost closeout only. Formal accuracy, generalization, real-time, power, "
            "GPU comparison, causal performance and novelty-priority claims remain locked."
        ),
        "selected_candidate": "bact-159",
        "verified_cost_identity": {"tokens": 159, "t32_batches": 5, "logical_calls": 778},
        "same_cost_comparison": {"candidate": "count-144", "extra_tokens_retained_by_bact": 15},
        "cross_boundary_comparison": {"candidate": "ratio-164", "batches_removed": 1, "logical_calls_removed": 154},
        "outputs": {
            "evidence_report": {"path": evidence_path.name, "sha256": sha256(evidence_path)},
            "claims": {"path": claims_path.name, "sha256": sha256(claims_path)},
        },
        "inputs": {
            name: {"path": path.relative_to(workspace).as_posix(), "sha256": sha256(path)}
            for name, path in inputs.items()
        },
        "formal_dataset_tasks_deferred": True,
        "old_12_ai_videos_classification": "immutable engineering regression only",
        "quality_superiority_claim_allowed": False,
        "real_time_claim_allowed": False,
        "gpu_superiority_claim_allowed": False,
        "active_board_service_changed": False,
        "boot_dtb_cma_partitions_changed": False,
        "stable_rollback_preserved": True,
        "next_gate": "When data resources are available, execute the unchanged M312 preregistered 100-120-source formal quality protocol.",
    }
    atomic_write(args.result, canonical_bytes(result))
    print("M315_BACT_V2_CURRENT_STAGE_PACK_PASS selected=bact-159 method=true cost=true formal_quality=deferred")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
