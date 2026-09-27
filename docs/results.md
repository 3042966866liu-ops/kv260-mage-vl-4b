# 实测结果与证据

以下数值来自已有记录；本页没有新增板端推理。稳定 T32 Build ID 为 `0x4D395832`。每一项的输入、计时范围和推理入口不同，不应相加为一条未经测量的完整吞吐曲线。

| 问题 | 结果 | 条件与原始证据 |
| --- | --- | --- |
| 独立安装后能否完成固定视频推理？ | 首 Token `230.721 s`；PS 视觉 `43.638 s`，随后语言至首 Token `187.011 s`；输出 `0`，778 次逻辑 FPGA 调用 | 四帧 RGB448 按顺序提交，模型只使用末帧的两个视图；159 Token、5 个 T32 批次，不含初始化。[公开摘录](../experiments/fixed_video/RESULT.json)；[复现说明](fixed_video_reproduction.md) |
| FPGA 对代表性 Linear 链有什么收益？ | W2：A53/PL `5.891/2.244 ms`，约 `2.63×`；W4：`5.871/2.525 ms`，约 `2.33×` | 同板同量化、两种固定双 descriptor 链，各 10 对交错；计时不覆盖视觉或全模型。[原始配对](../experiments/m331_paired/)；[条件说明](cpu_pl_benchmark.md) |
| Token 减少何时降低 T32 开销？ | 164→159 Token：6→5 批，932→778 次逻辑调用；144 Token 仍为 5 批/778 次 | 固定语言 Prefill 几何；27 条板端边界记录。调用数不是耗时。[BACT 方法](bact_v2.md)；[边界原始结果](../deployment/mage_vl4b/M294R3_COUNTERBALANCED_BOUNDARY_BOARD_RESULT_05.json) |
| Web 请求能否进入真实 4B/FPGA 并回传？ | 两次手动请求均完成；首 Token `196.286/174.653 s`，每次 778 次逻辑调用 | 隔离演示入口；后一任务在前一任务忙时排队，SSE 结果按任务 ID 归属。仅使用窗口末帧的两个视图；不是自动报警。[实验报告](../experiments/m335_manual_web_review/REPORT.md) |

## 对候选优化作出的取舍

| 候选 | 原本要改善什么 | 实测与选择 |
| --- | --- | --- |
| 输出解析的临时数组缩放 | 减少 A53 解析时间 | 组件短测约 `1.76–2.04×`；两组固定视频 A/B 中，候选首 Token 分别多用 `20.224 s`、`7.023 s`。完整请求没有显示收益，因此仍使用稳定解析器。[双顺序结果](../experiments/m332_parser_scale/CLOSURE.json) |
| Decode-one 专用核 | 提高单 Token Decode 效率 | 一次同会话对照中，稳定核三步合计 `108.936 s`，实验核 `110.206 s`；第二个输出已是 EOS。实验核没有整体收益，且容量专项未完成，未成为稳定核。[原始记录](../deployment/mage_vl4b/M325_FULL_SESSION_BOARD_RESULT.json) |
| 缩短输入与对齐批边界 | 消除完整的 T32 执行批次 | 固定样例从 164 到 159 Token 后，逻辑调用减少 154 次。旧 12 段合成视频未证明 `bact-159` 的质量优于同为五批的 `count-144`；质量结论仍限于开发样例。[质量配对](../experiments/bact_v2_quality/paired_quality.json) |
| 快速刀具触发 | 自动挑选需 4B 复核的窗口 | 当前检测器在六段本地厨房视频的 253 张实际网页采样帧上，六片刀具分数峰值均低于既有 `0.20` 安全阈值；简单中心放大也未可靠区分刀具与汤勺。[诊断记录](../experiments/m337_real_video/REPORT.md) |

硬件实现的单独资源结果：T32 全壳 DSP 使用率 `85.74%`、LUT `33.82%`、WNS `+0.147 ns`，见[实现结果](../deployment/mage_vl4b/M300_BACT_RESOURCE_BINDING_RESULT.json)。这不是运行时吞吐或功率指标。

固定视频 `230.721 s` 是直接推理入口的单次首 Token；手动 Web 的两次时间来自另一隔离会话。M325 的三步增量 Decode 也是另一会话，并且出现 EOS，不能与前述首 Token 拼接成持续生成速率。更多耗时范围见[性能分析](performance_attribution_history.md)。
