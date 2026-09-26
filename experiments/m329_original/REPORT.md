# M329：KV260 同输入 CPU 参考与稳定 PL 事务对照

日期：2026-09-26。状态：**单链实现级 A/B 通过；不是整模型加速结论**。

本次复用冻结 M128 真实记录 fixture（SHA-256 `f384f45eea4bc14110a7add49dd0944f0a025403aecc3360369ec999e28257d9`），稳定 FPGA Build `0x4D395832`，不生成新 bitstream、不修改稳定目录/boot/DTB/CMA/分区。COM3 控制与结果收集；同一终端在加载 overlay 前完成 root/XRT/PYNQ/包哈希预检。CPU 和 PL 都在同一 KV260 上运行。

CPU 数值入口覆盖 7 个 W2/W4 case，各重复 3 次，完整 FP16 输出均与冻结参考逐字节相同。PL 对其中 W2、W4 各一个双 descriptor case 重复 3 次，全部符合预先确定的 FP16 次正规数清零（FTZ）完整输出契约，DMA 无错误、返回 Build-ID 正确。两侧的输入 packet 与四个权重分片 SHA-256 逐项相同。

| 双 descriptor case | CPU Python/NumPy 解包＋算术中位数 | 其中 CPU 整数点积及累加 | PL 权重 staging＋同步 | PL DMA 启动至完成等待 | PL 事务总中位数 |
|---|---:|---:|---:|---:|---:|
| W2，layer0/family4 | 449.348 ms | 65.001 ms | 0.515 ms | 1.113 ms | 2.074 ms |
| W4，layer0/family5 | 497.539 ms | 65.555 ms | 0.559 ms | 1.381 ms | 2.420 ms |

PL 事务总时间包含权重/输入 staging、同步、寄存器设置、DMA 启动与等待、输出同步/复制；不含一次性 overlay 加载（`2188.801 ms`）和缓冲区分配。CPU 时间包含本实现的 Python 解包与 NumPy 分组整数点积、累加、打包；不含 fixture 文件读取和冻结参考生成。CPU/PL 是先后测量，未交错顺序，也未控制温度/频率变化。当前 CPU 参考**不是优化过的 A53 NEON/C++ 实现**，不能把两列总时间之比宣称为硬件相对最佳 CPU 的加速，更不能外推为 4B 视频首 Token 或吞吐提升。M328 的 `230.721 s` 视频首 Token 基线未改变。

证据：机器结果 `RESULT.json`，原始串口日志 `tmp/m329/cpu_board_01.log`、`tmp/m329/pl_board_01.log`、`tmp/m329/result_hashes_01.log`；板端 9 个结果文件的 SHA-256 已收入机器结果。PL 预检 package manifest SHA-256 `7600ba1af87680fe1294ae6dc88f8e0968f23b2e38ca48dbfd316e351ea76e3e`。本轮无新核晋级；拒绝把这个脚本实现级差异包装成整模型优势。

下一步：用同量化的优化 A53 实现重测代表性 Linear，采用交错顺序与冷/热缓存控制；然后才考虑完整固定视频 PS-only 与 PS–PL 对照。若 PS-only 全模型受板端内存限制无法运行，应记录 `NOT_RUN`，不虚构结果。
