# 同模型 CPU-only 与 PS–PL 整体对照：可行性审计

状态：`BLOCKED`（尚无同量化整模型 CPU 后端），不是整模型 CPU/PL 性能实验。此审计只读复用已有证据，没有新的板端事务。

## 可复用的计算与缺失的部分

稳定路径 `M241VideoLanguageModel` 的视觉、Norm、RoPE、Attention、激活和残差在 PS 执行；语言各层的 q/kv 或 qkv、attention_out、gate_up、mlp_down，以及 LM Head 通过 runtime 的 `language_family_many`/`lm_head` 委托给稳定 PL。M330 原生 C++ CPU 实现只覆盖冻结 M128 的两个 W2/W4 双 descriptor 代表性 case，不是上述全部 family、LM Head、完整布局与所有输入形状的可替换 runtime。M329 七个 Python/NumPy case 和 M331 两个成对 case 的完整输出数值证据可复用，但不能自动扩展为 36 层加 LM Head 的同量化 CPU-only 模型。

因此，当前无法在不新增后端开发和整模型数值门禁的情况下做公平的固定视频 CPU-only/PS–PL 同会话对照。把 M331 单链 `2.3–2.6×` 写成整模型加速比是明确拒绝项。

## 内存与存储边界

发布资产清单 `manifests/external_assets.json` 记录：语言四路 `1,828,839,424 B`，LM Head 四路 `206,632,960 B`，FP16 embedding `777,912,320 B`，视觉 BF16 原资产 `660,770,912 B`，视觉 W4 布局四路 `174,915,584 B`。五项磁盘身份合计 `3,649,071,200 B`（`3.398 GiB`），其中视觉 BF16 与 W4 布局可能是替代表示，不能简单称为 CPU 运行时同时驻留需求。

历史 M270 只读板端状态显示物理 RAM `4,005,128 KiB`、当时 `MemAvailable=2,858,624 KiB`、无 swap、CMA 总量 `819,200 KiB`；这不是当前瞬时可用内存。将全部五项在 RAM 再复制一份没有可信余量；但顺序 mmap/流式读取可能可行，不能因此断言 CPU-only 在 KV260 上不可能。M328 固定视频 PS 视觉进程峰值约 `1,029,624 KiB`，不同会话和资产驻留不能直接相加成真实峰值。

当前缺少：全 family 与 LM Head 的同量化 CPU dispatch、W2/W4/分组/缩放/FTZ 完整合同、可控的流式权重生命周期、整模型完整 logits/KV 对照、固定视频 CPU-only 计时及板端当时内存/磁盘状态。M330 的单链速度不能可靠外推总运行时间；若将来开发 CPU 后端，应先逐 family 数值门禁，再最小层、固定文本、固定视频；同输入、同量化、同提示与同一初始化/计时边界分别记录。

决定：不为了补表格而运行一个数学或量化不同的 CPU 模型。保留 M331 同量化代表性单链公平对照和未来 D 阶段的 PS–PL 前后视频对照；整模型 CPU/PL 加速比维持 `NOT_RUN`。
