# M325：BACT 159 视频＋连续 Decode 同会话实板性能

日期：2026-09-26。设备：AMD Kria KV260。结论：**完整同会话测量完成，数值完全一致；Decode-one 实验核本轮未取得性能优势，不晋级稳定部署。**

## 实验边界

- 稳定 Build `0x4D395832`；Decode-one 实验 Build `0x4F503131`。两个运行各自从相同固定视频输入开始，在同一会话中完成视觉、159-token Prefill、首 token 和 3 次增量 Decode；不是把独立 KV852 测试与视频首 token 拼接。
- 使用 M277/M276 冻结的二元刀具问答输入：固定四帧夹具，但实际视觉塔只接收**最后一帧的两个 224×224 视图**、98 视觉 token；不能表述为四帧时序理解。完整输入为 159 token、5 个 T32 批次。
- 计时从模型和 FPGA 运行时加载完成后开始，包含预处理、视觉、Prefill 与 Decode；**不包含冷启动/overlay 和模型加载**。每个完整会话执行 1264 次逻辑 FPGA 调用。
- 固定文本门禁曾在 attempt01 以两个 Build 精确通过；attempt02 校验其原始结果哈希后复用。attempt01 视频因进度回调参数错误在视觉第 0 层、FPGA 视频推理前停止，原失败证据保留；仅修正回调接口后重新上板。

## 本轮实测

| 指标 | 稳定 T32 | Decode-one 实验核 |
|---|---:|---:|
| 首 token 延迟 | 228.531 s | 241.072 s |
| 视觉塔 | 41.487 s | 41.875 s |
| 视觉完成至首 token | 186.791 s | 198.948 s |
| 后续 Decode 第 1/2/3 步 | 36.584 / 36.169 / 36.183 s | 40.777 / 34.763 / 34.666 s |
| 3 步 Decode 合计 | 108.936 s | 110.206 s |
| 3 步平均速率 | 0.027539 token/s | 0.027222 token/s |
| 首 token 至第 4 token 完成 | 108.936 s | 110.206 s |
| 计时起点至第 4 token 完成 | 337.468 s | 351.278 s |

实验核首 token 比稳定核慢 `12.541 s`，3 步 Decode 合计慢 `1.270 s`，这轮平均速率低约 `1.15%`。实验核第 2、3 步各比稳定核略快，但第 1 步明显更慢；单次顺序配对不能证明普遍性能劣势或优势，也不能把 M324 独立 KV852 三步的约 1.5% 优势外推到此处。

## 正确性与“吞吐率”的限定

两套完整会话输出 token 均为 `[15, 151645, 198, 58]`；四步完整 logits SHA-256 与最终 72 份 KV SHA-256 全部一致，KV 长度增至 162。每套调用数均为预期的 1264，板端收尾显示 DMA 空闲、无恢复待办。稳定 M254 网页服务已恢复并通过运行时就绪探针，PID `126540`；稳定 boot、DTB、CMA、分区和回滚目录未动。临时 `192.168.0.2/24` 地址已删除，原 `192.168.77.2/24` 及路由恢复。

**第 2 个 token（索引 1）是 EOS。** 因此后两步是为了比较硬件增量路径而强制续跑；表中的 0.027 token/s 是这 3 次真实板端增量计算的诊断速率，**不是二元问答服务的正常持续生成吞吐率**。这个任务正常只交付受限首 token 后结束。要测用户可见的长文本流式吞吐，必须另选不会立即 EOS 的自然语言任务，并重新核对 BACT token/批次预算与正确性。

Decode-one 容量专项仍为 `STOPPED_BY_USER_NOT_PASS`，不能称正式 RTL 容量 PASS 或稳定部署晋级。当前默认服务继续使用稳定 Build `0x4D395832`。若继续追求实验核晋级，先闭合容量证据，再做顺序交错、重复的非 EOS 实板配对；否则这轮结果足以支持项目交付时保留稳定实现并明确边界。

## 可复核证据

- 机器汇总：[M325_FULL_SESSION_BOARD_RESULT.json](deployment/mage_vl4b/M325_FULL_SESSION_BOARD_RESULT.json)，SHA-256 `b8d8175922443e2e434f3a54aabaa8cbd709d2cbc730621428c7b5a265e1d398`。
- 原始 COM3 日志：`tmp/m325_full_session_02_uart.log`，SHA-256 `bb51433c6dd111ed200899c35e1af1e8de9cf6acc7f1cfc4f1a3195037cbe31c`；门禁与恢复标记分别为 `__M325_GATE_RC_0__`、`__M325_RESTORE_RC_0__`。
- 板端完整结果：`/home/ubuntu/tellme_m120_m89x2_20260901/results/m325_full_session_02/video_stable.json` SHA-256 `569cdbe6b07cdf876a8355d700f59223528be2b1cf3540ebeb467fe8bc604a0b`；对应 candidate SHA-256 `6da360399a000042b0561173b4392e727ab9e2547d2222121a6b0b133d8225c0`。两哈希已另经 COM3 `sha256sum` 核对。
- attempt01 的回调失败和自动恢复保留在 `tmp/m325_full_session_uart.log`；修正版包在板端逐文件通过 `M325_SHA256SUMS.txt`。

本报告在 `reports/backups/M325_FULL_SESSION_PERFORMANCE_REPORT_2026-09-26.md` 保留同内容备份。
