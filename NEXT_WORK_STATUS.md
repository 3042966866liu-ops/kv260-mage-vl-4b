# 历史阶段计划（归档）

本文件保存 2026-09-26 提出的 A–H 阶段范围，**不再作为当前进度或下一步指令**。原计划之后完成了 M332 端到端候选对照、M333 调度、M335 手动 Web 复核及 M336–M337 输入诊断。请从[项目首页](README.md)、[结果总表](docs/results.md)和[实验索引](experiments/README.md)读取当前公开结论；机器结果仍保留原编号与状态。

| 原阶段 | 归档后的事实 |
| --- | --- |
| A 基线与证据 | 固定模型、权重布局、Build ID、输入和输出身份已有机器记录。稳定推理 Build 为 `0x4D395832`。 |
| B 固定视频耗时 | 已复用 M328 实测，得到互斥顶层分解：首 Token `230.721 s`（加载外），视觉 `43.638 s`、语言至首 Token `187.011 s`。同请求的更细分阶段与多次请求分布没有补测。[性能分析](docs/performance_attribution_history.md) |
| C A53/PL 对照 | M331 的 W2/W4 两种双 descriptor 链各 10 对交错通过；局部比值约 `2.63×/2.33×`，不是整模型加速。[条件](docs/cpu_pl_benchmark.md) |
| D 端到端候选 | M332 已完成两组相反顺序的固定视频 A/B。解析器候选虽有局部短测收益，整视频首 Token 分别多用 `20.224 s`、`7.023 s`，没有采用。[负结果](experiments/m332_parser_scale/REPORT.md) |
| E 整模型 CPU-only | 可行性审计已完成，但没有 36 层及 LM Head 的同量化完整 CPU 后端；公平整模型 CPU/PL 性能对照未运行。[审计](docs/whole_model_cpu_feasibility.md) |
| F BACT 质量—成本 | 27 条板端成本记录和旧 12 段合成视频配对可复算。跨 T32 边界的调用收益成立；同为五批的 BACT-159 与 count-144 尚无独立质量优势。[方法](docs/bact_v2.md) |
| G Web 复核 | M333 调度与 HTTP/SSE 子测试后，M335 隔离手动入口完成两次真实 4B/FPGA/SSE 复核；自然报警→4B 链路没有通过。[手动实验](experiments/m335_manual_web_review/REPORT.md) |
| H 外部复现 | 维护者的 KV260 在独立目录完成预构建固定文本和固定视频测试；预构建资产现已通过 Release 公开，自有原创代码许可已选定；第三方再分发审查、公开分片完整下载重组及新板干净系统复现仍待验证。[发布状态](RELEASE_READINESS.md) |

这份归档不修改稳定部署或回滚。历史 `PASS`/`FAIL`/`BLOCKED` 状态以各自机器结果为准；上表只是方便阅读的工作轨迹。
