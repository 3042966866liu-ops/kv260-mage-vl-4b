# 本地发布状态——2026-09-26

这是当时的**本地研究预览暂存目录**，尚不是公开的 GitHub 仓库。默认使用用户的稳定板端路径：M254/M120/T32 Build `0x4D395832`。OP01 Decode-one 明确保留为实验，不由 `scripts/run_demo.sh` 选用。

## M0–M4 状态

| 阶段 | 本次暂存完成的工作 | 剩余范围 |
| --- | --- | --- |
| M0 盘点 | 追溯 M254→M243/M223 与 M181/M175/M249、BACT M321 JSON 引用、OP01/M325；确认大型二进制和模块优先级 | 板端动态导入、精确上游版本／许可及完整 Vivado 系统构建尚未解决 |
| M1 独立快照 | 复制原 `.py/.sh/.cpp/.hpp/.tcl/.js/.html/.css` 与小型 JSON／契约，不含权重或 bitstream；Git 保留仍在使用的历史 `tmp/` 依赖路径；相对 HLS include 依赖 `missing=0` | 模型／硬件资产另行提供，尚无验证过的公开获取流程 |
| M2 首次安装适配／文档 | 增加相对根目录的启动器／配置、无设备预演、哈希身份检查、文档及来源／资产清单 | 新启动器尚未在 KV260 测试，有意要求操作者明确确认 |
| M3 轻量检查 | Python 语法、JSON、链接及逐文件哈希扫描通过（本次审查后清单含 419 文件）；HLS 双引号 include `missing=0`；M254 静态 Python 导入解析 31 本地模块，无未解析名称；在发布根目录、空 `PYTHONPATH` 下 M321 历史选择器／成本／质量复算通过；预检帮助／预演、预期缺资产失败和 Git 忽略行为已检查；WSL 中 `bash -n scripts/run_demo.sh` 通过 | 实际板端模块导入、完整软件参考和硬件检查为 NOT_RUN |
| M4 本地交付 | 准备发布说明、GitHub 指引、无板 CI 定义与本状态核验 | 未创建远端、未 push、未发布 Release、未执行板端命令 |

## 能力等级

- `SOURCE_REVIEWABLE`：**YES，但署名仍有待核事项**。可审阅原源码和证据，不证明再分发权或首次安装依赖完整。
- `OFFLINE_REPRODUCED`：**YES，范围有限**，仅 M321 固定 BACT 选择器、27 条既有板端成本记录和 12 段历史已见预测。无新模型前向或独立质量测试。
- `PREBUILT_READY`：对干净用户安装为 **NO**。精确 M125 语言／LM Head 布局及八个分片已在所有者 WSL 主机找到并重算哈希，与稳定运行时 M120 身份一致。它们仍在 Git 外；其他权重／tokenizer／检测器／bit/hwh 尚未组成权利核清的首次安装包。发布启动器仍未在干净 KV260 测试。见[稳定资产来源](../../docs/stable_asset_provenance.md)。
- `SOURCE_BUILD_VERIFIED`：**NOT_RUN**。已有 HLS 源码／IP 导出脚本，但尚未验证干净完整 Vivado BD/IP/DMA/时钟/地址/约束/打包流程。

## 当时公开 GitHub 前必须解决的事项

1. 所有者须决定并记录项目源码许可证，并确认衍生 Mage-VL 模型代码、项目代码及复制的小型证据／数据集元数据的权利与署名。当时未擅自添加 `LICENSE`。
2. 若要声称预构建可复现，所有者须提供或说明**全部**精确哈希锁定模型／硬件资产的合法获取方式，包括已找到的 M125 布局，并允许新板首次安装验证。源码研究预览可在权利核清后发布，**不声称预构建已就绪**。

明确标注的源码预览不以新板重测、完整 Vivado 重建、独立质量收益、视频二进制或性能优势结论为发布前提；这些缺口保持公开说明。

## 保留的拒绝或未完成路径

- Decode-one FIFO 容量长测：`STOPPED_BY_USER_NOT_PASS`；OP01 在 M325 同会话比较中未优于稳定 M254，未进入稳定版。
- M321 历史质量：BACT-159 与 count-144 尚未建立独立质量优势，旧 12 段不作为新测试集。
- 提示词改写和前后时刻视图：无净收益被采用，保留 P0/V0。
- 本次发布暂存未改变板端 root、overlay、boot、DTB、CMA、分区、稳定回滚或运行服务。

## 当时计划的后续检查

在发布目录执行 `python3 scripts/check_release.py`、`python3 scripts/m321_reproduce_bact_v2_evidence.py --only all` 和 `python3 scripts/preflight.py --dry-run`。权利与资产问题解决后，按同终端固定 root/XRT/PYNQ 预检及项目历史检查顺序，在**独立**干净 KV260 安装中验证，并保留稳定回滚。有 Bash 的环境运行 `bash -n scripts/run_demo.sh`。不能将 M321 或语法检查描述为板端部署 PASS。
