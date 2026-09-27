# 实验索引

首页只列出代表性结果；本目录保留测量条件、机器结果和没有采用的候选。实验编号用于追溯，不表示读者必须按编号阅读。

| 研究问题 | 从这里看 | 可得出的结论 |
| --- | --- | --- |
| 固定视频能否在独立安装中完成推理？ | [公开固定视频结果](fixed_video/RESULT.json) | 在稳定 T32 Build 上完成末帧双视图的 4B 首 Token；不是四帧时序理解。 |
| PS–PL 代表性 Linear 的数值与耗时如何？ | [最初 CPU/PL 检查](m329_original/) · [原生 A53](m330_cpu/) · [同会话配对](m331_paired/REPORT.md) | W2/W4 固定双 descriptor 链有局部 PL 收益；没有整模型 CPU-only 基线。 |
| 输入压缩与固定批边界怎样影响成本？ | [BACT 质量配对](bact_v2_quality/paired_quality.json) · [方法和板端成本](../docs/bact_v2.md) | 164→159 跨过 6→5 批，159→144 不减少批次；旧质量样本未证明 BACT-159 优于 count-144。 |
| 解析器短测提速能否缩短整视频请求？ | [A53 短测与双顺序视频 A/B](m332_parser_scale/REPORT.md) | 局部优化没有带来端到端收益，稳定解析器保留。 |
| Web 能否连续安排和完成复核？ | [调度与 HTTP/SSE](m333_web_review_loop/) · [真实手动复核](m335_manual_web_review/REPORT.md) | 两次手动请求完成真实 4B/FPGA→SSE；自动报警触发没有在此通过。 |
| 快速刀具触发为何仍不可靠？ | [浏览器输入短诊断](m336_browser_input/REPORT.md) · [六段本地视频抽样](m337_real_video/REPORT.md) | 网页与 loopback 帧字节一致；现有检测器在这些厨房样本中分数偏低，简单放大未解决。 |

HLS 资源、批边界扫描和 Decode-one 单会话结果仍按原始文件名保存在 [`deployment/mage_vl4b/`](../deployment/mage_vl4b/)；[结果总表](../docs/results.md)给出关键数值与每项范围。这里不包含原始个人视频、逐帧截图、模型权重或 bitstream。
