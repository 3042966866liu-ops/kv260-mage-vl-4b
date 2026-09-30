# 运行环境

| 用途 | 已有记录 | 未验证或未提供的部分 |
| --- | --- | --- |
| 开发主机 | Windows PowerShell；历史 WSL 发行版明确为 `Ubuntu-24.04`；包含 Vitis/Vivado 源码脚本 | 未从此快照完成干净构建；首次发布时实际安装的工具版本未完整核实 |
| 离线 BACT 证据复算 | Python 标准库与复制的 `bact/` 模块；M321 已在发布目录复算 | GPU 软件参考环境独立，未在此重建 |
| KV260 板端 | 已观察到 Ubuntu 22.04.4 LTS/AArch64、Python 3.10、XRT 2.13.0 与 PYNQ 环境；特定稳定启动配置使用 800 MiB CMA | 所有者板端的 v7 独立目录安装及启动已验证；新板干净系统镜像安装尚未验证 |

板端检查要求 root、`XILINX_XRT=/usr`、`TMPDIR=/dev/shm`、`/usr/local/share/pynq-venv/bin/xclbinutil` 位于 `PATH` 首位、`xclProbe()==1`、恰好一个 PYNQ 设备，以及精确的包哈希。该历史开发板不得使用 `/usr/bin/xclbinutil`。控制使用串口 COM3；以太网仅用于有界、哈希核验的临时传输。本发布不会配置网络、boot 或 CMA。不要把 800 MiB CMA 当作 KV260 通用默认值。

软件依赖见[依赖说明](../requirements/README.md)。仓库不负责安装板端系统包，也不将猜测的通用 `pip install -r` 命令作为已验证的板端配置流程。
