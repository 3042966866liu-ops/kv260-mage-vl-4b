param(
    [string]$OutputPath = "deliverables/TeLLMe_Qwen3B_M20_code.md"
)

$ErrorActionPreference = "Stop"
$workspace = Split-Path -Parent $PSScriptRoot
$release = "releases/M20-resident-directddr-20260828"

$releaseSources = Get-ChildItem -File -Recurse (Join-Path $workspace $release) |
    Where-Object {
        $_.Extension -in ".py", ".sh", ".ps1", ".service" -or $_.Name -eq "Makefile"
    } |
    ForEach-Object { $_.FullName.Substring($workspace.Length + 1).Replace("\", "/") }

$hardwareSources = @(
    "deployment/qwen25_3b_directddr_chain/boot_candidate_reserved1664.cmd",
    "deployment/qwen25_3b_directddr_chain/user-override-reserved1664.overlay.dts",
    "deployment/qwen25_3b_directddr_chain/reserved1664_mmap/Makefile",
    "deployment/qwen25_3b_directddr_chain/reserved1664_mmap/tellme_reserved1664.c",
    "deployment/qwen25_3b_no_final_forward/runtime/native/Makefile",
    "deployment/qwen25_3b_no_final_forward/runtime/native/prefill_native.cpp",
    "hls/prefill_decode_shared_l40_packetdf/qwen25_prefill_w4a8.hpp",
    "hls/prefill_decode_shared_l40_packetdf/qwen25_prefill_w4a8.cpp",
    "hls/prefill_decode_shared_l40_packetdf/tb_qwen25_prefill_w4a8_single.cpp",
    "hls/prefill_decode_shared_l40_packetdf/tb_qwen25_prefill_w4a8.cpp",
    "hls/prefill_decode_shared_l40_packetdf/run_csim_single.tcl",
    "hls/prefill_decode_shared_l40_packetdf/run_csim_synth.tcl",
    "hls/prefill_decode_shared_l40_packetdf/run_csim.tcl",
    "hls/prefill_decode_shared_l40_packetdf/run_decode_directddr_chain_csim.tcl",
    "hls/prefill_decode_shared_l40_packetdf/run_decode_directddr_chain_synth.tcl",
    "hls/prefill_decode_shared_l40_packetdf/run_decode_directddr_chain_export.tcl",
    "hls/prefill_decode_shared_l40_packetdf/run_export.tcl",
    "hls/prefill_decode_shared_l40_packetdf/run_synth_only.tcl",
    "vivado/decode_directddr_chain_highddr/create_candidate_project.tcl",
    "vivado/decode_directddr_chain_highddr/run_synthesis.tcl",
    "vivado/decode_directddr_chain_highddr/run_implementation.tcl",
    "vivado/prefill_l40_only/create_candidate_project.tcl",
    "vivado/prefill_l40_only/inspect_axis_switch.tcl",
    "vivado/prefill_l40_only/inspect_base.tcl",
    "vivado/prefill_l40_only/inspect_dma.tcl",
    "vivado/prefill_l40_only/run_synthesis.tcl",
    "vivado/prefill_l40_only/run_implementation.tcl"
)

$descriptions = @{
    "$release/verify_release.ps1" = "校验冻结 M20 release 中全部载荷的 SHA-256 与锁文件，只有零缺失、零漂移时才输出完整性通过标志。"
    "$release/control/arm_reserved1664_m20_authorized_cycle.sh" = "板端授权入口：核对稳定启动状态和所有控制脚本哈希，安装跨启动服务与候选启动文件，并安排一次受控重启。"
    "$release/control/install_reserved1664_m20_boot.sh" = "安装并校验 M20 的 reserved1664 候选 boot/DTB，同时保留稳定启动备份；支持只检查不写入模式。"
    "$release/control/m20_arm_authorized_cycle_uart.ps1" = "Windows 串口侧 M20 启动器：独占并核对指定 FTDI/COM 设备，通过串口登录后触发哈希锁定的授权周期。"
    "$release/control/prepare_reserved1664_m20_full_gate.sh" = "在稳定系统上准备 M20 完整门禁目录和依赖，执行文件存在性、权限、哈希及运行环境预检。"
    "$release/control/rollback_reserved1664_boot.sh" = "将启动文件恢复到已锁定的稳定版本，删除候选覆盖 DTB，并验证回滚后的启动文件身份。"
    "$release/control/run_reserved1664_m20_authorized_cleanup.sh" = "候选周期后的稳定系统清理器：收集恢复证据，移除临时服务/运行器并确认 FPGA、CMA 与启动状态。"
    "$release/control/run_reserved1664_m20_authorized_cycle.sh" = "跨启动周期编排器：在候选系统执行 M20 全门禁，持久化结果，回滚稳定启动并安排恢复重启。"
    "$release/control/run_reserved1664_m20_full_gate.sh" = "M20 板端总门禁脚本：串联制品、启动、内存、模型身份、真实权重 Prefill、Decode、端到端性能和清理检查。"
    "$release/control/tellme-reserved1664-m20-cleanup.service" = "systemd 稳定恢复清理单元，确保候选周期结束后的证据采集和临时文件清理由系统自动执行。"
    "$release/control/tellme-reserved1664-m20-cycle.service" = "systemd 候选周期单元，在 reserved1664 候选 Linux 启动后自动运行一次 M20 授权门禁。"
    "$release/runtime/board_model_identity_preflight.py" = "读取板端模型文件、索引和配置的尺寸/哈希/结构，阻止错误模型或不完整权重进入 FPGA 门禁。"
    "$release/runtime/chain_common.py" = "Direct-DDR 链式运行时的公共常量、量化元数据解析、张量布局和数值辅助函数。"
    "$release/runtime/chain_hardware_smoke.py" = "对 Decode Direct-DDR 链进行最小真实硬件冒烟测试，核对寄存器、DMA、Build ID、调用计数和输出。"
    "$release/runtime/chain_layer_benchmark.py" = "逐层执行并计时 Qwen2.5 解码线性算子链，输出硬件耗时、误差和调用统计。"
    "$release/runtime/chain_lm_head_benchmark.py" = "执行量化 LM Head 的分块 FPGA 计算与候选 token 精确复核，并记录端到端输出层性能。"
    "$release/runtime/dtcma_boot_preflight.py" = "检查设备树 CMA 候选启动下的内存布局、保留区和 FPGA 运行条件；作为历史兼容预检随冻结运行时保留。"
    "$release/runtime/highddr_boot_preflight.py" = "检查高地址 DDR 候选启动的物理内存边界、保留区和可用状态，防止映射越界。"
    "$release/runtime/highddr_prefill_smoke.py" = "在高地址 DDR 映射上执行 Prefill 硬件冒烟验证，核对真实权重、DMA 地址和输出。"
    "$release/runtime/hostbo_boot_preflight.py" = "检查 Host-BO 候选的启动参数、内存池和设备节点；作为 M20 前序内存方案的兼容依赖保留。"
    "$release/runtime/hostbo_pool.py" = "封装 Host Buffer Object 的申请、映射、物理地址查询、同步和释放生命周期。"
    "$release/runtime/m20_reserved1664_artifact_preflight.py" = "M20 专用的 23 项可执行制品门禁，验证候选 boot、bitstream、模块、运行时和脚本的精确哈希。"
    "$release/runtime/m20_resident_full_e2e_gate_impl.py" = "M20 端到端核心实现：复用常驻 Direct-DDR 权重，执行逐 token 因果 Prefill、Decode、采样、性能统计和双门禁判定。"
    "$release/runtime/m20_resident_sequential_full_e2e_gate.py" = "M20 端到端命令入口，加载专用实现并固定 resident-directddr-sequential-v1 执行模式。"
    "$release/runtime/offline_ddr_mapping_smoke.py" = "验证离线高地址 DDR 设备的 mmap、读写一致性、边界保护和清理行为。"
    "$release/runtime/offline_ddr_pool.py" = "封装离线高地址 DDR 内存池的分配、对齐、映射和生命周期管理。"
    "$release/runtime/qwen3b_prompt_identity_probe.py" = "固定 Qwen2.5-3B 提示词、tokenizer 和期望 token ID，生成 CPU/FPGA 可比的输入身份记录。"
    "$release/runtime/reserved_ddr_mapping_smoke.py" = "验证 reserved1664 驱动暴露的保留 DDR 映射是否可读写、地址正确且越界访问被拒绝。"
    "$release/runtime/reserved_ddr_pool.py" = "M20 使用的 reserved high-DDR 内存池封装，负责偏移分配、页对齐、mmap、物理地址和释放。"
    "$release/runtime/reserved1664_artifact_preflight.py" = "reserved1664 通用制品预检，检查部署文件、权限、设备节点和哈希身份。"
    "$release/runtime/reserved1664_boot_preflight.py" = "核对 reserved1664 候选内核命令行、设备树保留内存、CMA、驱动和物理地址窗口。"
    "$release/runtime/resident_chain_runtime.py" = "Qwen2.5-3B PS-PL 协同推理主运行时，管理常驻量化权重、Prefill/Decode 加速器、KV Cache、LM Head 和生成循环。"
    "$release/runtime/resident_full_e2e_gate.py" = "常驻权重方案的通用端到端门禁，执行固定预热和多轮正确性/性能测试，并生成结构化证据。"
    "$release/runtime/resident_memory_preflight.py" = "在载入大模型前核对 MemAvailable、CMA、映射私有性、常驻区容量和安全余量。"
    "$release/runtime/resident_sequential_prefill_runtime.py" = "M20 新增的逐 token 串行 Prefill 适配层：从常驻 Direct-DDR 权重构建严格因果 KV Cache，避免逐请求重读 microSD。"
    "$release/runtime/resident_store_lifecycle_smoke.py" = "验证常驻权重存储的创建、复用、哈希、地址稳定性和显式释放，防止残留或重复加载。"
    "$release/stable_runtime/qwen_fpga_runtime.py" = "冻结的 Qwen2.5-3B 完整 FPGA 推理运行时，包含 tokenizer/embedding、RoPE、RMSNorm、量化线性层、KV Cache、LM Head 与生成逻辑。"
    "deployment/qwen25_3b_directddr_chain/boot_candidate_reserved1664.cmd" = "生成 reserved1664 候选启动脚本，设置内核、设备树、启动参数和保留内存布局；冻结 release 保存的是其编译后启动镜像。"
    "deployment/qwen25_3b_directddr_chain/user-override-reserved1664.overlay.dts" = "定义 M20 高地址 reserved-memory 与驱动可见区域的设备树覆盖源，避免被普通 Linux/CMA 分配器占用。"
    "deployment/qwen25_3b_directddr_chain/reserved1664_mmap/Makefile" = "交叉编译 tellme_reserved1664 Linux 内核模块的构建规则。"
    "deployment/qwen25_3b_directddr_chain/reserved1664_mmap/tellme_reserved1664.c" = "reserved1664 Linux 字符设备驱动，受控地将指定高地址 DDR 区域 mmap 给用户态并实施范围/权限检查。"
    "deployment/qwen25_3b_no_final_forward/runtime/native/Makefile" = "构建 AArch64 Python 原生 Prefill 扩展的 Makefile，链接 pybind11 并启用 Cortex-A53/NEON 优化。"
    "deployment/qwen25_3b_no_final_forward/runtime/native/prefill_native.cpp" = "PS 侧 Prefill 原生扩展源，使用 AArch64/NEON 加速嵌入、归一化、RoPE、采样和数据整理等 CPU 辅助计算。"
    "hls/prefill_decode_shared_l40_packetdf/qwen25_prefill_w4a8.hpp" = "Qwen2.5 W4A8 HLS 核的接口、常量、数据类型、寄存器映射和顶层函数声明。"
    "hls/prefill_decode_shared_l40_packetdf/qwen25_prefill_w4a8.cpp" = "FPGA PL 计算核心的完整 HLS 实现，包含 W4 权重解包、A8 激活、分块矩阵乘、Prefill、Decode 与 Direct-DDR 链式数据流。"
    "hls/prefill_decode_shared_l40_packetdf/tb_qwen25_prefill_w4a8_single.cpp" = "单算子 HLS C 仿真测试平台，构造确定性输入并检查 W4A8 内核数值和接口行为。"
    "hls/prefill_decode_shared_l40_packetdf/tb_qwen25_prefill_w4a8.cpp" = "Prefill/Decode 多模式 HLS 测试平台，覆盖分块、链式调用、计数器和误差门限。"
    "hls/prefill_decode_shared_l40_packetdf/run_csim_single.tcl" = "运行单算子 HLS C 仿真的 Vitis 2026.1 TCL 脚本。"
    "hls/prefill_decode_shared_l40_packetdf/run_csim_synth.tcl" = "顺序执行 HLS C 仿真与综合，用于同时检查数值正确性和资源/时序估算。"
    "hls/prefill_decode_shared_l40_packetdf/run_csim.tcl" = "运行共享 Prefill/Decode HLS 核完整 C 仿真的 TCL 入口。"
    "hls/prefill_decode_shared_l40_packetdf/run_decode_directddr_chain_csim.tcl" = "运行 M20 Decode Direct-DDR 链式顶层的 C 仿真门禁。"
    "hls/prefill_decode_shared_l40_packetdf/run_decode_directddr_chain_synth.tcl" = "综合 Decode Direct-DDR 链式 HLS 顶层并导出资源与时序报告。"
    "hls/prefill_decode_shared_l40_packetdf/run_decode_directddr_chain_export.tcl" = "将通过综合的 Decode Direct-DDR 链式 HLS 核导出为 Vivado 可集成 IP。"
    "hls/prefill_decode_shared_l40_packetdf/run_export.tcl" = "导出共享 Prefill HLS 核 IP，供 Prefill l40 Vivado 工程使用。"
    "hls/prefill_decode_shared_l40_packetdf/run_synth_only.tcl" = "只执行共享 Prefill HLS 核综合，用于快速审计资源和时序。"
    "vivado/decode_directddr_chain_highddr/create_candidate_project.tcl" = "创建 Decode Direct-DDR 高地址 DDR 候选 Vivado 工程，连接 HLS IP、AXI DMA/互连与 KV260 平台端口。"
    "vivado/decode_directddr_chain_highddr/run_synthesis.tcl" = "执行 Decode 候选 Vivado 综合并生成利用率、时序和设计检查报告。"
    "vivado/decode_directddr_chain_highddr/run_implementation.tcl" = "执行 Decode 候选布局布线并生成 bitstream/HWH；M20 release 以板端通过版本的二进制哈希为权威。"
    "vivado/prefill_l40_only/create_candidate_project.tcl" = "创建 l40 Prefill 专用 Vivado 工程并连接共享 HLS IP、AXI 数据通路和 KV260 PS。"
    "vivado/prefill_l40_only/inspect_axis_switch.tcl" = "检查 Prefill 工程 AXI-Stream Switch 的端口、路由和属性连接。"
    "vivado/prefill_l40_only/inspect_base.tcl" = "审计 KV260 基础 block design 中的 PS、时钟、复位和地址空间。"
    "vivado/prefill_l40_only/inspect_dma.tcl" = "审计 Prefill DMA 的通道、位宽、突发和地址连接配置。"
    "vivado/prefill_l40_only/run_synthesis.tcl" = "执行 Prefill l40 工程综合并输出资源、DRC 和时序报告。"
    "vivado/prefill_l40_only/run_implementation.tcl" = "执行 Prefill l40 工程布局布线并生成 M20 使用的 Prefill bitstream/HWH。"
}

function Get-Language([string]$path) {
    $name = [IO.Path]::GetFileName($path)
    $extension = [IO.Path]::GetExtension($path).ToLowerInvariant()
    if ($name -eq "Makefile") { return "makefile" }
    switch ($extension) {
        ".py" { return "python" }
        ".sh" { return "bash" }
        ".ps1" { return "powershell" }
        ".service" { return "ini" }
        ".c" { return "c" }
        ".cpp" { return "cpp" }
        ".hpp" { return "cpp" }
        ".tcl" { return "tcl" }
        ".dts" { return "dts" }
        ".cmd" { return "bash" }
        default { return "text" }
    }
}

$sources = @($releaseSources | Sort-Object) + $hardwareSources
$duplicates = $sources | Group-Object | Where-Object Count -gt 1
if ($duplicates) { throw "duplicate source paths: $($duplicates.Name -join ', ')" }

$missing = @()
$missingDescription = @()
$blocks = [Collections.Generic.List[string]]::new()
foreach ($path in $sources) {
    $absolute = Join-Path $workspace $path
    if (-not (Test-Path -LiteralPath $absolute -PathType Leaf)) {
        $missing += $path
        continue
    }
    if (-not $descriptions.ContainsKey($path)) {
        $missingDescription += $path
        continue
    }
    $code = [IO.File]::ReadAllText($absolute).Replace("`r`n", "`n").TrimEnd("`n")
    $language = Get-Language $path
    $blocks.Add((@(
        "代码路径头：``$path``"
        ""
        "代码块："
        ('````{0}' -f $language)
        $code
        '````'
        ""
        "功能块："
        $descriptions[$path]
    ) -join "`n"))
}

if ($missing) { throw "missing source files: $($missing -join ', ')" }
if ($missingDescription) { throw "missing descriptions: $($missingDescription -join ', ')" }

$rendered = ($blocks -join "`n`n====================`n`n") + "`n"
$destination = Join-Path $workspace $OutputPath
$destinationDirectory = Split-Path -Parent $destination
if (-not (Test-Path -LiteralPath $destinationDirectory)) {
    New-Item -ItemType Directory -Path $destinationDirectory | Out-Null
}
[IO.File]::WriteAllText($destination, $rendered, [Text.UTF8Encoding]::new($false))

$separatorCount = ([regex]::Matches($rendered, "(?m)^====================$")).Count
$pathHeaderCount = ([regex]::Matches($rendered, "(?m)^代码路径头：``[^``]+``$")).Count
$functionCount = ([regex]::Matches($rendered, "(?m)^功能块：$")).Count
if ($pathHeaderCount -ne $sources.Count -or $functionCount -ne $sources.Count) {
    throw "block count mismatch: sources=$($sources.Count) paths=$pathHeaderCount functions=$functionCount"
}
if ($separatorCount -ne ($sources.Count - 1)) {
    throw "separator count mismatch: expected=$($sources.Count - 1) actual=$separatorCount"
}

$hash = (Get-FileHash -Algorithm SHA256 -LiteralPath $destination).Hash.ToLowerInvariant()
Write-Output "M20_CODE_MARKDOWN_PASS"
Write-Output "path=$destination"
Write-Output "source_blocks=$($sources.Count)"
Write-Output "separators=$separatorCount"
Write-Output "bytes=$((Get-Item -LiteralPath $destination).Length)"
Write-Output "sha256=$hash"
