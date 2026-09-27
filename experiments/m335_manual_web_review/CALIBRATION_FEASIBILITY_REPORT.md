# M335 快速刀具通道：仅调报警阈值不可行

结论：在本次**六段 AI 生成校准视频**的近似浏览器裁剪、原 M249 checkpoint 下，当前双阈值实现不存在“只调 `knife_alarm_threshold` 且保持 `knife_safe_threshold=0.20`”即可召回全部三段正例的可行区间。没有修改原 0.80/0.20 阈值、模型或稳定部署；六段独立 test 视频未用于本次搜索。

预登记规则见 [CALIBRATION_FEASIBILITY_PLAN.md](CALIBRATION_FEASIBILITY_PLAN.md)。人工标签来自 `data/bact_target_scene/M304_HUMAN_REVIEW_LABELS.json`，SHA-256 `9a60bfe6fc0c58b3340897744d2f9b4297ff39e5ec79cb5ad66fba8bf61d9055`；逐段视频 SHA 与标签记录匹配。复用此前已扫描的两段 289 帧，只新扫其余四段；每段连续覆盖 289 帧，共 1,734 帧。新增四段原始扫描 `tmp/m335/calibration_remaining_full.json` SHA-256 `b40923d32c01033240708e2005b92b9f364a8e3f1d7a922150c37714560a7b1a`。冻结 M249 checkpoint SHA-256 `a79551df90c79834bcd3bb3845ef9d966b5449a3a9b2833ae8404778ca5d65d2`，类别 49 为 knife；板端同版本实现会过滤 `<0.05` 的检测框。

| 校准视频 | 人工刀具标签 | 全帧原始 knife score 最大值 | 经过 `<0.05` 过滤后的最大值 |
|---|---:|---:|---:|
| `cal_falling_no_knife_01.mp4` | 无 | 未返回 knife 框 | 0 |
| `cal_fighting_no_knife_01.mp4` | 无 | 未返回 knife 框 | 0 |
| `cal_idle_knife_01.mp4` | 有 | 未返回 knife 框 | 0 |
| `cal_walking_knife_01.mp4` | 有 | 0.028569 | 0 |
| `cal_working_knife_02.mp4` | 有 | 0.147813 | 0.147813 |
| `cal_working_no_knife_01.mp4` | 无 | 未返回 knife 框 | 0 |

原 `FastFramePolicy.validate()` 要求 `knife_safe_threshold < knife_alarm_threshold`；因此保持 safe=0.20 时 alarm 必须大于 0.20，而三段正例的经过过滤后峰值全部低于 0.20。特别是两段正例根本没有可用于阈值选择的存活 knife 框。故降低 **alarm 单一阈值**既无法覆盖校准正例，也不满足现有规则。不能靠直接把 0.80 调成 0.10 之类的值作为自动报警验收。

此结论限当前六段 AI 视频及 OpenCV 近似 Canvas 中心裁剪，不说明其他真实场景中检测器一定失败，也不评价 4B 复核质量。第 48、144 帧的可视诊断显示工作场景的刀具仍在裁剪中心，但未做浏览器 RGB448 字节级对齐。下一步若要解决自动触发，应先核对网页实际输入，再在正负新视频上评估检测器/预处理或替代触发源；任何新策略必须冻结后在独立 test 集及板端验证事件级召回、误报和延迟。**本轮没有扫描独立 test，也没有调整阈值。**

可复算机器结果 `CALIBRATION_FEASIBILITY.json` SHA-256 `74ba6b4a9f37839bcbe1c77b3b5dec6a074dd1202a6e6dadc6d232ac8f7a62e4`；本发布目录附有 `CALIBRATION_SCAN_REMAINING_FOUR.json`、`CALIBRATION_SCAN_EXISTING_TWO.json` 和 `m335_calibration_feasibility.py`。在仓库根目录运行 `python3 experiments/m335_manual_web_review/m335_calibration_feasibility.py --labels data/bact_target_scene/M304_HUMAN_REVIEW_LABELS.json --scans experiments/m335_manual_web_review/CALIBRATION_SCAN_REMAINING_FOUR.json experiments/m335_manual_web_review/CALIBRATION_SCAN_EXISTING_TWO.json --output /tmp/m335_feasibility_recomputed.json` 可重算；这是离线数据复算，不执行模型或板端推理。这只是一项负的可行性审计，不是自动报警或完整监控部署 PASS。
