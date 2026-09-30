# 发布状态——2026-09-27（八分片上传记录）

源码和文档快照已推送到 [GitHub 仓库](https://github.com/3042966866liu-ops/kv260-mage-vl-4b) 的 `main`，首次发布提交为 `69b14e8ac616b1c5c50f67d73c52190e961c9ea7`。GitHub Releases 现已提供八个预构建分片（前七个各 500 MB）、M328 伴随包和八分片 `RELEASE_PARTS.json`；公开清单已下载并核对为八分片版本。公开归档分片的完整下载、重组和哈希检查尚无记录。默认仍为 M254/M120/T32 Build `0x4D395832`，OP01 Decode-one 保持实验状态。

## 已有验证记录

- M0–M4 的源码暂存、路径允许列表、递归依赖检查、JSON/Python/Bash 语法、固定 BACT 选择器／成本／质量复算及本地逐文件哈希均通过。见 `manifests/release_files.json` 和生成安装目录中的 `INSTALL_PACKAGE_MANIFEST.json`。
- 所有者本地预构建归档包含精确 M125 语言／LM Head 分片、稳定 bit/hwh、视觉、tokenizer、检测器与辅助资产。大型文件不进入 Git 源码目录。Release 已提供八分片与匹配清单，但公开八分片归档仍无完整下载、重组校验记录。
- 所有者 KV260 上的独立 v4 安装核对了 450 个文件，随后通过环境、Build-ID-only 和固定文本 FPGA E2E。Build-ID 为 `0x4D395832`，生成 Token `17` 与固定参考一致，逻辑／物理 FPGA 调用为 `162/165`，CPU Linear fallback 为 false。固定文本总耗时 `62.468 s`，不是视频 TTFT 或持续吞吐。descriptor／chain／layer 的历史检查仅在稳定 bit/hwh 身份完全相同时复用，没有在新目录重跑。
- v4 首次 Web 启动因遗漏 M175 `runtime` 搜索路径（`board_runtime` 导入）在 **overlay／模型加载前**失败。v5 修正后通过发布根目录模块路径检查；独立安装通过 450 文件哈希、Build-ID-only 和固定文本 E2E（Token `17`、162 次逻辑／165 次物理调用、`61.901 s`）。空闲 HTTP／Build-ID 检查通过，但 `live/start` 因隔离运行时缺少 `torch` 失败，没有视频推理。v5 服务自行停止，稳定安装未受影响。
- v6 增加了哈希锁定的 36-wheel ARM64 包和带原生 Torch/torchvision 测试的隔离安装器。**在 v6 当时，这个 wheel 归档仍是本地资产，尚未公开下载。**
- 后续 v6 检查通过 452 个安装文件哈希、隔离 Torch/torchvision 原生算子测试、Build-ID-only 和同一固定文本 E2E（Token `17`、162 次逻辑／165 次物理调用、`62.802 s`）。Web worker 随后因 PYNQ 系统 Pillow 9.0.1 缺少包内 Transformers 5.7.0 所需的 `Image.Resampling` 失败，因此 v7 加入哈希锁定的历史 M193 Pillow 12.1.0 wheel，不再复用系统版本。
- 不可变的 **v7** TAR `kv260-mage-vl-4b-prebuilt-install-20260926-v7.tar`（SHA-256 `c487e16bcc18698808d7c48822e355c8b6cf291633b00d661f372f7280d41145`）通过独立 KV260 首次安装：453 个文件哈希、37 个隔离 wheel（含 Pillow 12.1.0 和原生 NMS）、稳定 Build-ID `0x4D395832`、固定文本 Token `17`、162 次逻辑／165 次物理调用、无 CPU Linear fallback，耗时 `62.083 s`。仅 localhost 的 Web 测试返回 HTTP 202，使用预期 M238/M241 类及发布根目录模块达到运行时就绪。**没有提交视频帧。** 结果见上级工作区 `deployment/mage_vl4b/M327_RELEASE_FIRST_INSTALL_V7_RESULT.json`。本文是安装后更新的源码目录说明，不可变 v7 TAR 仍含更早的验证前版本。
- 随后的独立 M328 v3 伴随包在该 v7 安装中，通过固定 M277 直接 4B 入口提交原四个 RGB448 帧。板端核对五个伴随文件、有序张量及 M277 运行时源码子集；在 Build `0x4D395832` 上完成 24 层视觉、159 Token T32 语言 Prefill 和 778 次逻辑 FPGA 调用，无语言 CPU Linear fallback。输出 `0`／Token `15`／`ABSENT` 匹配参考。首 Token `230.721 s` 不含模型／运行时加载，完整检查 `511.854 s`。这是**直接**固定视频 E2E PASS，不是自动报警 Web 复核。见上级 `deployment/mage_vl4b/M328_RELEASE_VIDEO_BOARD_RESULT.json` 与[固定视频复现](docs/fixed_video_reproduction.md)。v7 基础 TAR 保持不变，不含伴随包。

## 当前范围与未完成事项

| 能力 | 当前结论 |
| --- | --- |
| `SOURCE_REVIEWABLE` | 源码可审阅；原创许可已选定，第三方逐文件署名与权利审查仍未完成。 |
| `OFFLINE_REPRODUCED` | 仅固定 M321 BACT 证据已复算，不是新的模型质量结果。 |
| `PREBUILT_READY` | **所有者 KV260 的精确固定文本 E2E、Web 运行时启动及独立伴随包直接固定视频 E2E 已通过。** Release 资产已公开，完整下载／重组未验证；自动报警 Web 4B 视频、持续吞吐和通用干净系统配置仍未验证。 |
| `SOURCE_BUILD_VERIFIED` | NOT_RUN；未声称从干净目录完成 Vivado 全系统重建。 |

源码快照已公开。所有者为其有权许可的原创代码选择 Apache-2.0，[许可范围](LICENSE_SCOPE.md)单独界定第三方内容。不可变 v7 TAR 拆为八个本地哈希校验分片，前七个各 500,000,000 字节，末片 409,191,680 字节；精确哈希见[资产说明](docs/prebuilt_release.md)。Release 已附八分片清单，公开分片的完整下载／重组检查仍无记录。逐文件第三方署名和再分发审查也未完成，公开不代表这些权利已核清。

本地独立目录首次安装不能证明通用干净系统无需额外配置即可满足 PYNQ/XRT/Torch 环境。M328 补齐直接固定视频验证；固定文本和无帧 Web 检查仍须分开，不得描述成自动报警视频 Web 测试。M328 只取末帧两个视图，不证明四帧时序推理或实时运行。剩余实验及判定范围见[后续验证说明](docs/next_validation.md)。

## 保留的失败与恢复范围

- v2 漏掉 M77 固定文本辅助文件；v3 漏掉 M143 参考及 M181 bit/hwh 副本，均在隔离候选加载 overlay 前被拒绝。v4 补齐包路径后暴露启动器搜索路径错误；v5 修正路径后暴露隔离 Torch 缺失。这些记录均不改写为 Web／视频 PASS。
- 无关的旧 7B 板端目录仅在用户授权且已在电脑保留完整核验备份后删除。本次打包未修改稳定 Mage-VL 安装、boot、DTB、CMA、分区或回滚。
- Decode-one 容量测试仍为 `STOPPED_BY_USER_NOT_PASS`；M325 同会话对照未证明优于稳定核，未进入稳定版。

精确 v4–v7 与 M328 板端／UART 证据保存在上级工作区的 `deployment/mage_vl4b/M327_RELEASE_FIRST_INSTALL*_RESULT.json`、`deployment/mage_vl4b/M328_RELEASE_VIDEO_BOARD_RESULT.json`、`tmp/m327_v7_*_uart.log` 和 `tmp/m328_video_gate_uart.log`。安装失败即停止的流程见[快速开始](docs/quickstart.md)，许可范围见[来源说明](docs/provenance.md)。
