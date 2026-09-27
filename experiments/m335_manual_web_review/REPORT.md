# M335 v3：KV260 真实 Web 手动 4B/FPGA 复核

日期：2026-09-27。结论：`PASS_MANUAL_WEB_ONLY`。本轮隔离候选未晋级或替换稳定 M254，自动报警触发链路仍未通过。

## 范围与身份

候选 `deployment/mage_vl4b/optimization_v1/candidates/M335-manual-web-review-02/` 把 M333 单活跃＋最新等待任务调度与原 M254 网页 Handler 连接；新增 `POST /api/4b/video/live/review`，显式记录 `trigger=manual`，不伪造自动报警。仅语义复核运行时改接已有板端验证的 M276：收到四帧源窗口，但语义计算只取末帧 `[3]` 的两视图、98 视觉 Token、159 总 Token、T32 五批、受限 0/1 logits。**这不是四帧时序动作理解**，也不改变快速通道 0.80 自动刀具阈值。

COM3 上传独立 7 文件包 `tmp/m335/M335_MANUAL_BOARD_PACKAGE_v3.tar.gz`，包 SHA-256 `d9223e189dc415b21dc545293f499b5ecd8f4e447312a7b7d83a9359274429b8`；板端逐文件哈希核对通过。同终端 `sudo -n true`、root、`XILINX_XRT=/usr`、`TMPDIR=/dev/shm`、PYNQ-venv xclbinutil、`xclProbe()==1`、恰好一台 PYNQ 设备、原 M175 package-manifest SHA `406dcca340e4604baeb761445795391c43ec26bd99fa06ffae893d597b17414f` 均 PASS。未更改 boot/DTB/CMA、稳定目录或回滚。

## 固定视频实板结果

采用既有 M328 哈希锁定 RGB448 四帧，两次顺序回放；这是同一视频窗口重复提交，不是两个独立质量样本。网页按钮可见，模型未获四帧时返回明确 `MISSING_FRAMES`。任务 #1 关联源帧 `[0,1,2,3]` 并启动；忙时任务 #2 关联 `[4,5,6,7]` 等待。两项均有真实 `token`、`complete`、FPGA proof、`semantic_review_result` 和 `semantic_review_released`，任务 ID 与源/语义序列无串线。结束后 active/waiting 清空、运行时仍加载一次、SSE 无错误，可继续接收新事件。

| 指标 | 任务 #1 | 任务 #2 |
|---|---:|---:|
| 首 Token（推理开始至首 Token） | 196.286 s | 174.653 s |
| 单窗口语义总耗时 | 196.287 s | 174.654 s |
| 结果 | `0` / ABSENT | `0` / ABSENT |
| Prompt / 视觉 Token | 159 / 98 | 159 / 98 |
| FPGA 逻辑调用 | 778 | 778 |
| Build-ID | `0x4D395832` | `0x4D395832` |
| 语言 CPU Linear fallback | false | false |

整次门禁 660.068 秒，含服务启动/模型加载/两次执行/收尾，**不是**单次首 Token 延迟，也不能当持续视频吞吐率。每次输出内容与先前固定样例一致，但同一视频重复两次不能证明新场景准确率。没有自动 `safety_result.alarm.active`；这验证手动入口未制造假报警，不验证自动触发正确性。

## 失败与局限

- M335 v1 包清单 CRLF 导致板端 `sha256sum -c` 拒绝，未加载模型；修正后保留原失败。
- M335 v2 使用原 M254/M243 全四帧长输入，在 900 秒内未完成两次真实 4B 复核；第一轮 24 层视觉约 317 秒。v3 选择的是**不同语义输入合约**，不能把两者耗时直接宣称为同条件模型提速。
- 本轮没有校准刀具阈值、没有完成自动报警→4B→网页回传、没有做新视频质量/动作评估；不晋级稳定部署。自动触发定向审计见本目录的 [AUTO_TRIGGER_AUDIT.md](AUTO_TRIGGER_AUDIT.md)。

## 可审计文件

- 原子板端 JSON：`BOARD_RESULT.json`，SHA-256 `8a498ee839e5cf42b13a1f779351888e0673a726641518bc26e59b4a4e131754`。
- 完整服务日志：本发布目录 `SERVICE_TRACE.txt`（板端原名 `SERVICE.log`），SHA-256 `2fc351e3364b8549ad379033a0977fa92d9d7ca95700773fea7088dd53c23f13`。
- 原始串口在所有者工作区 `tmp/m335/real_web_gate_v3_uart.log` 等路径，不进入 Git；公开包保留哈希锁定的板端 JSON、完整服务追踪及报告。
- 本机假模型协议回归 18 项 PASS；它只验证调度/HTTP/SSE，不替代上述实板证据。

下一步若要验证自动报警，先用正负样本独立校准并留出验收，不改阈值迎合当前样例；然后在原规则下完成真实报警触发、4B 复核和 Web 回传。若只需手动入口，可将此独立候选作为演示路径，但应保留“末帧两视图、约三分钟一次受限判断”的明确界限。
