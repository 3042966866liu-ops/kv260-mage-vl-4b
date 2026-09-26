# M332 双顺序固定视频 A/B 归档（2026-09-26）

结论：M332 解析器微测虽通过且位精确，但同一四帧 4B 直接推理的两组 A/B 均未产生端到端收益。候选正确执行，然而 `baseline→candidate` 观察到慢 `20.224 s`，唯一补充的 `candidate→baseline` 仍慢 `7.023 s`；预登记要求候选至少节省 `11.536 s`。因此 `REJECT_NO_E2E_GAIN`，M332 结束，**原稳定实现及回滚保留**。两组不足以证明候选固有变慢的统计结论，也不能定位波动的根因。

| 测量顺序 | 稳定首 Token（加载外） | 候选首 Token（加载外） | 候选−稳定 | 语言 Prefill 候选−稳定 | 视觉候选−稳定 |
|---|---:|---:|---:|---:|---:|
| 稳定→候选 | 205.050 s | 225.274 s | +20.224 s | +20.495 s | −0.270 s |
| 候选→稳定 | 215.864 s | 222.887 s | +7.023 s | +8.539 s | −1.513 s |

两组均为四帧张量 SHA-256 `5911485955780036ac4c8990bcaa248667f2e86bd1fd6f9b0783002553b4adff`，实际语义只取末帧 `[3]` 的两视图，159 Token、Build `0x4D395832`、778 次逻辑 FPGA 调用、语言 CPU Linear fallback=false；输出 Token `15`、文本 `0`、ABSENT 与未校准分数 `0.441673` 相同。稳定模块 SHA-256 `d8061b561fe4d2a089523fde0d3860684244e76bca9646f255f03134fb50be56`，隔离候选 SHA-256 `7e36223f762cfc04c0fc74e3f468664e05d38b8f8024c8eb194e77cdc12944e8`。这些是功能身份检查，不是完整 logits 逐元素对照，也未测持续 Decode。

两次差额都集中在语言 Prefill，不在视觉。加载到预处理的差额分别为 +44.060 s 和 +52.133 s，但不计入首 Token，不能直接解释上述差值。现有 159-Token 视频日志没有把语言阶段再拆成权重文件读取、解析、设备等待及 PS 算子，因此不能宣称 M332 本身造成多少秒回退。`ATTRIBUTION_AND_REPEAT_DECISION.md` 及同哈希备份保存了补测前的判断；历史 849-Token M239 子阶段画像只能指导将来的真实路径分段，不得代替本次归因。

反向包只安装在板端隔离目录 `/home/ubuntu/m332_parser_scale_video_pkg_03`；仓库副本位于 [`reverse_board_package`](reverse_board_package/)。manifest SHA-256 `8f88a5e2fffefcd7fa9e58d68d2f343d43c2922e251ff4547a09300847ca9407` 与板端一致；3 个 payload 文件逐项哈希 PASS。同终端 `sudo -n`、root/XRT/PYNQ 环境、51 文件闭包及实际导入身份在 overlay 前 PASS。候选和稳定均返回完整固定视频功能 PASS；没有覆盖稳定目录、bitstream、boot/DTB/CMA/分区。原 attempt01 前置失败和首轮负结果未覆盖。

机器证据：首轮 [`SUMMARY.json`](SUMMARY.json) SHA-256 `66629c1fef56530ee88251890455603a71f8207c433825d12f29afa3a98f0755`；反向组 [`REVERSE_CANDIDATE_BOARD_RESULT.json`](REVERSE_CANDIDATE_BOARD_RESULT.json) SHA-256 `00b039c6638bcc4b79d72247637230d8cd2c8c8863df48a429d5bb9ffc94bef0`、[`REVERSE_BASELINE_BOARD_RESULT.json`](REVERSE_BASELINE_BOARD_RESULT.json) SHA-256 `211879324a4119e88160ca77f3209b0680c02d520b8ca28bbb14b2b95d58aebf`、[`REVERSE_SUMMARY.json`](REVERSE_SUMMARY.json) SHA-256 `28fc49fbedfa6842c71a37987594c1feef28ea956cbb033436a4e1acac5370e7`、双组 [`CLOSURE.json`](CLOSURE.json) SHA-256 `4457e07909fec6f4f27d99b7574252d759e744e62ab62cb82785eb5932a16bef`；原始 COM3 日志在维护者工作区 `tmp/m332/reverse_candidate_full.log`、`reverse_baseline_full.log`，未随此公开仓库提供。板端时钟不作为时间证据，分段均来自单调时钟。

离线复算：在仓库根目录运行 `python3 experiments/m332_parser_scale/m332_close_two_pairs.py`。脚本逐个核对四份板端结果的 SHA-256 和身份后生成 `CLOSURE_REPRODUCED.json`；本次该文件与冻结 `CLOSURE.json` 的 SHA-256 完全相同。

后续不再围绕 M332 做额外复测，也不重做阶段 B。只有真实 159-Token 链分段数据揭示明确、收益可观的新瓶颈，才重启阶段 D；否则复用已有 BACT-V2 成本/质量证据，优先完成独立质量验证和 Web 报警触发→4B 复核→结果回传闭环。
