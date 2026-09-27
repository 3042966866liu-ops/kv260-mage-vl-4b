# M336 浏览器真实输入短诊断（离线）

本轮只检验“浏览器裁剪/RGB 传输是否造成刀具消失”这一假设；不重跑 4B，不改原 M249 检测器、`0.05` 过滤、`safe=0.20` 或 `alarm=0.80`，不访问 KV260，不动稳定服务。

使用 M335 未改动的 `static/app.js`（SHA-256 `3aa35208a7739cb9068796735aec78410f39f94d48041f0b41bf3cf397dfd95e`），由 Chrome `153.0.8010.53` 本地解码两段 **AI 生成的 calibration** 视频，在 `4.8 s` 运行真实 `drawCover()`/`sendFrame()`。请求发往本机 loopback 接收器，**不是**板端服务。两个接收帧均为 `448×448×3`、`602112 B`、`application/x-tellme-rgb448`，浏览器与接收端逐字节 SHA-256 相同。

| 样例 | 浏览器/接收端 RGB SHA-256 | 原 M249 SSDLite 类别 49 原始最高分 | 原 0.80 报警 |
|---|---|---:|---|
| `cal_working_knife_02.mp4`，人工标注有刀 | `ec78d9ea223e68646ada965c3f7a2bff8b75043209184a1f0d3c454d56a133f7` | `0.052441` | 不触发 |
| `cal_working_no_knife_01.mp4`，人工标注无刀 | `1726eae8e4a03abeddf2982be904e5e07774a91578c18dd7af2070ecb826cfe1` | 无刀具框 | 不触发 |

已保存的正例浏览器画面里，厨师手中的菜刀在中心裁剪内清晰可见。使用原 M249 checkpoint（SHA-256 `a79551df90c79834bcd3bb3845ef9d966b5449a3a9b2833ae8404778ca5d65d2`）和原输入变换 `RGB uint8 → CHW float/255` 在 WSL/GPU 做短诊断；正例刀具分数仅 `0.052441`，刚过 `0.05` 检测过滤且低于 `safe=0.20`。这增强了“当前检测器对该 AI 样例响应弱”的证据，**不**代表真实摄像头召回率，也不代表板端 CPU 得分逐位相同。

源码审计：M335 页面先中心正方形裁剪、Canvas 缩放到 448，再按 R/G/B 顺序打包；继承的服务入口仅按固定长度以 `np.frombuffer(...).reshape(448,448,3)` 接收，不做 BGR 交换。实际板端 Web 请求字节尚未直接采集，因此本轮结论仅限浏览器→本机接收器；不能把两帧诊断写成完整自动报警链路 PASS。M335 v3 手动复核仍只取四帧窗口末帧两视图；v2 全四帧超时与 v3 完成不能用于同输入性能对比。

复现脚本：`scripts/optimization/m336_capture_actual_browser_rgb448.js` 与 `scripts/optimization/m336_score_actual_browser_rgb448.py`。原始本地结果 `tmp/m336/browser_positive/RESULT.json` SHA-256 `648224f9e74e9f146719c4e84296ff0bbbb9df0699fab747b9cc76eeb4b68507`、`tmp/m336/browser_negative/RESULT.json` SHA-256 `a038b14c16dbd1d2f22886e24ad734d2f44e401d6906599895bc2892e39df073`、`tmp/m336/M336_EXACT_BROWSER_DETECTOR_RESULT.json` SHA-256 `0fe9c6000ced73a953aa71d0f21c79f9cea82a802807235520ba4495d2232e44`。原始视频/帧不进入公开 GitHub，公开机器摘要为本目录 `RESULT.json`。

下一步先收集有授权的真实摄像头正例、负例和刀具相似物，冻结片段级标注与拆分。对真实浏览器 RGB448 查看检测框及分数；若输入正确而仍系统性漏检，才在隔离候选考虑替换或微调快速检测器。不能为演示直接降低阈值，也不能把“检出刀具”等同“危险行为”。
