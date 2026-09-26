# 同量化 A53 CPU／稳定 FPGA 单链对照

状态：**M331 代表性单链成对实验 PASS**。本页不声称 4B 整模型或视频端到端加速。稳定部署仍为 Build `0x4D395832`，未替换内核。

此前的 [M329 原始门禁](../experiments/m329_original/REPORT.md)证明冻结 M128 fixture 上 7 个 W2/W4 CPU Python/NumPy case 与两个 PL case 的数值契约，但 Python 解包不是优化 CPU 基线。新增 [M330 原生 A53 结果](../experiments/m330_cpu/RESULT.json)只补 W2/W4 双 descriptor 两个形状：单线程绑核 1、`g++ 11.4.0 -O3 -ffp-contract=off -fno-fast-math -march=armv8-a+simd`，原始打包路径与预解包路径各 10 次，完整原始 FP16 输出精确。

M331 在同一 KV260 会话交错运行 CPU→PL、PL→CPU，各形状 10 对；预检通过后使用未变的稳定 bitstream。CPU 从内存原始打包 fixture 计算到完整输出；PL 从内存 packet/权重经 CMA staging、同步、DMA、输出复制到完整输出。CPU 不计进程启动、fixture 文件读取/解析和文件写盘，PL 不计 overlay 加载和一次性 buffer 分配。两者实现 API 不完全相同，比较的是同量化输入的单链实现级成本。PL 等待不等于纯核计算。

| 冻结形状 | 优化 A53 CPU 中位数 | 稳定 PL 事务中位数 | 逐对 CPU/PL 中位数 |
|---|---:|---:|---:|
| W2，双 descriptor，40 groups | 5.891 ms | 2.244 ms | 2.625× |
| W4，双 descriptor，40 groups | 5.871 ms | 2.525 ms | 2.328× |

20 对原始顺序、分段、输出哈希及 DMA 快照见 [M331 板端原始结果](../experiments/m331_paired/BOARD_RESULT.json)，复算统计见 [摘要](../experiments/m331_paired/SUMMARY.json)；[中文报告](../experiments/m331_paired/REPORT.md)列出范围、预解包成本和限制。CPU 全输出按原始 FP16 精确；PL 按预先固定的 FP16-FTZ 契约精确；每次 PL 返回 Build-ID 正确、DMA idle 且无错误。

无需板卡即可从已公布的逐对结果复算统计：

```bash
python3 scripts/optimization/m331_summarize_paired.py \
  --board-result experiments/m331_paired/BOARD_RESULT.json \
  --summary /tmp/m331-summary-recomputed.json
```

运行全新实板实验仍需未公开分发的匹配 fixture、稳定权重和 bitstream，并须遵守板端 root/XRT/PYNQ/包哈希预检及独占 FPGA 条件；仓库中的 `scripts/optimization/m330_*`、`m331_*` 是这次的精确实验源码，不是绕过安装门禁的一键脚本。原始 COM3 日志和备份保存在维护者工作区，未随 Git 提交；板端原始机器 JSON 的 SHA-256 为 `3e1409ca5ac1999d977613e4d3cbe01812f85e1c12cf10f517bff324aca2bb63`。

M328 的固定视频首 Token 仍为约 `230.721 s`。单链 2.x 倍不能线性外推到整个模型；下一步须在不改模型、量化与输入的固定视频上验证端到端收益。
