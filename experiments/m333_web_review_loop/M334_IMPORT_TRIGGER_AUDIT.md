# M334：真实 M333/M254 板端导入与触发夹具审计（2026-09-27）

结论：**前置导入与发布资产身份 PASS；真实自动报警→4B→SSE 未运行，也未晋级。** 原稳定 Build-ID `0x4D395832` 的资产和回滚未改。本轮没有加载 overlay、检测器或 4B 模型，没有发起 Web 请求。

## 实际板端证据

- COM3 同一登录终端的 `sudo -n true` 返回 0，但本轮只读导入和资产检查未使用 sudo。
- 哈希核验的版本化导入探针：`scripts/optimization/m334_real_import_probe.py`，SHA-256 `66249d1a40ce05189aab2870704cf3d2bd5d3cea9f2a7c96951a57931ce21a25`。板端原子结果 `BOARD_RESULT.json` 与 COM3 复建文件 SHA-256 均为 `b7bec374283e981c83d072433c8269827ee1bbb1b041e81cacb331d339c2994d`。
- 实际导入 `m333_review_bridge`、原 `m254_video_server` 与 `m333_video_server` 均从预期目录解析；板端源码 SHA 分别为 `ad42c5d58dabe419dca545d18b66df3b31c765def16de587ddfb40e4049547bf`、`86e2c79740af645449db5b2f8c64246000dab1896a30b4148e5c90f1e321fc6f`、`b2281dcbe8c4b6d9f65b5e7f1222ace70c6eb9cf5c85d8d623c78c982772362e`，均与本机对应源码一致。真实 `video_server.LiveController` 已绑定 M333 类。导入耗时 18.78 秒，不是模型加载耗时。
- 原发布版 `scripts/preflight.py --check` 报 `READY_FOR_BOARD_PREFLIGHT`，`missing=[]`、`hash_or_identity_mismatch=[]`，Build-ID 目标 `0x4D395832`；它没有启动板端服务。日志 `tmp/m334/release_preflight_check_uart.log` SHA-256 `ef6cd29fb788eef6b47548694b3ddc72ce26b1fb557fd8a04245ecdf54c7bd25`。
- 当前只读端口检查未发现 8001 监听者，也未发现 `m254_video_server.py` 进程；稳定目录仍在。没有为了本轮测试停服务或覆盖稳定目录。

## 自动报警夹具缺口

未改变 M249 SSDLite checkpoint（SHA-256 `a79551df90c79834bcd3bb3845ef9d966b5449a3a9b2833ae8404778ca5d65d2`）和刀具报警阈值 `0.80`。主机端对已有 6 段刀具视频各均匀抽样 25 帧，以近似浏览器中心裁剪形成 RGB448；150 个抽样帧中没有达到报警阈值，最高刀具分数 `0.147813`。结果 `tmp/m333/historical_crop_trigger_scan_25.json` SHA-256 `a6469797db14d16fc365c1d6ae57cd269299dde081b5871434c7efc3e68b1413`。这不证明整段所有帧都不会报警，也不代替精确 Canvas/板端输出。

另以 3 张公开可用的清晰刀具图片做**功能夹具搜索**，同一未改 checkpoint 下最高 `0.186304`，同样未达到 `0.80`。它们不是监控视频、不是独立准确率数据，且没有传上板。来源分别为 Pexels 图片 5237008、16457297、11209032；记录 `tmp/m334/still_probe.json` SHA-256 `acd93f940fecea78d615f962d5c7ea3048534d5041886b0db9690f3e7988e3d0` 与 `tmp/m334/still_probe_02.json` SHA-256 `b7cf11af6bec8af28cf21c1b018c25ec017e7a24ec957036b5609214abe5c962`。图片只在本机 `tmp/` 作诊断，不进入 GitHub 发布包。

因此本轮**没有**伪造报警结果、降低阈值、重放假引擎事件或把前置 PASS 称作真实 Web/4B PASS。若坚持自动报警验收，需要在冻结阈值下找到真实会触发的合法视频并先在板端确认检测结果；或者另行校准/替换快通道并重新做准确率门禁。若只想先证明网页里的真实 4B/FPGA 路径，可在隔离候选中增加显式手动复核入口，独立验收，不能代替自动报警链路。

原始 COM3 导入日志 `tmp/m334/real_import_probe_uart.log` SHA-256 `b4aca7a2a1543d99d50faa9de281fa7331c368f635bb951c476ae2fbed921a4d`。拒绝尝试：M333 仅假运行时通过，不晋级；本轮历史视频和三张图库图片均未形成自动报警夹具。
