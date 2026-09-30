# GitHub 源码发布与后续更新

建议仓库名：`kv260-mage-vl-4b`。建议简介：“在 AMD Kria KV260 上部署 Mage-VL 4B，包含 PS–PL 推理、BACT-V2 Token 预算选择与可复算的评测材料。”建议主题标签：`fpga`、`kv260`、`multimodal`、`edge-ai`、`hls`、`research-prototype`。

源码和文档快照已推送到 [GitHub 仓库](https://github.com/3042966866liu-ops/kv260-mage-vl-4b) 的 `main`，首次发布提交为 `69b14e8ac616b1c5c50f67d73c52190e961c9ea7`。GitHub Releases 已提供 v7 归档的八个分片、M328 伴随包和八分片 `RELEASE_PARTS.json`；公开清单已与[仓库清单](../manifests/release_parts_v7.json)核对。完整下载公开分片并重组校验的记录尚未提供。剩余事项见[发布状态](../RELEASE_READINESS.md)，尤其是第三方许可审查。

后续更新前，检查本地 `git status`、[文件清单](../manifests/release_files.json)和暂存差异，仅加入本发布目录中预期修改的文件。保留远端历史，使用普通非强制 push，并在推送后核对远端提交 SHA。不要暂存意外嵌套的仓库、`external_assets/`、权重、wheel 或 bitstream。[发布说明](releases/v0.1.0.md)区分了清单已核对与公开归档完整校验。硬件二进制和模型权重仍需逐文件再分发审查；哈希一致或已上传不等于取得许可。
