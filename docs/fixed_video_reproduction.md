# 使用 KV260 预构建包复现固定视频

稳定发布由 v7 预构建 TAR（`0x4D395832`）和单独哈希锁定的四帧伴随包组成。所有者确认摩托车样例为 AI 生成并同意公开，它不是真实监控录像。伴随包沿用已在该 Build 上执行的原 M277 输入与固定检查，不改变权重、bitstream、图像预处理、帧序、Prompt、量化或输出契约。原 v7 TAR 保持逐字节不变。

两项资产均可从 [GitHub Releases](https://github.com/3042966866liu-ops/kv260-mage-vl-4b/releases)获取。附件 `RELEASE_PARTS.json` 已与仓库八分片清单核对一致。**公开基础归档的完整下载、重组及哈希验证尚无记录。** 伴随包的精确身份见[清单](../manifests/fixed_video_companion_v3.json)。

## 精确输入与预期结果

伴随包按以下顺序包含四个原始 `uint8` RGB448 NumPy 帧：

1. `frame_00_0068_rgb448.npy`
2. `frame_01_0102_rgb448.npy`
3. `frame_02_0137_rgb448.npy`
4. `frame_03_0171_rgb448.npy`

堆叠张量形状为 `(4, 448, 448, 3)`，SHA-256 为 `5911485955780036ac4c8990bcaa248667f2e86bd1fd6f9b0783002553b4adff`。伴随包 `run_fixed_video.py` 调用已发布的 M277 `M276ShortPromptBinaryRuntime.stream`，使用固定 `M276_KNIFE_PROMPT`、`max_new_tokens=1` 提交完整有序张量。历史稳定板端参考要求：159 个输入 Token、视觉选帧索引 `[3]`、受限输出文本 `0`／Token ID `15`、刀具判定 `ABSENT`、稳定 Build-ID、778 次语言逻辑 FPGA 调用，且无语言 CPU Linear fallback。入口会明确发出 preprocess、vision、prefill、token、knife observation 和 complete 事件。

这是**直接 4B 视频推理入口**，不是 M254 快通道报警会话，不能描述为自动报警触发的 Web 语义复核。虽然四帧按顺序提交，历史运行时只取末帧形成全景／细节视图；通过测试不能证明四帧时序理解。旧 M277 结果是固定输入的参考，不代表任意新安装已通过。

## 所有者板端已用的安装流程

**基础 v7 安装必须位于 `/home/ubuntu/tellme_release_install_20260926`。这是 v3 附件 `run_fixed_video.py` 第 22 行 `RELEASE` 的硬编码路径，不是任意示例目录。**

基础安装须具备精确包清单、已安装的隔离 wheel，且没有其他服务占用 FPGA／端口 8001。通过有界、哈希核验的接收流程，将伴随包安装到 `/home/ubuntu/tellme_release_video_addon_20260926_v3`，不要覆盖稳定部署。按[公开伴随包清单](../manifests/fixed_video_companion_v3.json)核对 TAR 与内部 `PACKAGE_MANIFEST.json` 的 SHA-256；原构建记录位于所有者工作区 `deployment/mage_vl4b/M328_VIDEO_ADDON_BUILD_RESULT_V3.json`。在同一 COM3 登录终端完成 `sudo -v`、依赖与环境预检后执行以下命令；**此命令对应上述固定基础目录及伴随包目录**：

```sh
sudo -n /usr/local/share/pynq-venv/bin/python3 /home/ubuntu/tellme_release_video_addon_20260926_v3/run_fixed_video.py
```

入口先检查发布身份、root/XRT/PYNQ、M277 运行时源码哈希与导入、四个样例帧哈希及有序张量哈希，然后才调用未修改的 M277 视频运行时。它在伴随包目录写入 `results/environment.json`、`results/video_forward.log`、`results/m277_fixed_video.json`，并原子写入 `results/result.json`。900 秒超时避免无限等待 FPGA。脚本不会停止或替换稳定服务，端口 8001 被占用时拒绝执行。失败时保留首个异常和完整日志，仅重跑失败级别。

板端验证结论以所有者工作区最新 `deployment/mage_vl4b/BOARD_GATE_RESULT.json` 为准。不能仅依据 v7 无帧 Web 就绪或历史 M277 结果声称视频 E2E 通过。

## 所有者板端首次安装结果（M328，2026-09-26）

单独分发的 v3 伴随 TAR（SHA-256 `254587ec1f776a01dc12ef98b900a558e4c3087c90a8630a59be51ef12df8b93`）安装于独立 v7 安装的伴随目录，五个载荷文件全部通过板端哈希检查。该直接入口按指定顺序接收四帧，完成全部 24 层视觉计算，再在稳定 `0x4D395832` 上执行 159 Token 的 T32 语言路径。预期的 778 次逻辑 FPGA 调用完成，无语言 CPU Linear fallback，输出文本 `0`／Token ID `15`、判定 `ABSENT`。首 Token 为 `230.721 s`（不含启动）；完整检查为 `511.854 s`（含启动与校验）。输出分数未经校准。完整结果保存在所有者工作区 `deployment/mage_vl4b/M328_RELEASE_VIDEO_BOARD_RESULT.json`，原始 COM3 日志为 `tmp/m328_video_gate_uart.log`。

该结果将**直接固定视频 4B 首次安装测试**从未验证变为 PASS，不改变不可变的 v7 基础包，也不证明自动报警 Web 路由、持续 Decode 吞吐、独立任务准确率或实时性能。模型只使用末帧全景／细节视图。Release 已提供 AI 生成的伴随包、八个基础分片和已核对清单；公开分片完整下载与重组尚无记录。基础包第三方署名与再分发审查独立于所有者对这四帧的公开许可。
