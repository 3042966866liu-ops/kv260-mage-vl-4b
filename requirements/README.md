# 依赖范围与版本说明

- `offline-evidence.txt` 中的 M321 与发布检查仅使用 Python 3 标准库，无需安装额外 Python 包。
- 对历史 KV260 运行时的静态遍历发现外部导入 `PIL`、`cv2`、`numpy`、`packaging`、`pynq`、`requests`、`safetensors`、`scipy`、`tokenizers`、`torch`、`torchvision`、`tqdm`、`transformers` 和 `typing_extensions`，另外需要 XRT。已测镜像记录 CPU Torch `2.12.1+cpu`、torchvision `0.27.1+cpu`、NumPy `1.26.4` 和 XRT `2.13.0`；本依赖盘点未核验其余导入项版本。这是**已观察到的环境**，不是可移植依赖锁文件，也不保证每个 wheel 都有独立公开下载地址。
- HLS/Vivado 是独立的构建主机工具，不能通过 `pip` 依赖安装。

本快照尚未完整记录精确 aarch64 wheel 来源、transformers/tokenizers 上游版本和系统镜像配置流程，因此不提供猜测的通用安装命令。[发布状态](../RELEASE_READINESS.md)记录了所有者 KV260 上 v7 独立目录安装已通过；新板干净系统安装仍未验证。使用已公开预构建包时，按[快速开始](../docs/quickstart.md)安装其哈希锁定的隔离依赖。
