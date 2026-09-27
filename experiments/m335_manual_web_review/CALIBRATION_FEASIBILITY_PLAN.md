# M335 快速刀具通道：校准可行性检查预登记

不改 M254/M253 checkpoint、浏览器采样、板端阈值或稳定部署。现有标注 `data/bact_target_scene/M304_HUMAN_REVIEW_LABELS.json` 把 12 个 AI 生成视频分成 6 个 calibration 与 6 个 test，且标注为完整观看后的片段恒定标签。本轮只读 6 个 calibration；test 在候选规则冻结前不扫描。

采用 M249 SSDLite 原 checkpoint SHA-256 `a79551df90c79834bcd3bb3845ef9d966b5449a3a9b2833ae8404778ca5d65d2`，保持刀具类别 49 和当前近似浏览器中心裁剪 448×448。对每段 calibration 连续逐帧记录该类最高原始 score，并按片段取最大值；这仅是“是否曾有一帧足以触发”的离线候选分析，不是板端报警或独立准确率。已完成 `cal_working_knife_02.mp4` 和 `cal_working_no_knife_01.mp4` 全 289 帧扫描，直接复用，其他四段补扫，不重算已测片段。

预设停止规则：现有 `FastFramePolicy` 强制 `knife_safe_threshold < knife_alarm_threshold`，当前 safe 为 `0.20`。若任一有刀具校准片段全帧最高 score `<=0.20`，则保持 safe=0.20 的单一 alarm 阈值无可能召回全部校准正例，停止“只调 alarm 阈值”候选；不得把测试集拿来搜索阈值。若所有正例都高于 0.20，才检查负例片段峰值是否与正例分离；未分离则仍停止。即使分离，也只能形成开发信号，需先固定正负样本、事件级误报/召回约束和候选阈值，再对独立 test 一次验收，之后还要用浏览器真实 RGB448 和板端复测。

本检查不更改原 0.80 报警或 0.20 安全阈值，不宣称已校准，也不以一段触发视频替代目标场景有效性。
