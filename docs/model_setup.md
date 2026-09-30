# 模型与外部资产配置

板端结果记录的模型为 `microsoft/Mage-VL`（4B 部署路径）。复制的包清单**不能证明**精确上游版本、下载资格或模型再分发条款。不能用上游当前最新版替代并假定逐位兼容。

稳定语言运行时需要 W2/W4 四端口打包权重、FP16 缩放系数、T32 descriptor、FP16 行优先 embedding、tokenizer JSON、文本归一化参数和 PS 使用的 W4 视觉载荷。`m181_m120_video_board_candidate` 仅包含小型清单、配置与源码，不含数百 MB 的二进制。`weights_root` 必须包含 `language_fourport/` 和 `lmhead_fourport/`，各自带有 `SIXPORT_LAYOUT_MANIFEST.json` 及其引用的二进制分片。还需 `m181.../vision_layout/weights*.bin`、`ps_vision_payload/vision_bf16.safetensors`、`text_auxiliary/embedding.fp16.rowmajor.bin`、tokenizer 文件、`text_norms.fp16.npz` 和原始视觉辅助数据。快通道另需 SSDLite checkpoint。

[外部资产清单](../manifests/external_assets.json)记录已知大小、哈希和精确目标路径。[稳定资产来源核验](stable_asset_provenance.md)在所有者 WSL 产物目录中找到了精确的 M125 语言及 LM Head 布局，并重新核对清单、八个分片和固定 M120 源 checkpoint 的哈希。相邻 M89Y/M89Z 文件的布局或载荷确实不同，没有拿来替换。匹配资产**不包含在 Git 源码目录中**。[GitHub Releases](https://github.com/3042966866liu-ops/kv260-mage-vl-4b/releases)提供八分片预构建归档和对应清单；安装前须校验全部公开分片及重组后的 TAR。公开可下载不等于再分发权已核清。

`scripts/verify_prebuilt_package.py` 按包清单检查全部解压文件；`scripts/preflight.py --check` 检查运行关键资产和前置结果的身份，历史运行时还会进一步核对契约。本源码快照没有重建从上游原始模型到打包权重的完整转换流程。首次安装需要精确的已验证预构建 TAR，或合法取得的等价资产。

不得修改历史 `PACKAGE_MANIFEST.json` 来制造新包哈希兼容的假象。合法准备好精确资产后，应另行保存带版本的安装记录。
