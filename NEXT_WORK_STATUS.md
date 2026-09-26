# KV260 Mage-VL 4B：本轮工作状态

日期：2026-09-26。本文件是阶段 A–H 的工作索引，不覆盖历史原始证据；状态仅用 `PASS / FAIL / BLOCKED / NOT_RUN`。唯一稳定推理基线是 M254/M120/T32 Build `0x4D395832`。Decode-one `0x4F503131` 为未晋级实验核，容量专项仍未通过。相对证据路径均从主工作区根目录解析，非 Git 发布仓库内文件。

| 阶段 | 状态 | 当前可证明的范围、缺口与下一步 |
|---|---|---|
| A 基线与证据 | PASS | `BASELINE_IDENTITY.json` 锁定模型/权重布局/bitstream/样例。M329 机器结果与原始 COM3 日志在本地；M328 是独立安装的直接视频入口。启动 Web 不等于报警后 4B 复核。 |
| B 固定视频耗时分解 | PASS | 按所有者最新要求复用历史实板数据，不新跑视频。`docs/performance_attribution_history.md` 完成互斥顶层重算；细分读盘/PS/PL 仅有不同 849-token 输入的旁证，不冒充 159-token 明细。原方案中的 5 次同条件完整采样与计时开关开销仍 `NOT_RUN`。 |
| C 优化 A53 CPU/PL 公平对照 | PASS | M329 数值与 M330 新原生 CPU 子门禁复用；M331 在稳定 Build 上 W2/W4 各 10 对交错，同量化完整输出、Build-ID/DMA 全通过。单链配对 CPU/PL 中位数为 W2 `5.891/2.244 ms`、W4 `5.871/2.525 ms`；仅为代表形状，不外推整模型或视频。逐对机器证据已随仓库置于 `experiments/m331_paired/`。 |
| D 端到端优化 | NOT_RUN | 必须依据 B 的前两大瓶颈选择一个候选，预登记 ≥5% 固定视频改善门槛；失败保留负结果。 |
| E 整模型 CPU-only 可行性 | NOT_RUN | 需先审计全算子、内存、时间及同量化输入；算子级速度不冒充整模型速度。 |
| F BACT 质量—成本 | BLOCKED | 旧 12 段 AI 视频只能作开发回归；`bact-159` 与 `count-144` 同为 5 批/778 逻辑调用，历史质量未证明 BACT 胜出。独立人工确认新样本缺失时先完成可复现工具，不伪造独立准确率。 |
| G Web 报警复核闭环 | NOT_RUN | M327 v7 证明 Web runtime-ready，M328 证明直接 4B 视频；尚无同一会话“自然报警→排队→4B→SSE”的实板 PASS。 |
| H 外部复现交付 | BLOCKED | 本地 v7 预构建独立安装固定文本及 M328 伴随包直接视频 PASS；公开资产 URL、文件级再分发权、自有代码许可、干净 OS/整壳重建未闭合。按用户后续明确要求，完成阶段后同步 GitHub；外部资产仍不得擅自公开上传。 |

## 阶段 A 证据分类

- **已完成且本地证据齐全：** M329 冻结 M128 W2/W4 单链 CPU/PL 数值和计时；M328 独立安装直接固定视频；M327 v7 固定文本及 Web runtime-ready；M325 同会话 Decode-one 对照负结果。权威结果见 `deployment/mage_vl4b/BOARD_GATE_RESULT.json` 的相应最新字段；原始日志见 `tmp/m329/`、`tmp/m328_video_gate_uart.log`、`tmp/m325_full_session_02_uart.log`。
- **已完成但尚未随 Git 仓库交付：** v7 预构建 TAR、M328 视频伴随 TAR、语言/LM Head/视觉权重、轮文件、bitstream；本地身份见 `release_staging/kv260-mage-vl-4b/manifests/external_assets.json`。本地存在不等于读者可合法获取。
- **尚未完成：** 首 Token 细分归因、优化 A53 公平基线、由瓶颈驱动的整视频优化、完整 CPU-only 可行性、自然报警触发 Web 复核、正式独立质量结论。
- **被外部输入阻塞：** 新的来源独立且人工复核样本、资产再分发权/自有许可决定、公开合法获取地址。阻塞 F/H 不妨碍 B/C/G 的本地工作。

## 严格测量边界

M328 四帧 RGB448 按顺序提交，但 M276 只取索引 `[3]`，再作两个视图；98 视觉 Token、159 总 Token、5 个 T32 批、778 次语言逻辑 FPGA 调用。首 Token `230.721 s` 不含初始化，视觉 `43.638 s`、语言 Prefill 至首 Token `187.011 s`。这不证明四帧时序理解、持续生成、秒级实时性或 Web 报警复核。M329 W2/W4 CPU Python/NumPy 与 PL 事务时间分别 `449.348/2.074 ms`、`497.539/2.420 ms`，不能据此写优化 CPU 或整模型加速比。

下一步：依据 B 的历史宏观瓶颈进入 D，先选一个不改模型/量化/输入的优化候选，估算收益上限并预登记 ≥5% 固定视频改善门槛。稳定回滚、boot、DTB、CMA 和分区不改。
