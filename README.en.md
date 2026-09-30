# 在 KV260 上部署 Mage-VL 4B

[项目主入口](README.md)。本页保留原文件名以兼容已有链接，说明正文统一为中文。

这是面向 AMD Kria KV260 的多模态推理研究原型，研究如何在有限内存和固定 T32 FPGA 执行粒度下运行 4B 模型，同时让 PS–PL 执行过程及其成本可测量。

项目包含混合精度权重适配、PS 视觉塔与 PL 语言 Linear 运算、独立安装的固定视频样例，以及隔离的 Web 手动复核路径。也保留了未改善完整请求的实验：局部解析器更快、T64 设计未满足时序，以及通用快速检测器对可见菜刀响应较弱。

默认板端路径使用稳定 T32 Build `0x4D395832`。本仓库可审阅源码与实验材料，模型权重和 bitstream 不进入 Git。[GitHub Releases](https://github.com/3042966866liu-ops/kv260-mage-vl-4b/releases)提供八个预构建分片、固定视频伴随包及匹配的八分片 `RELEASE_PARTS.json`，下载后必须按清单校验。

## 硬件开销为何不随 Token 数线性变化

![本项目使用的 AMD Kria KV260 开发板](docs/assets/kv260-board.jpg)

照片由项目所有者提供并授权公开。仓库不包含 UI 截图或原始监控录像。

![固定 T32 批边界下的语言逻辑 FPGA 调用次数](docs/assets/t32_batch_boundary.svg)

图中展示的是**逻辑调用次数**，不是完整请求时延；实现和测量见[架构说明](docs/architecture.md)与[实验索引](experiments/README.md)。

## 主要工作

1. **适配板端资源约束。** 按敏感性选择 W2/W3/W4 及部分高精度组件，并用哈希锁定打包权重和布局。[工程取舍](docs/optimization_journey.md)
2. **建立可核验的 PS–PL 推理。** PS 负责视觉、注意力、归一化和 KV cache；T32 PL 核承担语言 Linear／LM Head。固定输入检查覆盖 Build ID、FPGA 调用、输出和 CPU Linear fallback。[系统架构](docs/architecture.md) · [源码导览](docs/source_map.md)
3. **按完整请求测量决定是否采用优化。** 视觉 W4 向量化解码、权重暂存和输出解析改善了部分组件；T64、Decode-one 与解析器候选在时序或端到端比较后仍保留为实验。[性能分析](docs/performance_attribution_history.md)
4. **让输入预算对应硬件批次。** BACT-V2 围绕 T32 边界研究视图与提示词预算。总输入由 164 降至 159 Token 时跨过 160 Token 边界，语言逻辑调用由 932 降为 778。[BACT 与提示词探索](docs/bact_v2.md)

## 代表性结果

| 实验 | 结果及范围 |
| --- | --- |
| 独立安装固定视频 | 按序提交四帧，但模型仅使用末帧两个视图；159 输入 Token、778 次语言逻辑 FPGA 调用，输出 `0`；首 Token **230.721 s**，不含初始化。[公开结果](experiments/fixed_video/RESULT.json) |
| CPU／PL 单链配对 | 两种固定双 descriptor 形状各 10 对交错测量。A53 CPU／PL 中位：W2 **5.891/2.244 ms**、W4 **5.871/2.525 ms**，约 **2.63×/2.33×**，不是整模型加速比。[实验条件](docs/cpu_pl_benchmark.md) |
| T32 批边界 | 固定 Prefill 契约下，164 Token 为 6 批／932 次调用，159 Token 为 5 批／778 次调用。阶梯现象有 27 条板端记录支持。[方法与证据](docs/bact_v2.md) |
| Web 手动复核 | 隔离版本完成两次真实视频窗口 Web→4B/FPGA→SSE 复核，首 Token **196.286/174.653 s**；不是自动报警触发。[实验记录](experiments/m335_manual_web_review/REPORT.md) |

分钟级 4B 首 Token 时延不等于秒级视频语义更新。受限路径只使用末帧两个视图。快通道可继续接收帧并丢弃过期任务，但尚未建立可靠自动刀具报警。完整条件见[结果](docs/results.md)与[限制](docs/limitations.md)。

## 快速开始

无需开发板时，按[环境说明](docs/environment.md)复算固定 BACT 选择器、成本和质量记录；该命令不下载权重，也不运行新模型推理：

```bash
python3 scripts/m321_reproduce_bact_v2_evidence.py --only all
```

KV260 安装请阅读[安装指南](docs/quickstart.md)、[预构建资产与校验](docs/prebuilt_release.md)、[模型及硬件资产](docs/model_setup.md)和[固定视频复现](docs/fixed_video_reproduction.md)。不访问设备的预检命令为：

```bash
python3 scripts/preflight.py --dry-run --config configs/deployment.example.json
```

本地 v7 预构建包与固定视频伴随包已在所有者 KV260 的独立目录完成安装验证。下载者可从 Release 获取全部八个分片和 `RELEASE_PARTS.json`，按[预构建资产说明](docs/prebuilt_release.md)校验并重组。Release 清单已核对为八分片版本，但公开分片的完整下载、重组和哈希检查尚无记录。**仅克隆仓库不足以复现板端安装。** 源码可重建范围见[构建说明](docs/build.md)。

## 文档导航

| 问题 | 入口 |
| --- | --- |
| PS 和 PL 如何分工？ | [系统架构](docs/architecture.md) · [源码导览](docs/source_map.md) |
| 为什么选择当前实现？ | [工程取舍](docs/optimization_journey.md) · [BACT／提示词](docs/bact_v2.md) |
| 如何核对测量数据？ | [结果总表](docs/results.md) · [实验索引](experiments/README.md) |
| 如何安装或构建？ | [快速开始](docs/quickstart.md) · [资产清单](manifests/external_assets.json) · [构建指南](docs/build.md) |
| 发布与署名条款是什么？ | [原创许可范围](LICENSE_SCOPE.md) · [来源说明](docs/provenance.md) · [第三方声明](THIRD_PARTY_NOTICES.md) · [发布状态](RELEASE_READINESS.md) |

本仓库是研究预览，不是经过认证的安全监控产品。所有者为其有权许可的原创内容选择 Apache-2.0；第三方文件、模型与样例保留各自条款。详见[许可范围](LICENSE_SCOPE.md)与[发布状态](RELEASE_READINESS.md)。
