[CmdletBinding()]
param(
    [string]$OutputPath = 'TeLLMe_Current_Deployment_Code.md'
)

$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest

$workspace = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
$separator = '===================='

$items = @(
    [pscustomobject]@{ Path='deployment\mage_vl4b\m129_source_closure\hls\mage_prefill_t6_runtime_wrapper_m75b\mage_prefill_t6_arith.hpp'; Lang='cpp'; Function='定义底层量化算术核的数据类型、AXI Stream 接口和公共常量，是 T32 FPGA Linear 算术链的基础头文件。' },
    [pscustomobject]@{ Path='deployment\mage_vl4b\m129_source_closure\hls\mage_prefill_t6_runtime_wrapper_m75b\mage_prefill_t6_arith.cpp'; Lang='cpp'; Function='实现基础 W2/W4 解包、缩放、乘加与流式输出逻辑，为后续 T32 微块计算提供可综合算术单元。' },
    [pscustomobject]@{ Path='deployment\mage_vl4b\m129_source_closure\hls\mage_prefill_m89_t32_reuse\mage_prefill_m89_t32_reuse.hpp'; Lang='cpp'; Function='定义一次权重读取服务 32 个 Token 的 T32 权重复用接口、描述符和流数据合同。' },
    [pscustomobject]@{ Path='deployment\mage_vl4b\m129_source_closure\hls\mage_prefill_m89d_t32_microtile\mage_prefill_m89d_t32_microtile.hpp'; Lang='cpp'; Function='声明 T32 微分块计算层的接口，把大矩阵乘拆成可在 KV260 片上资源中执行的小块。' },
    [pscustomobject]@{ Path='deployment\mage_vl4b\m129_source_closure\hls\mage_prefill_m89d_t32_microtile\mage_prefill_m89d_t32_microtile.cpp'; Lang='cpp'; Function='实现 T32 微分块、部分和累加和流式前进逻辑，控制片上缓存与底层算术单元的调用。' },
    [pscustomobject]@{ Path='deployment\mage_vl4b\m129_source_closure\hls\mage_prefill_m89e_t32_packedaccum\mage_prefill_m89e_t32_packedaccum.cpp'; Lang='cpp'; Function='实现 T32 打包累加路径，减少中间结果的数据搬运并保持输出字数和 TLAST 合同。' },
    [pscustomobject]@{ Path='deployment\mage_vl4b\m129_source_closure\hls\mage_prefill_m89h_t32_chunkedpacked\mage_prefill_m89h_t32_chunkedpacked.cpp'; Lang='cpp'; Function='实现分块打包的 T32 数据通路，使较大的 Linear 能按 descriptor 分片执行。' },
    [pscustomobject]@{ Path='deployment\mage_vl4b\m129_source_closure\hls\mage_prefill_m89n_t32_w2w4\mage_prefill_m89n_t32_w2w4.cpp'; Lang='cpp'; Function='实现 W2/W4 两种权重量化格式在同一 T32 FPGA 核中的分派和执行。' },
    [pscustomobject]@{ Path='deployment\mage_vl4b\m129_source_closure\hls\mage_prefill_m89o_shared15\mage_prefill_m89o_shared15.cpp'; Lang='cpp'; Function='实现共享输入与中间通路的多链调度，降低 QKV、Gate/Up 等家族的重复搬运开销。' },
    [pscustomobject]@{ Path='deployment\mage_vl4b\m129_source_closure\hls\mage_prefill_m89s_scaleaware\mage_prefill_m89s_scaleaware.cpp'; Lang='cpp'; Function='实现 activation scale 感知的量化与输出恢复逻辑，为非有限值重试和数值稳定性提供硬件支持。' },
    [pscustomobject]@{ Path='deployment\mage_vl4b\m129_source_closure\hls\mage_prefill_m89x_runtime\mage_prefill_m89x_runtime.hpp'; Lang='cpp'; Function='声明当前 Build 0x4D395832 的顶层 T32 FPGA Runtime 接口和寄存器/流合同。' },
    [pscustomobject]@{ Path='deployment\mage_vl4b\m129_source_closure\hls\mage_prefill_m89x_runtime\mage_prefill_m89x_runtime.cpp'; Lang='cpp'; Function='组合 W2/W4、分片、scale-aware 和多 AXI 通路，形成当前稳定 T32 FPGA 顶层核。' },

    [pscustomobject]@{ Path='deployment\mage_vl4b\m241_grouped_gqa_board_candidate\m230_prefill_runtime.py'; Lang='python'; Function='提供 T32 Prefill 基础调度、权重 stage-once、描述符提交和运行统计。' },
    [pscustomobject]@{ Path='deployment\mage_vl4b\m241_grouped_gqa_board_candidate\m231_prefill_runtime.py'; Lang='python'; Function='优化 FPGA 输出解析与缓冲复用，减少 T32 block 结果转换和重复分配。' },
    [pscustomobject]@{ Path='deployment\mage_vl4b\m241_grouped_gqa_board_candidate\m236_prefill_runtime.py'; Lang='python'; Function='将当前 FPGA block 的执行与上一 block 的融合解析并行，降低 launch/parse 串行等待。' },
    [pscustomobject]@{ Path='deployment\mage_vl4b\m241_grouped_gqa_board_candidate\m238_prefill_runtime.py'; Lang='python'; Function='在 FPGA 执行当前 T32 block 时预量化并打包下一 block，形成输入预取流水。' },
    [pscustomobject]@{ Path='deployment\mage_vl4b\m241_grouped_gqa_board_candidate\m230_video_language_runtime.py'; Lang='python'; Function='把 T32 Prefill Runtime 适配到完整 Mage-VL 4B 视频语言模型调用接口。' },
    [pscustomobject]@{ Path='deployment\mage_vl4b\m241_grouped_gqa_board_candidate\m241_video_language_runtime.py'; Lang='python'; Function='实现通过实板门禁的 Grouped-GQA Attention，并保留参考 RoPE，组成优化后的 4B 语义复核后端。' },
    [pscustomobject]@{ Path='deployment\mage_vl4b\m243_web_prefill_board_candidate\m243_video_server.py'; Lang='python'; Function='把 M238 T32 Prefill 与 M241 视频语言模型安装到 Web Runtime，是慢速 4B 异步复核通道的入口。' },

    [pscustomobject]@{ Path='deployment\mage_vl4b\m254_dual_path_web_candidate_r4\knife_alarm.py'; Lang='python'; Function='定义刀具 SAFE/REVIEW/ALARM 状态机、迟滞策略、证据字段和报警事件合同。' },
    [pscustomobject]@{ Path='deployment\mage_vl4b\m254_dual_path_web_candidate_r4\fast_safety_monitor.py'; Lang='python'; Function='把人物动作与刀具检测合成为统一 safety_result，保证慢速 4B 复核不会阻塞快速报警。' },
    [pscustomobject]@{ Path='deployment\mage_vl4b\m254_dual_path_web_candidate_r4\temporal_action_adapter.py'; Lang='python'; Function='维护每个人物的有界时序历史，根据轨迹和运动特征输出 WORKING/IDLE/WALKING/FALLING/FIGHTING/UNKNOWN。' },
    [pscustomobject]@{ Path='deployment\mage_vl4b\m254_dual_path_web_candidate_r4\immediate_safety_monitor.py'; Lang='python'; Function='提供逐帧刀具即时报警分支，使首帧刀具阳性无需等待四帧动作窗口。' },
    [pscustomobject]@{ Path='deployment\mage_vl4b\m254_dual_path_web_candidate_r4\fast_frame_pipeline.py'; Lang='python'; Function='完成检测框、IoU 人物跟踪、运动特征、动作适配和即时刀具报警的端到端快速帧处理。' },
    [pscustomobject]@{ Path='deployment\mage_vl4b\m254_dual_path_web_candidate_r4\latest_fast_stream.py'; Lang='python'; Function='实现容量为 1 的 latest-only 邮箱和独立工作线程，覆盖旧帧而不形成无限积压。' },
    [pscustomobject]@{ Path='deployment\mage_vl4b\m254_dual_path_web_candidate_r4\m253_board_latest_stream.py'; Lang='python'; Function='加载并预热 SSDLite320 MobileNetV3 检测器，在 KV260 A53 上输出人物/刀具检测并驱动最新帧快速链。' },
    [pscustomobject]@{ Path='deployment\mage_vl4b\m254_dual_path_web_candidate_r4\m254_dual_path_core.py'; Lang='python'; Function='协调快速安全链和容量为 1 的报警触发式 4B 语义复核队列，形成双路径调度核心。' },
    [pscustomobject]@{ Path='deployment\mage_vl4b\m254_dual_path_web_candidate_r4\m254_video_server.py'; Lang='python'; Function='提供 M254 HTTP/SSE 服务，把浏览器视频帧送入快速链，并异步推送安全结果和 4B 复核状态。' },
    [pscustomobject]@{ Path='deployment\mage_vl4b\m254_dual_path_web_candidate_r4\m254_dependency_preflight.py'; Lang='python'; Function='在启动服务前一次检查 ARM64、Torch/Torchvision、检测器 strict load、T32/M243 依赖和候选哈希。' },
    [pscustomobject]@{ Path='deployment\mage_vl4b\m254_dual_path_web_candidate_r4\m254_runtime_ready_probe.py'; Lang='python'; Function='对运行中的双路径服务执行有界就绪探测，核对快链、语义链、Build ID 和 Kernel 身份。' },
    [pscustomobject]@{ Path='deployment\mage_vl4b\m254_dual_path_web_candidate_r4\verify_m254_candidate.py'; Lang='python'; Function='按 manifest 复核 M254 候选文件数、大小与 SHA-256，防止缺失依赖或旧文件混入。' },
    [pscustomobject]@{ Path='deployment\mage_vl4b\m254_dual_path_web_candidate_r4\run_m254_board_gate.sh'; Lang='bash'; Function='以 fail-closed 顺序执行板端依赖预检、服务切换、双路径启动、就绪验证和失败回滚。' },
    [pscustomobject]@{ Path='deployment\mage_vl4b\m254_dual_path_web_candidate_r4\static\index.html'; Lang='html'; Function='定义监控视频、人物状态、刀具报警、快速链时延、FPGA 证据和 4B 复核结果的网页结构。' },
    [pscustomobject]@{ Path='deployment\mage_vl4b\m254_dual_path_web_candidate_r4\static\style.css'; Lang='css'; Function='实现当前干净浅色风格、报警红色状态、人物动作卡片和响应式布局。' },
    [pscustomobject]@{ Path='deployment\mage_vl4b\m254_dual_path_web_candidate_r4\static\app.js'; Lang='javascript'; Function='控制摄像头/本地视频采样、活跃会话接管、帧 POST、SSE 订阅及快速/语义结果渲染。' }
)

