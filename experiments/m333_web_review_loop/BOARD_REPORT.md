# M333 KV260 隔离板端软件门禁：PASS，真实 4B Web 复核未测

日期：2026-09-26。收到用户“先在板端验证”后，COM3 `sudo -n true` 返回 0，但本门禁**没有使用 sudo、没有加载 overlay、没有启动或停止稳定服务**。原稳定 Build `0x4D395832`、M254 入口和回滚目录未改。

## 范围与结果

- 本机先用**未修改的原 `video_server.py` Handler 类**、假检测器/假语义引擎测试 HTTP 提交、状态与 SSE。六帧形成两次不同报警，第一次完成后第二次从最新待处理窗口入队，两次终态均释放，全部 13 项检查 PASS。离线 `HTTP_SSE_RESULT.json` SHA-256 `55c05e8140aadb8b0ccff446f0532f64dd85622b9cdd0cdaef8809a423365fdb`。
- CPU-only 板端包为 6 文件白名单，`16,000 B`，归档 SHA-256 `a9264139488a97cbca1ad3abbd1b819e9bef473033396716b9372ef8c4e6e832`，传输契约 SHA-256 `ff4f0a52906ead29b581b6c4bb785e3280986ec31c98f0c0bc2f48cdf7dd67af`。经 COM3 逐文件/归档哈希核对，解入新的 `/home/ubuntu/m333_offline_board_01`；没有覆盖稳定文件。
- KV260 的 PYNQ Python 实际执行调度假引擎回归（13 项）和真实 HTTP Handler/假模型 SSE 集成（13 项），两者 PASS。板端 `BOARD_RESULT.json` SHA-256 `36ac06bb14b692057a0b172429cfa3f5b33ef73912e491dba49d12a239c4c405`，本机复原字节与板端 `sha256sum` 相同。原始 COM3 记录在 `tmp/m333/`。

## 尚未验证

这项板端 PASS 只证实 KV260 的 Python、NumPy、隔离调度器及 HTTP/SSE 协议路径可运行；**检测器、真实 4B 模型、FPGA 调用、报警触发后的真实语义推理和两次真实 Web 复核均未执行**。不能称为 M333 已部署或完整视频推理通过。网页和外部网络服务也没有被启动，本次 HTTP 监听仅测试进程的 `127.0.0.1` 随机端口，已关闭。

下一步需要独立准备真实 M254/M333 运行时依赖闭包和哈希包，先验证实际报警输入与任务身份，再在不破坏稳定回滚的前提下走完整板端门禁。用户不在场时不要求新的授权；如果届时 `sudo -n true` 过期，应停止在 overlay 之前，不尝试绕过。
