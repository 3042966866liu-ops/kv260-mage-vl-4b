# M330：优化 A53 原生 CPU 基线，暂不宣称 CPU/PL 加速比

日期：2026-09-26。状态：**CPU 数值及局部测速 PASS；C 阶段公平 CPU/PL 成对对照尚未完成**。

本轮仅补 M329 未覆盖的优化 CPU 路径，没有重跑 M329 已通过的七个 Python/NumPy CPU case 或两个稳定 PL case。新 C++ 实现从冻结 M128 原始打包记录解码 W2/W4，整数点积、FP32 按序累加，输出原始 FP16 字节；另外测量预解包后算术路径。完整输出对原始 FP16 参考逐字节相同；PL 原有契约是 FP16-FTZ，不能混为同一个哈希。

KV260 Cortex-A53，单线程绑核 1，`g++ 11.4.0`，`-O3 -std=c++17 -ffp-contract=off -fno-fast-math -march=armv8-a+simd`。每个模式/形状独立 10 次，文件读取、编译、结果验证与输出写盘不在计算计时内。首次与后续原始数值均在机器结果保留，以下为十次中位数：

| M128 双 descriptor | 原始打包输入到完整输出 | 预解包一次性时间 | 预解包额外空间 | 预解包后算术到输出 |
|---|---:|---:|---:|---:|
| W2，layer0/family4，40 groups | 5.790 ms | 1.524 ms | 174,080 B | 4.498 ms |
| W4，layer0/family5，40 groups | 5.787 ms | 1.514 ms | 174,080 B | 4.496 ms |

预解包路径反复运行可省约 1.29 ms/次，但若只运行一次，预处理加算术约 6.02 ms，反而略慢于直接打包路径的约 5.79 ms。`174,080 B` 是这两个小 case 的解码表，不是全模型内存估算；原始冻结记录相应为 `87,040 B`，约 2 倍。不能据此建议全模型权重常驻预解包：需要单独核算实际层权重和板端可用内存。

M329 同板稳定 PL 历史双 descriptor 事务中位数为 W2 `2.074 ms`、W4 `2.420 ms`；该事务包含 staging、同步、DMA、输出复制，不含 overlay 加载和缓冲分配。由于本轮没有与新 CPU **交错/平衡**重复 PL 事务，且 CPU 时间不含同等输入 staging，**不计算或宣称 CPU/PL 速度比**。M328 视频首 Token `230.721 s` 没有改变；本轮没有视频端到端收益。

证据：`RESULT.json`，COM3 原始 `tmp/m330/board_native_cpu_01.log`、`tmp/m330/board_native_logs_01.log`、`tmp/m330/board_result_hashes_01.log`，板端独立目录 `/home/ubuntu/tellme_m330_native_cpu_20260926/` 的四份结果与日志 SHA-256 在机器结果中。源文件和 runner 在 `scripts/optimization/m330_*`。结果没有覆盖稳定目录，没有加载 overlay、停止服务或改动 boot/DTB/CMA/分区。板端原生二进制 SHA-256 `97730113c0c34c99c9b61aaf5ad70ac57c00a6749c89752ea2b510c338f36354`。

Go/No-Go：M330 CPU 子门禁 **Go**；完整 C 阶段 **No-Go/NOT_RUN**，欠同条件 CPU/PL 至少 10 对有效交错样本和公平的 staging 边界。下一步只补该成对对照，不重复 M329 数值门禁；再判断是否能声称稳定 PL 在代表性 W2/W4 形状上仍有优势。
