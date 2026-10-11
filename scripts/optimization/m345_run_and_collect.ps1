[CmdletBinding()]
param([switch]$SelfTest)
$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest
function Invoke-GateAndCollect {
    param([scriptblock]$GateAction, [scriptblock]$CollectAction)
    $gateError = $null
    try { & $GateAction } catch { $gateError = $_ }
    # A terminating UART failure must still recover the already-written FAIL.
    # Collection never invokes a gate or releases board resources.
    & $CollectAction
    if ($gateError) { throw $gateError }
}
if ($SelfTest) {
    $script:m345TestCollected = $false
    $caught = $false
    try {
        Invoke-GateAndCollect -GateAction { throw 'EXPECTED_GATE_FAIL' } -CollectAction { $script:m345TestCollected = $true }
    } catch {
        if ($_.Exception.Message -ne 'EXPECTED_GATE_FAIL') { throw }
        $caught = $true
    }
    if (-not ($caught -and $script:m345TestCollected)) { throw 'Terminating gate FAIL bypassed collection' }
    $script:m345TestGateRan = $false
    try {
        Invoke-GateAndCollect -GateAction { $script:m345TestGateRan = $true } -CollectAction { throw 'EXPECTED_COLLECT_FAIL' }
        throw 'Collector failure accepted'
    } catch { if ($_.Exception.Message -ne 'EXPECTED_COLLECT_FAIL') { throw } }
    if (-not $script:m345TestGateRan) { throw 'Test gate did not execute' }
    Write-Output 'M345_CONTROLLER_SELF_TEST_PASS terminating-gate-failure-collects collector-failure-stops'
    exit 0
}
$workspace = (Resolve-Path (Join-Path $PSScriptRoot '../..')).Path
$priorSha = '897bb817d6bd2a12f5de5437bb015541210f86c297c85456bc570586d479673a'
$priorPath = Join-Path $workspace 'deployment/mage_vl4b/optimization_v1/runs/M344-fixed-text-board-01/BOARD_RESULT.json'
if ((Get-FileHash -LiteralPath $priorPath -Algorithm SHA256).Hash.ToLowerInvariant() -ne $priorSha) { throw 'M344 raw identity differs' }
$board = Get-Content -LiteralPath (Join-Path $workspace 'deployment/mage_vl4b/BOARD_GATE_RESULT.json') -Raw -Encoding UTF8 | ConvertFrom-Json
if ($board.latest_m344_fixed_text.sha256 -ne $priorSha) { throw 'BOARD predecessor not synchronized' }
foreach ($name in @('CURRENT_STATE.md','docsMILESTONES.md')) {
    if (-not (Get-Content -LiteralPath (Join-Path $workspace $name) -Raw -Encoding UTF8).Contains($priorSha)) { throw "Predecessor not synchronized in $name" }
}
if (Test-Path -LiteralPath (Join-Path $workspace 'deployment/mage_vl4b/optimization_v1/runs/M345-fixed-video-board-01/BOARD_RESULT.json')) { throw 'Existing result: collect only; never repeat hardware' }
$package = Join-Path $workspace 'deployment/mage_vl4b/optimization_v1/candidates/M345-fixed-video-01'
$digest = (Get-FileHash -LiteralPath (Join-Path $package 'PACKAGE_MANIFEST.json') -Algorithm SHA256).Hash.ToLowerInvariant()
$uart = Join-Path $workspace 'scripts/m75c_uart_command.ps1'
& $uart -Command 'bash -n /home/ubuntu/m345_fixed_video_01/run_m345_video.sh' -LogPath 'tmp/m345/runner_syntax_uart.log' -TimeoutSeconds 15 -MarkerPrefix '__M345_SYNTAX_RC_'
if (-not $?) { throw 'Runner syntax failed; no gate' }
& $uart -Command 'sudo -n true' -LogPath 'tmp/m345/sudo_before_gate_uart.log' -TimeoutSeconds 15 -MarkerPrefix '__M345_SUDO_RC_'
if (-not $?) { throw 'Same-terminal sudo expired; no gate' }
Invoke-GateAndCollect -GateAction {
    & $uart -Command "bash /home/ubuntu/m345_fixed_video_01/run_m345_video.sh $digest" -LogPath 'tmp/m345/fixed-video_uart.log' -TimeoutSeconds 1200 -MarkerPrefix '__M345_VIDEO_RC_'
} -CollectAction {
    & 'C:\Users\30429\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe' -B (Join-Path $PSScriptRoot 'm345_collect_video.py')
    $collectCode = $LASTEXITCODE
    if ($collectCode -ne 0) { throw "M345 collector rc=$collectCode; repair collection only; do not run hardware again" }
}
Write-Output 'M345_VIDEO_RESULT_SYNCHRONIZED_PASS'
