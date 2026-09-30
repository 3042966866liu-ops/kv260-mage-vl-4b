# 源码入口与依赖关系

大部分复制文件保留原工作区相对路径，且逐字节一致。`manifests/release_files.json` 记录逐文件来源与 SHA-256。以下按目录说明作用，未修改原部署文件。

| 发布路径 | 原始路径 | 作用／状态 |
| --- | --- | --- |
| `deployment/mage_vl4b/m254_dual_path_web_candidate/` | 相同 | 稳定 Web 控制器／静态文件 |
| `deployment/mage_vl4b/m243_web_prefill_board_candidate/`, `m242_m241_fixed_text_board_candidate/`, `m238_input_prefetch_board_candidate/`, `m241_grouped_gqa_board_candidate/`, `m231_parse_reuse_board_candidate/` | 相同 | 稳定 Prefill 模块导入优先级 |
| `deployment/mage_vl4b/m181_m120_video_board_candidate/`, `m175_m120_fixed_text_candidate/`, `m246_knife_binary_board_candidate/`, `m249_ssdlite_board_candidate/` | 相同 | 模型适配器／板端契约／快通道；大型二进制另行提供 |
| `tmp/m218_dual_source/`, `tmp/m223_realtime/`, `tmp/m227_runtime_base/` | 相同 | **仍在使用的历史运行时依赖**，有意纳入版本管理而非忽略 |
| `hls/mage_prefill_m89x_runtime/` | 相同 | 稳定 T32 HLS 源码与测试 Tcl |
| `hls/mage_prefill_m89s_scaleaware/`, `mage_prefill_m89d_t32_microtile/`, `mage_prefill_m89o_shared15/`, `mage_prefill_m89n_t32_w2w4/`, `mage_prefill_m89h_t32_chunkedpacked/`, `mage_prefill_m89e_t32_packedaccum/` 及其他同级 HLS 模块 | 相同 | 双引号 include 递归依赖齐全，仅限源码级检查 |
| `bact/`, `deployment/mage_vl4b/m277_m276_fixed_window_board_candidate/`, `scripts/m321_reproduce_bact_v2_evidence.py` | 相同 | 离线 BACT 与固定视频研究路径，不是 Web 默认入口 |
| `deployment/mage_vl4b/optimization_v1/candidates/OP01-decode-one-ab-01/`, `hls/mage_decode_op01_one/`, `scripts/m325*` | 相同 | 未进入稳定版的实验路径 |
| `model_tools/m125...`, `m126...`, `m148...`, `m153...` | 上级项目对应的 `scripts/` 文件 | 逐字节复制，覆盖部分转换过程 |
| `scripts/preflight.py`, `scripts/run_demo.sh`, `configs/`, 发布文档／清单 | 无 | 发布版专用启动器与说明，不是历史实板证据 |

沿 M321 固定 JSON 的引用关系纳入了 `scripts/m313_gate_bact_v2_selector.py`、M297、M306、标签、预测与配对结果；BACT 已能从此目录复算通过。M254 Python 静态导入遍历按记录的优先级及外部包允许列表解析出 31 个本地模块，无未解析本地名称。稳定服务使用 PYTHONPATH／模块覆盖与延迟 `board_runtime` 导入；静态依赖齐全和路径存在不能证明首次安装时实际导入必然完整。历史 `PACKAGE_MANIFEST.json` 列出的二进制载荷有意不进入 Git，动态文件路径和板端环境变量仍是安装约束。

原 M254 控制器以前置路径 `/home/ubuntu/tellme_m120_m89x2_20260901` 为回退值。新启动器提供以发布根目录解析的 `M254_M243_RESULT`、`M254_M253_RESULT`、`M254_M249_RESULT`、`M254_M249_CANDIDATE` 和 `M200_STATIC_ROOT`，因此该入口不应使用旧回退路径。原 M223 运行时从启动器接收 `--candidate`、`--text-candidate`、`--weights-root`、`--board-gate`、`--host` 和 `--port`。没有放宽或重写原检查。路径扫描发现 27 个复制的历史源码／证据文件含 `/home/ubuntu` 类板端路径；新发布入口／配置没有个人工作区绝对路径。这些历史检查脚本不是首次安装命令。包含临时公网隧道地址的综合板端摘要未复制入发布目录，具体 M325/M300/M314 证据仍保留，原文件没有删除。
