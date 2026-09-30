# 稳定 M120/T32 布局资产来源核验（2026-09-26）

范围：对稳定 M254/M120/T32 Build ID `0x4D395832` 的只读身份核验。未连接开发板、停止服务、加载 overlay、执行模型推理、重写权重或构建 bitstream。这**不是**新板首次安装测试。

## 所需身份及来源

稳定视频运行时（`deployment/mage_vl4b/m181_m120_video_board_candidate/video_server.py`）和 M126 运行时契约锁定了以下 `SIXPORT_LAYOUT_MANIFEST.json` 哈希。M125 精确布局构建结果（`deployment/mage_vl4b/M125_EXACT_FOURPORT_LAYOUT_RESULT.json`）记录原 WSL 来源目录及八个分片哈希。历史 KV260 G00 盘点（`deployment/mage_vl4b/optimization_v1/gates/G00-model-inventory/attempt_01/board_raw.json`）也独立记录了板端布局哈希与分片字节数。G00 因随后缺少 Python 依赖而总体 FAIL；其布局身份检查成功不能改写为整体 PASS。

| 资产 | 预期与实测清单 SHA-256 | 原本地来源 | 载荷 |
| --- | --- | --- | ---: |
| 语言 | `12ea4b8cc58639d0aab6da4ef3a3f12bbbb1254f88865f76512a5f0d00d4ae5d` | `/home/lyy/artifacts/tellme-mage-vl/m125-m120-fourport-layouts-v1/language_fourport/` | 4 × 457,209,856 字节 |
| LM Head | `a1a555700e3daec8049627564c73e5783affe3827ab5437665249786d5c079ef` | `/home/lyy/artifacts/tellme-mage-vl/m125-m120-fourport-layouts-v1/lmhead_fourport/` | 4 × 51,658,240 字节 |

2026-09-26 对两个 WSL 清单及全部八个 WSL 分片执行 `sha256sum`，均与 M125 记录一致；逐文件哈希及独立安装目标见[外部资产清单](../manifests/external_assets.json)。固定源 checkpoint 为 `/home/lyy/artifacts/tellme-mage-vl/m120-text4b-mixed-w3e-w4h-w4mlpkv-v2/`，其 `CHECKPOINT_MANIFEST.json` SHA-256 为 `5ff33d1922376e18277902a8b051d069315f79c11b4f63e8d72517acd1dcd5d0`，`weights.bin` SHA-256 为 `9c7de8995a08602186c7090081bbfc10b7c51170ad7e544f2f2dc71333b4f21d`。两个源文件也在当日重新计算哈希，与 M125 来源记录吻合。以上绝对路径是历史来源记录，不是读者应使用的下载或安装路径。

## 为什么拒绝相邻旧文件

只读[布局清单比较脚本](../scripts/compare_layout_manifests.py)发现：

| 与 M125 对比 | 清单 SHA-256 | 结构观察 | 结论 |
| --- | --- | --- | --- |
| M89Y 语言 | `b7cafc930326179091aa32d666395331f27d5518d01758ef01e71b31ed70ac26` | 252 个模块名与 648 个 tile 相同，但 42 个模块位宽、251 个 tile／偏移记录不同，每个分片的大小和哈希都不同；M89Y 来源为 M56，而非固定 M120 checkpoint。 | 实际布局与载荷不同，不能替代。 |
| M89Z LM Head | `0fbaaebc102c4deece9945c98d1dc719a4102929ca4db79077175af32a571b28` | LM Head 位宽、tile 数据、分片大小及哈希不同。 | 布局与载荷不同，不能替代。 |
| M89Z2 W4 LM Head | `3a028f5d5f579142e5003243d6200de2e447a8acb2ef97f30ab7809d2f29e253` | 模块形状、位宽和 tile 字段与 M125 相同，但四个等大小分片的哈希全部不同；来源为较早 M89Z/M56 分支。 | 不只是 JSON 格式差异，载荷身份不同，不能替代。 |

共享布局参数（`shard_count=4`、`group_size=64`、行块及对齐方式）不能证明权重等价。仅凭 SHA-256 不同无法说明差异原因，上述结构和分片比较才给出了具体依据。

## 当次核验的发布范围

精确 M125 资产已在所有者 WSL 主机找到，因此“本地未找到”的旧缺口已解决。资产仍位于 Git／源码快照**之外**。此次核验没有向 Git 复制大型权重或 bitstream，没有据此推断公开下载地址或再分发权，也没有在干净 KV260 上试运行新的首次安装启动器。独立安装时，需将精确两套目录放到 `external_assets/weights/{language_fourport,lmhead_fourport}/`，按 `external_assets.json` 核对清单及每个分片，再准备其余资产并执行规定的检查失败即停止的预检。不得重命名 M89Y/M89Z 或放宽预期哈希以取得 PASS。

当时源码预览可在许可／署名审查后完成，但不能声称 `PREBUILT_READY` 或干净全系统源码重建。此次核验没有修改任何历史板端 PASS/FAIL。

本文保存 2026-09-26 的核验范围；后续安装及资产公开状态见[发布状态](../RELEASE_READINESS.md)和[预构建资产](prebuilt_release.md)。
