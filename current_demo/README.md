# 当前校园刀具演示源码（2026-10-28）

这里集中保存当前演示链路实际依赖的网页、Windows串口桥、KV260/A53运行时、M455 FPGA内核，以及剪枝和教师学生恢复代码。原文件保留项目相对路径与SHA；根目录旧版本、旧Release和失败历史不因此改写。

## 当前版本

| 项目 | 当前采用 |
|---|---|
| FPGA | M455，Build `0x4D343535`，T32 |
| 结构 | 24视觉块/36语言块 → 10视觉块/18语言块 |
| 输入 | 一张选定采样帧的全局＋中心细节双视图；98视觉token、128总token、4批T32 |
| PS视觉压缩 | V2/V3/V6为3072；V4贡献选组＋恢复至3584 |
| 学习恢复 | V4 fc2重构并导回W4；M542 rank8全词表残差头 |
| 网页 | `apps/campus_guard/live_server.py`，本机8766，实际播放触发新板端请求 |
| 报警 | 新真实Yes显示红色警告；No不显示判断/报警；错误保留未知状态；页面不显示TTFT |

当前任务是“是否可见刀具”的演示研究。每次播放只推理一张明确采样帧，**不是全片逐帧或持续刀具跟踪**。4B模型可用于语义复核；其他问题（如手持关系）未完成本版验收，不能作为已支持功能展示。

## 源码导航

| 内容 | 入口 |
|---|---|
| 网页与上传/任务队列 | [live_server.py](apps/campus_guard/live_server.py)、[server.py](apps/campus_guard/server.py)、[前端](apps/campus_guard/static/playback_live.js) |
| 当前启动与COM3桥 | [start_demo.ps1](apps/campus_guard/start_demo.ps1)、[run_live_worker07.py](apps/campus_guard/run_live_worker07.py)、[live_uart07.ps1](apps/campus_guard/live_uart07.ps1) |
| 实际板端工作器 | [07包](deployment/mage_vl4b/optimization_v1/candidates/M544-campus-live-worker-07/)；`native.py`、`live_protocol.py` |
| PS–PL运行时、权重预取与解析 | [当前运行时](deployment/mage_vl4b/optimization_v1/candidates/M544-freshboot-runtime-05/)及07包中的C解析/语言解析代码 |
| FPGA内核与递归头文件 | [冻结M455 HLS源码](deployment/mage_vl4b/optimization_v1/candidates/M455-dense_output-02/hls/) |
| 当前10V18L结构生成 | [speed_candidates.py](experiments/demo_recovery_20261025/speed_candidates.py) |
| 整层删除与KV索引收缩 | [runtime_demo.py](experiments/fixed_demo_prune_20261025/runtime_demo.py) |
| V4贡献选组、R1、W4恢复 | [fit.py](experiments/v4_recovery_20261025/fit.py) |
| 清晰教师／较难学生与反例回放 | [M542 fit.py](experiments/demo_counterexample_20261026/fit.py) |
| 早期联合蒸馏/LoRA研究 | [train_joint02.py](experiments/augmented_student_20261025/train_joint02.py)，与已部署方法分开 |

详见[剪枝与蒸馏说明](docs/PRUNING_DISTILLATION.md)、[当前精确结构](docs/CURRENT_RECIPE.json)、[操作约束](docs/OPERATIONS.md)。早期文件名中的旧版本是依赖追溯，不代表当前同时执行所有旧方案。

## 无板卡校验

```text
cd current_demo
<你的Python解释器> -B tools/verify_sources.py
```

该命令仅核查原源码SHA、字节数和Python语法，不导入模型、不连接板卡、不发起推理。原代码含Windows/WSL/板端环境固定路径、冻结清单、旧boot身份和不可覆盖输出；它是可审阅的当前源码快照，**并非仅克隆即可执行的一键板端安装包**。

训练需原模型、mixed-bit checkpoint、数据/特征缓存及CUDA环境；A53运行需对应bit/hwh、权重分片、PYNQ/XRT环境和逐级门禁。二进制资产、视频、采样图、人像、SQLite、串口日志、worker token均不上传。外部依赖路径和SHA见[DEPENDENCIES.json](docs/DEPENDENCIES.json)。原包清单包含未随Git上传的资产，缺资产时必须停止，不能删除检查绕过。

## 保存的结果及边界

- M543：六固定采样帧及两条热重复实板通过；热态两次27.633822/27.584494秒，均值27.609158秒；首次请求49.188272秒单列，不含模型加载。它不是与旧版的同场配对提速证据。
- M544：2026-10-28实际视频7采样图的新请求返回Yes、TTFT28.007205秒，网页红警可见；不复用旧结果，不按文件名/播放时间报警。依据各自runs目录原RESULT；模型首次加载、预热和UART准备画面在播放前完成，不计作TTFT。
- 当前07会话配置6小时接受窗口、最多12新任务；CPU/A53过期边界检查通过，未做6小时持续运行验证。
- 固定视频与同源增强用于演示适配，不是独立泛化准确率；旧漏判/误报及被拒方案不改写为成功。

第三方基座、Transformers及FPGA工具的源码/授权范围沿用仓库既有LICENSE_SCOPE、THIRD_PARTY_NOTICES和原文件标注；本快照不重新声明第三方代码或模型权重的许可证。