$lines = [System.Collections.Generic.List[string]]::new()
$lines.Add('# TeLLMe 当前部署完整代码汇编')
$lines.Add('')
$lines.Add('生成范围：当前实板活动的 M254 R4 双路径 Web 代码、其复用的 M236/M238/M241 T32 语义后端核心，以及 Build `0x4D395832` 的 T32 HLS 源码闭包。')
$lines.Add('')
$lines.Add('边界说明：二进制模型、权重、wheel、xclbin、bitstream、测试夹具、结果 JSON 和测试代码不是“源代码”，因此不嵌入本文件；T64 已淘汰，不在当前代码路径中。每个代码块均为对应源文件的完整内容。')
$lines.Add('')

for ($index = 0; $index -lt $items.Count; $index++) {
    $item = $items[$index]
    $absolute = Join-Path $workspace $item.Path
    if (-not (Test-Path -LiteralPath $absolute -PathType Leaf)) {
        throw "Missing source file: $($item.Path)"
    }
    $content = [System.IO.File]::ReadAllText($absolute)
    if ($content.Contains('```')) {
        throw "Source contains Markdown fence and needs a longer fence: $($item.Path)"
    }
    $hash = (Get-FileHash -Algorithm SHA256 -LiteralPath $absolute).Hash.ToLowerInvariant()

    $lines.Add('## 代码路径头')
    $lines.Add('')
    $lines.Add('`' + $item.Path.Replace('\','/') + '`')
    $lines.Add('')
    $lines.Add('SHA-256：`' + $hash + '`')
    $lines.Add('')
    $lines.Add('### 代码块')
    $lines.Add('')
    $lines.Add('```' + $item.Lang)
    $lines.Add($content.TrimEnd("`r", "`n"))
    $lines.Add('```')
    $lines.Add('')
    $lines.Add('### 功能块')
    $lines.Add('')
    $lines.Add($item.Function)
    $lines.Add('')
    if ($index -lt ($items.Count - 1)) {
        $lines.Add($separator)
        $lines.Add('')
    }
}

$output = if ([System.IO.Path]::IsPathRooted($OutputPath)) {
    $OutputPath
} else {
    Join-Path $workspace $OutputPath
}
[System.IO.File]::WriteAllText($output, ($lines -join "`n") + "`n", [System.Text.UTF8Encoding]::new($false))

$text = [System.IO.File]::ReadAllText($output)
$separatorCount = ([regex]::Matches($text, '(?m)^====================$')).Count
if ($separatorCount -ne ($items.Count - 1)) {
    throw "Separator count mismatch: observed=$separatorCount expected=$($items.Count - 1)"
}
if (([regex]::Matches($text, '(?m)^## 代码路径头$')).Count -ne $items.Count) {
    throw 'Code-path header count mismatch'
}
if (([regex]::Matches($text, '(?m)^### 功能块$')).Count -ne $items.Count) {
    throw 'Function-block count mismatch'
}

$result = [ordered]@{
    status = 'PASS'
    output = $output
    source_file_count = $items.Count
    separator_count = $separatorCount
    bytes = (Get-Item -LiteralPath $output).Length
    sha256 = (Get-FileHash -Algorithm SHA256 -LiteralPath $output).Hash.ToLowerInvariant()
}
$result | ConvertTo-Json
