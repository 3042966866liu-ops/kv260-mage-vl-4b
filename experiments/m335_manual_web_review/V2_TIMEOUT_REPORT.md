# M335 手动 Web→4B/FPGA 隔离候选 v2：超时，未通过

2026-09-27。稳定 Build `0x4D395832`、原 M254 目录与回滚未修改；候选没有晋级。

## 已验证部分

- v1 包因 Windows CRLF 清单在 `sha256sum -c` 被拒绝，未加载模型/overlay；保留 `tmp/m335/real_web_gate_uart.log`。
- v2 包 TAR SHA-256 `b3ad65b710a636edc303d76b473de079f5d5750e10ded0fcf69b5f48de7e134f`，7 个文件逐项哈希 PASS。
- COM3 同终端 `sudo -n true`、固定 M175 root/XRT/PYNQ 环境门禁 PASS；`xclProbe=1`、PYNQ 设备数 1、PYNQ-venv `xclbinutil` 与 M175 清单哈希吻合。
- 真实隔离网页返回手动按钮；真实 Web 会话和 4B/FPGA runtime 加载一次。未满四帧手动请求返回 `MISSING_FRAMES`。四帧视频经 HTTP 发送后任务 #1 进入 active；另四帧在其忙时经 HTTP 发送，任务 #2 进入 waiting，来源序号分别 `[0,1,2,3]`、`[4,5,6,7]`。该输入是既有 M328 真实视频四帧夹具的两次本地循环，不是两个独立视频。

## 首个未闭合门禁

等待两次 `semantic_review_released` 的 900 秒预算超时。完整服务日志显示第一轮已进入真实 24 层视觉塔并在约 317 秒完成视觉前向；之后语言阶段仍运行，但在门禁预算内未形成可核验的 `complete`、最终 FPGA 调用证明或第二次复核。因此不能宣称 Web→4B/FPGA→结果回传 PASS，也不能把任务受理视作推理完成。隔离服务在门禁退出时已停止；没有修改稳定目录。

板端原子结果与 COM3 重建的 [V2_BOARD_RESULT.json](V2_BOARD_RESULT.json) SHA-256 `66e878a3168db9f25f7a1cfadb4f7c7af659d232d160af4401eb4a79424786e0`；完整 [V2_SERVICE_TRACE.txt](V2_SERVICE_TRACE.txt)（板端原名 `SERVICE.log`）SHA-256 `7c578f593fdf5b83b023d7945761dcf8bf32f06ed91f05dceac3486249406e32`，原始 COM3 记录保留在所有者工作区 `tmp/m335/real_web_gate_v2_uart.log`，不进入 Git。

## 定向修复

M335 v2 继承原 M254→M243 全四帧语言路径；它尚未使用既有 M276/M277 的 159 Token、5 批路径。下一次只在独立候选的运行时选择层接入已通过固定视频门禁的 M276 受限 0/1 路径，继续沿用同一 M333 手动/自动调度、任务身份和 SSE；原自动报警阈值保持 `0.80`。先做离线接线与哈希检查，再重测当前失败的真实 Web 级，不把 v2 超时抹掉。
