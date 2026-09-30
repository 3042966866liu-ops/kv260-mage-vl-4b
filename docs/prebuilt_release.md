# KV260 预构建发布资产

稳定安装使用 Build `0x4D395832` 对应的哈希锁定 M327 v7 归档，已在所有者 KV260 的独立目录安装并运行。Git 仓库本身不含模型权重或 bitstream。以下八个分片及匹配的八分片 `RELEASE_PARTS.json` 已在 [GitHub Releases](https://github.com/3042966866liu-ops/kv260-mage-vl-4b/releases)公开。不要替换成名称相近的旧 v2–v6 包，也不要混用 2 GB 与 500 MB 分片。

| 资产 | 字节数 | SHA-256 |
| --- | ---: | --- |
| `kv260-mage-vl-4b-prebuilt-install-20260926-v7.tar.part01` | 500,000,000 | `60d7d3c1e7045ee36bb8a452b8c01474cacbdc29199b01ecd1a186efb040be10` |
| `kv260-mage-vl-4b-prebuilt-install-20260926-v7.tar.part02` | 500,000,000 | `b7de4ff4f0a71df41397b5737890072f16966ddab86912113c84a53daf7aa0e0` |
| `kv260-mage-vl-4b-prebuilt-install-20260926-v7.tar.part03` | 500,000,000 | `61e1c948b652ed570d8f58147212515f9ab4bdd6c9d596e81ffab501b8c32dc1` |
| `kv260-mage-vl-4b-prebuilt-install-20260926-v7.tar.part04` | 500,000,000 | `5e5cca1d2edd6af941810aa16ffb97105edc9fc9fe748900414c45aea5bf16ad` |
| `kv260-mage-vl-4b-prebuilt-install-20260926-v7.tar.part05` | 500,000,000 | `d94e19be5142b0e9174b99d5109a430c0020068add7dfee9d41287419aa26547` |
| `kv260-mage-vl-4b-prebuilt-install-20260926-v7.tar.part06` | 500,000,000 | `35cbc6b16a5f3bacdbe4b0c9a7c96abc1c0eb8238fa59851bb36c1aa5195cfc6` |
| `kv260-mage-vl-4b-prebuilt-install-20260926-v7.tar.part07` | 500,000,000 | `fc9b9a1742df21d00a94943406e8f9b346265a67a02b50b53e1bad7cea719651` |
| `kv260-mage-vl-4b-prebuilt-install-20260926-v7.tar.part08` | 409,191,680 | `1ecb792ea63f92fd565111c2e8b3528dcede774ed2c4f78d7c9eb70b7beb6a20` |
| 重组后的 v7 TAR | 3,909,191,680 | `c487e16bcc18698808d7c48822e355c8b6cf291633b00d661f372f7280d41145` |

GitHub Releases 要求单个附件小于 2 GiB。最初的 2 GB 分片虽低于上限，但浏览器上传失败，因此在保持原 TAR 不变的前提下重新拆成较小分片。机器清单见[八分片清单](../manifests/release_parts_v7.json)。上传来源是所有者本地 `release_staging/distribution_v7_500mb/`，不是读者的下载路径。Release 清单已经下载并核对为八分片版本；公开归档分片尚无完整下载和重组校验记录。

将同一 Release 中的全部八个分片与 `RELEASE_PARTS.json` 下载到同一主机目录。清单应列出八个分片，`part_bytes_limit` 为 `500000000`；仓库副本见[八分片清单](../manifests/release_parts_v7.json)。组装前先校验每个分片及合并数据流。验证器拒绝缺失、被修改或重复的分片，不连接开发板，也不运行模型。

```sh
# 在克隆仓库根目录运行；下载的清单与八个分片须放在同一目录。
python3 scripts/release_parts.py verify /path/to/downloads/RELEASE_PARTS.json
python3 scripts/release_parts.py assemble /path/to/downloads/RELEASE_PARTS.json /path/to/kv260-mage-vl-4b-prebuilt-install-20260926-v7.tar
```

仓库保存了同一清单。`assemble` 拒绝覆盖已有输出，并在最终落盘前核对完整 TAR 的 SHA-256。主机还需约 3.9 GB 额外磁盘空间，不要在接近满容量的 KV260 microSD 上重组。

v7 TAR 不包含视频、静态图像样例或监控录像。历史 M328 固定视频入口需要独立的四帧伴随包。所有者确认四帧摩托车画面为 AI 生成并批准公开。伴随包 **`m328_release_video_addon_20260926_v3.tar` 已在 [GitHub Releases](https://github.com/3042966866liu-ops/kv260-mage-vl-4b/releases)公开下载**，大小为 2,437,120 字节，SHA-256 为 `254587ec1f776a01dc12ef98b900a558e4c3087c90a8630a59be51ef12df8b93`，另有[机器清单](../manifests/fixed_video_companion_v3.json)。本分发不包含真实监控视频。仅有 v7 TAR 可执行固定文本与运行时启动检查，**不能**复现已记录的固定视频结果；参见[固定视频复现](fixed_video_reproduction.md)。

解压到独立板端目录后，按[快速开始](quickstart.md)完成包内逐文件校验、隔离 wheel 安装、环境预检和分级 FPGA 检查。**固定视频 v3 伴随包要求基础安装位于 `/home/ubuntu/tellme_release_install_20260926`。** 已验证的首次安装依赖记录中的 PYNQ/XRT/Ubuntu 环境，尚未证明通用干净 KV260 系统镜像与之等价。稳定部署和回滚必须保留。

资产公开并不解决[来源说明](provenance.md)中的逐文件第三方署名与再分发审查。SHA-256 校验成功或所有者允许公开项目文件，不会授予第三方组件的权利。
