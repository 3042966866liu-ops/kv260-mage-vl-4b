# KV260 上的 Mage-VL 4B（研究预览）

这是 AMD Kria KV260 上 PS–PL 协同 Mage-VL 4B 原型的源码和证据快照。默认路径为历史实板验证的 **M254 / M120 T32** 服务，Build ID `0x4D395832`。它不是秒级 4B 视频系统。BACT-V2 是离线预算/评测路径，不是网页默认路由。Decode-one Build `0x4F503131` 是独立实验，尚未晋级。

| 路径 | 无板可审阅或复现 | 实板状态 |
| --- | --- | --- |
| 稳定 M254 | 原始 Python/网页源码、T32 HLS、历史清单与门禁 | 独立 v7 首装已通过固定文本 FPGA E2E 和无帧网页运行时；M328 伴随包的直接固定视频 4B E2E PASS。报警触发的网页视频链尚未验证。 |
| BACT-V2 | 九个冻结候选、27 条实板成本记录、12 段历史预测重算 | 成本来自已有 KV260 测量；不是新模型运行或独立精度优势 |
| Decode-one | OP01 源码和同会话 M325 结果 | 仅实验；FIFO 容量长测中止，未正式晋级 |

快通道在不等待 4B 复核时处理人物、动作和刀具相关事件；慢通道仅在报警后触发 4B 语义复核。视觉塔在 PS，语言 Linear 使用 T32 PL。它不是经过认证的安全检测系统，不能用于无人值守的安全决策。

先看[快速开始](docs/quickstart.md)与[架构](docs/architecture.md)。`scripts/preflight.py --dry-run` 是不访问设备的发布入口；`scripts/run_demo.sh` 是带门禁的板端入口，不是旧版升级门禁。BACT 证据可用 `python3 scripts/m321_reproduce_bact_v2_evidence.py --only all` 重算，无需下载权重。还请阅读[模型资产](docs/model_setup.md)、[环境](docs/environment.md)、[构建范围](docs/build.md)、[结果](docs/results.md)、[限制](docs/limitations.md)、[来源](docs/provenance.md)及[发布就绪状态](RELEASE_READINESS.md)。

历史固定视频同会话 M325 对照：稳定 T32 首 Token **228.531 秒**、三步增量 **36.584 / 36.169 / 36.183 秒**；实验 OP01 为 **241.072 秒**、**40.777 / 34.763 / 34.666 秒**。第二个输出 Token 已是 EOS，后两步是强制续跑诊断，不是用户可见的持续吞吐。两者都未达到 4B 实时视频分析。见[原始证据](deployment/mage_vl4b/M325_FULL_SESSION_BOARD_RESULT.json)。

在独立 v7 首装上，另以哈希锁定的伴随包提交原 M277 四帧样例，**直接** 4B 路径完成：Build `0x4D395832`、778 次逻辑 FPGA 调用、输出 `0`、不含初始化的首 Token **230.721 秒**。冻结运行时实际只从末帧形成两个视觉视图；这不证明网页报警复核或四帧时序理解。见[固定视频复现](docs/fixed_video_reproduction.md)及所有者工作区的 `deployment/mage_vl4b/M328_RELEASE_VIDEO_BOARD_RESULT.json`。

Git 中不包含模型权重或 bitstream；身份与可获得性见[外部资产清单](manifests/external_assets.json)。稳定版 M125 的语言与 LM Head 清单及八个分片已在本机 WSL 找到并重哈希确认，见[资产溯源](docs/stable_asset_provenance.md)。本地 v7 预构建 TAR 与 M328 视频伴随包已完成上述所有者板端门禁，但都没有公开下载地址，也未打进 Git。当前还不是可无限制公开发布的版本：项目源码、上游衍生代码和样例视频的再分发授权需所有者核准。见[第三方说明](THIRD_PARTY_NOTICES.md)和[版本说明](docs/releases/v0.1.0.md)。不虚构远程仓库、DOI、论文或作者。

English: [README.md](README.md).
