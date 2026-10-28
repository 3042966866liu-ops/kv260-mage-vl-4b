# 校园安防协同复核台

本地启动（PowerShell）：

```powershell
& 'C:/Users/30429/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/python.exe' -X utf8 -B apps/campus_guard/server.py --port 8765
```

浏览器访问 http://127.0.0.1:8765 。仅监听本机；所有前端资源均为本地文件。

## 已实现

- 食堂后厨、实训工坊两个**模拟**机位，视频播放、4/8秒冻结窗口和对应实际448输入截图。
- 真实历史板测的四窗口判断、逐条TTFT、首次/热态条件及原始证据SHA。
- 模型复核、人工确认、正常作业/需要关注/误报的处置记录；SQLite持久化、版本冲突保护和JSON导出。
- 串行任务队列，工作器失联、推理失败或超时均不转换成“No”。
- 实时结果接口绑定任务nonce、输入帧、已冻结模型包、完整词表、真实物理调用及新结果证据路径；不能直接提交历史答案冒充实时推理。
- 桌面/手机布局；实际Chrome 15项交互检查、7项后端软件检查通过。

## 当前边界

默认是**实板记录查看模式**，不是已接通的实时模型服务。实时板端工作器未接通，因此“发起板端复核”按钮禁用，MQTT显示未配置。页面不自动生成假判断、不按视频文件名或窗口查表伪装推理。

历史记录对应 M525 small8 增强训练输出头、10视觉/18语言层，4/4固定窗口实板正确；热态两次29.227/29.121秒，首次49.879秒。这不代表任意视频泛化准确率；后续续写不是验收目标。页面历史值不随实际推理未运行而假装更新。

## 实时工作器接口（已实现网页侧，板端接线待验收）

工作器token由首次启动生成到 `var/worker_token`，仅后端读取，不发送给前端。

- `POST /api/worker/heartbeat`，头 `X-Worker-Token`，字段 `ready`、`warm`、`build`。15秒未更新自动显示失联。
- `GET /api/worker/next`：同token，领取唯一任务；返回job ID、case、原帧SHA、冻结模型包SHA，不返回预期答案。
- `POST /api/worker/result`：同token，提交job ID、新证据JSON的工作区相对路径及SHA。证据必须在 `optimization_v1/runs` 下，含 `ui_job_id`、`case_id`、`frame_sha256`、`package_manifest_sha256`、`actual_full_vocab=151936`、`physical_calls>0`、`primary_rc`、`argmax_verified`、`decision`和 `TTFT_s`。
- 浏览器只能选择已冻结四个窗口；当前网页进程不直接打开COM3、加载Overlay、启动子进程或提交DMA。

板端接线将沿用COM3控制和原七缓冲区生命周期，必须先通过新软件组件及同固定窗口E2E门禁，不自动改稳定Overlay或扩大权限。

## 验证

```powershell
& 'C:/Users/30429/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/python.exe' -X utf8 -B apps/campus_guard/test_server.py
$env:CAMPUS_BROWSER_EXE='C:/Program Files/Google/Chrome/Application/chrome.exe'
& 'C:/Users/30429/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/bin/node.exe' apps/campus_guard/qa_browser.cjs
```

`qa/desktop.png`、`qa/mobile.png`、`qa/report.png` 是实际浏览器截图。浏览器检查不创建板端推理。后端测试只在临时根使用明确标记的合成worker结果，不写硬件门禁证据。

`prepare_assets.py` 仅核对旧板测及原视频SHA并生成截图与catalog，不运行模型。请保留原工作区依赖，网页目录不包含全部模型和位流。
