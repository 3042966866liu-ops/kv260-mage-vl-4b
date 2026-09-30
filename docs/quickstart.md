# 快速开始

## 无需开发板：离线复算

在仓库根目录使用 Python 3.10+：

```sh
python3 scripts/preflight.py --help
python3 scripts/preflight.py --dry-run --config configs/deployment.example.json
python3 scripts/m321_reproduce_bact_v2_evidence.py --only all
python3 scripts/check_release.py
```

预演会报告缺失的模型或硬件资产，不导入 PYNQ、不读取权重、不监听端口，也不访问开发板。M321 命令复核固定选择器身份、27 条既有板端记录和历史 12 段视频预测，**不会重新推理**。缺少资产时，`--check` 以非零退出码结束。在原开发机器的 Windows 上，请使用上级项目记录的已安装 Python 绝对路径，不要假定 `PATH` 中存在 `python`。

## KV260 预构建安装

前提：受支持的 KV260 Ubuntu 镜像、匹配的 PYNQ/XRT、精确模型与 bitstream 资产，以及独立保留的稳定回滚目录。预构建 TAR 包含[资产清单](../manifests/external_assets.json)中哈希锁定的文件，Git 源码目录不包含这些资产。[GitHub Releases](https://github.com/3042966866liu-ops/kv260-mage-vl-4b/releases)已提供八个分片（前七个各 500 MB）及匹配的八分片 `RELEASE_PARTS.json`。下载全部分片与清单后，按[预构建资产说明](prebuilt_release.md)在主机校验并重组 TAR。不要混用旧 2 GB 分片与新 500 MB 分片，也不要用同名上游 checkpoint 替代。公开分片的完整下载、重组和哈希核验尚无记录。

板端解压文件需要约 3.9 GB 空间，另需隔离 Python 运行时空间；wheel 安装约需 200 MB 临时内存。从身份确认的传输对端向新的安装目录流式解压，避免在空间紧张的 microSD 上同时保存完整 TAR 与解压副本。不得删除稳定 M254 安装来腾出空间。

**如需运行固定视频 v3 伴随包，基础 v7 安装目录必须是 `/home/ubuntu/tellme_release_install_20260926`。** 伴随包的 `run_fixed_video.py` 第 22 行将该路径固定为 `RELEASE`；它不是可自由替换的示例路径。伴随包目录及运行命令见[固定视频复现](fixed_video_reproduction.md)。保留稳定部署和回滚，不覆盖它们。解压目录中的 `INSTALL_BOARD_RESULT.json` 是一次安装记录，不等于模型结果 PASS。

在已解压的基础安装目录中执行：

```sh
/usr/local/share/pynq-venv/bin/python3 scripts/verify_prebuilt_package.py
/usr/local/share/pynq-venv/bin/python3 scripts/preflight.py --check --config configs/deployment.example.json
sudo -n true
sudo -n /usr/local/share/pynq-venv/bin/python3 scripts/install_runtime_wheels.py
sudo -n env TELLME_RELEASE_BOARD_LAUNCH_UNVERIFIED=ACKNOWLEDGED bash scripts/run_demo.sh
```

wheel 安装器校验包内 M189 ARM64 wheel 清单、torchvision wheel 和历史 M193 Pillow wheel，安装到本发布的 `runtime_site`，检查 Torch 2.12.1+cpu / torchvision 0.27.1+cpu、Pillow 12.1.0 的 `Image.Resampling` 及原生 NMS 算子，然后写入 `RUNTIME_SITE_READY.json`。它不使用历史稳定运行时目录；失败时不要启动服务。

`ACKNOWLEDGED` 表示操作者明确选择启动，**不是安装验证通过的证据**。实际启动要求 root，并在同一终端通过 `sudo -n true`。`run_demo.sh` 选择已观察到的 PYNQ Python 与 XRT 环境，在服务启动前执行固定的 root/XRT/PYNQ/包清单预检。历史 `run_m254_board_gate.sh` 依赖前置部署状态，是升级检查脚本，不是首次安装入口。端口被占用时，启动器退出，不会杀死其他服务。

模型初始化可能耗时数分钟；`live/start` 在返回 HTTP 202 前同步加载快速检测器，因此短客户端超时不能可靠判断就绪。发起有界启动请求后，轮询实时状态端点，并区分 `runtime-loading`、`ready` 与 `worker-failed`。完整部署验证遵循 Build-ID → descriptor → chain → layer → 固定样例 → Web 的顺序。v7 本地首次安装记录覆盖固定文本 E2E 与无帧 Web 运行时就绪；独立 M328 伴随包后来通过的是直接固定视频路径，**不是**自动报警 Web 路由。

四帧固定 Mage-VL 测试使用[固定视频复现](fixed_video_reproduction.md)中的独立哈希锁定伴随包和直接 4B 入口。没有触发报警的 M254 快通道结果不能算作 4B 视频推理。
