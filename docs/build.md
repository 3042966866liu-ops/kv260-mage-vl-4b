# 硬件源码构建范围

稳定源码见 [T32 HLS](../hls/mage_prefill_m89x_runtime/)，历史主机运行时契约位于 `deployment/mage_vl4b/m175_m120_fixed_text_candidate/`。HLS 目录包含 C++ 头文件、CSim/CoSim 测试程序及 Tcl，包括 `run_m134_export_m120_m89x2.tcl`。双引号 include 的递归依赖通过 `mage_prefill_m89s/m89d/m89o/m89n/m89h/m89e` 及相关同级模块补齐；本快照运行 `python3 scripts/audit_hls_includes.py` 得到 `missing=0`。这不等于编译检查。HLS 的 `export_design` 生成的是 IP，**不是** KV260 bitstream。

HLS Tcl 目标器件为 `xck26-sfvc784-2LV-c`，严格测试采用 4.8 ns 周期与 1.3 ns 不确定度。历史实板执行的完整系统产物为 Build `0x4D395832`、内核 `mage_m120_m89x2_0`、文件 `m120_m89x2_t32.bit/.hwh`。M300 绑定记录给出布线后资源：LUT 39,613/117,120 (33.82%)、FF 46,882/234,240 (20.01%)、BRAM 70/144 (48.61%)、URAM 16/64 (25.00%)、DSP 1,070/1,248 (85.74%)，WNS +0.147 ns、WHS +0.010 ns。这些是**历史源工程测量值**，不是从本快照重新构建所得。复制的 M134 导出 Tcl 硬编码了旧 Windows 工作区与 `m132_m120_fifo_backpressure_hls` 工程；保留它用于追溯，不能把它当作干净发布目录的构建命令。

本发布尚未验证完整、可迁移的 Vivado 系统构建：BD/IP 连线、PS/DDR/DMA/AXI 地址映射、时钟/XDC、板卡型号、完整实现及打包脚本都尚未证明能从干净克隆目录完成。上级工作区中的部分工程属于其他 Qwen 实验，不能直接作为 Mage-VL T32 的设计源。`SOURCE_BUILD_VERIFIED=NOT_RUN`。此次发布未运行 CSim、CoSim、IP 导出、综合、布线或 overlay 打包；历史 CSim/RTL 通过不能证明发布快照可完整重建。

OP01 Decode-one 源码见[实验 HLS](../hls/mage_decode_op01_one/)。其 FIFO 容量长测仍为已中止，不应默认替换稳定 T32 bitstream。
