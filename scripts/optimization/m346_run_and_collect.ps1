[CmdletBinding()]
param([switch]$SelfTest)
$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest
function Invoke-GateAndCollect {
    param([scriptblock]$GateAction,[scriptblock]$CollectAction)
    $gateError = $null
    try { & $GateAction } catch { $gateError = $_ }
    & $CollectAction
    if ($gateError) { throw $gateError }
}
if ($SelfTest) {
    $script:m346TestCollected = $false
    $caught = $false
    try { Invoke-GateAndCollect -GateAction { throw 'EXPECTED_GATE_FAIL' } -CollectAction { $script:m346TestCollected = $true } }
    catch { if ($_.Exception.Message -ne 'EXPECTED_GATE_FAIL') { throw }; $caught = $true }
    if (-not ($caught -and $script:m346TestCollected)) { throw 'Terminating FAIL bypassed collection' }
    try { Invoke-GateAndCollect -GateAction {} -CollectAction { throw 'EXPECTED_COLLECT_FAIL' }; throw 'Collector failure accepted' }
    catch { if ($_.Exception.Message -ne 'EXPECTED_COLLECT_FAIL') { throw } }
    Write-Output 'M346_CONTROLLER_SELF_TEST_PASS terminating-failure-collects collector-failure-stops'
    exit 0
}
$workspace = (Resolve-Path (Join-Path $PSScriptRoot '../..')).Path
$priorSha = 'b149cf6d4e031628c4ff43c99f6e4579575a64598ee55d80e35c2f7ff48e8fd4'
$priorPath = Join-Path $workspace 'deployment/mage_vl4b/optimization_v1/runs/M345-fixed-video-board-01/BOARD_RESULT.json'
if ((Get-FileHash -LiteralPath $priorPath -Algorithm SHA256).Hash.ToLowerInvariant() -ne $priorSha) { throw 'M345 raw identity differs' }
$board = Get-Content -LiteralPath (Join-Path $workspace 'deployment/mage_vl4b/BOARD_GATE_RESULT.json') -Raw -Encoding UTF8 | ConvertFrom-Json
if ($board.latest_m345_fixed_video.sha256 -ne $priorSha) { throw 'BOARD prerequisite differs' }
foreach ($name in @('CURRENT_STATE.md','docsMILESTONES.md')) {
    if (-not (Get-Content -LiteralPath (Join-Path $workspace $name) -Raw -Encoding UTF8).Contains($priorSha)) { throw "Prerequisite not synchronized: $name" }
}
if (Test-Path -LiteralPath (Join-Path $workspace 'deployment/mage_vl4b/optimization_v1/runs/M346-load-memory-board-01/BOARD_RESULT.json')) { throw 'Existing result; collect only' }
$package = Join-Path $workspace 'deployment/mage_vl4b/optimization_v1/candidates/M346-load-memory-01'
$digest = (Get-FileHash -LiteralPath (Join-Path $package 'PACKAGE_MANIFEST.json') -Algorithm SHA256).Hash.ToLowerInvariant()
$uart = Join-Path $workspace 'scripts/m75c_uart_command.ps1'
& $uart -Command 'bash -n /home/ubuntu/m346_load_memory_01/run_m346_memory.sh' -LogPath 'tmp/m346/runner_syntax_uart.log' -TimeoutSeconds 15 -MarkerPrefix '__M346_SYNTAX_RC_'
if (-not $?) { throw 'Runner syntax failed; no diagnostic' }
& $uart -Command 'sudo -n true' -LogPath 'tmp/m346/sudo_before_diagnostic_uart.log' -TimeoutSeconds 15 -MarkerPrefix '__M346_SUDO_RC_'
if (-not $?) { throw 'Same-terminal sudo expired; no diagnostic' }
Invoke-GateAndCollect -GateAction {
    & $uart -Command "bash /home/ubuntu/m346_load_memory_01/run_m346_memory.sh $digest" -LogPath 'tmp/m346/load-memory_uart.log' -TimeoutSeconds 900 -MarkerPrefix '__M346_MEMORY_RC_'
} -CollectAction {
    & 'C:\Users\30429\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe' -B (Join-Path $PSScriptRoot 'm346_collect_memory.py')
    if ($LASTEXITCODE -ne 0) { throw 'Collector failed; repair recovery only; never repeat diagnostic' }
}
Write-Output 'M346_LOAD_MEMORY_RESULT_SYNCHRONIZED_PASS'
