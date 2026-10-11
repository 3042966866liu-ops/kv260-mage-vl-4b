[CmdletBinding()]
param([ValidateSet('SelfTest','Upload','Run')][string]$Mode)
$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest
function Invoke-GateAndCollect {
    param([scriptblock]$GateAction,[scriptblock]$CollectAction)
    $gateError=$null
    try { & $GateAction } catch { $gateError=$_ }
    & $CollectAction
    if ($gateError) { throw $gateError }
}
if ($Mode -eq 'SelfTest') {
    $script:m347Collected=$false; $caught=$false
    try { Invoke-GateAndCollect { throw 'EXPECTED_GATE_FAIL' } { $script:m347Collected=$true } }
    catch { if ($_.Exception.Message -ne 'EXPECTED_GATE_FAIL') { throw }; $caught=$true }
    if (-not ($caught -and $script:m347Collected)) { throw 'FAIL skipped collection' }
    try { Invoke-GateAndCollect {} { throw 'EXPECTED_COLLECT_FAIL' }; throw 'Collector failure ignored' }
    catch { if ($_.Exception.Message -ne 'EXPECTED_COLLECT_FAIL') { throw } }
    $tokens=$null; $parseErrors=$null
    [void][System.Management.Automation.Language.Parser]::ParseFile($PSCommandPath,[ref]$tokens,[ref]$parseErrors)
    if ($parseErrors.Count) { throw 'Controller parse error' }
    Write-Output 'M347_CONTROL_SELF_TEST_PASS failure-collects collector-failure-stops parser-pass'
    exit 0
}
$workspace=(Resolve-Path (Join-Path $PSScriptRoot '../..')).Path
$local='deployment/mage_vl4b/optimization_v1/candidates/M347-asset-memory-01'
$remote='/home/ubuntu/m347_asset_memory_01'
$package=Join-Path $workspace $local
$manifest=Get-Content -LiteralPath (Join-Path $package 'PACKAGE_MANIFEST.json') -Raw -Encoding UTF8 | ConvertFrom-Json
$digest=(Get-FileHash -LiteralPath (Join-Path $package 'PACKAGE_MANIFEST.json') -Algorithm SHA256).Hash.ToLowerInvariant()
$uart=Join-Path $workspace 'scripts/m75c_uart_command.ps1'
if ($Mode -eq 'Upload') {
    foreach ($name in (@('PACKAGE_MANIFEST.json')+@($manifest.files | ForEach-Object path))) {
        & (Join-Path $workspace 'scripts/m212_uart_put_file_chunked.ps1') -LocalPath "$local/$name" -RemotePath "$remote/$name" -LogPrefix "tmp/m347/upload_$($name.Replace('.','_'))" -ChunkBytes 1800 -TimeoutSeconds 25
        if (-not $?) { throw "Upload failed: $name" }
    }
    Write-Output 'M347_TRANSFER_PASS'
    exit 0
}
if ($Mode -ne 'Run') { throw 'Explicit mode required' }
$prior='cc04ea32daba54878a4ac0f63a7cd990db36e67d745c1e696adb806fd60e086a'
if ((Get-FileHash -LiteralPath (Join-Path $workspace 'deployment/mage_vl4b/optimization_v1/runs/M346-load-memory-board-01/BOARD_RESULT.json') -Algorithm SHA256).Hash.ToLowerInvariant() -ne $prior) { throw 'Prior raw differs' }
$board=Get-Content -LiteralPath (Join-Path $workspace 'deployment/mage_vl4b/BOARD_GATE_RESULT.json') -Raw -Encoding UTF8 | ConvertFrom-Json
if ($board.latest_m346_load_memory.sha256 -ne $prior) { throw 'Prior BOARD differs' }
foreach ($name in @('CURRENT_STATE.md','docsMILESTONES.md')) {
    if (-not (Get-Content -LiteralPath (Join-Path $workspace $name) -Raw -Encoding UTF8).Contains($prior)) { throw 'Prior state not synchronized' }
}
if (Test-Path -LiteralPath (Join-Path $workspace 'deployment/mage_vl4b/optimization_v1/runs/M347-asset-memory-board-01/BOARD_RESULT.json')) { throw 'Result exists; collection only' }
& $uart -Command "bash -n $remote/run_m347_asset_memory.sh" -LogPath 'tmp/m347/runner_syntax_uart.log' -TimeoutSeconds 15 -MarkerPrefix '__M347_SYNTAX_RC_'
if (-not $?) { throw 'Runner syntax failed' }
& $uart -Command 'sudo -n true' -LogPath 'tmp/m347/sudo_before_diagnostic_uart.log' -TimeoutSeconds 15 -MarkerPrefix '__M347_SUDO_RC_'
if (-not $?) { throw 'Same-terminal sudo expired; no diagnostic' }
Invoke-GateAndCollect -GateAction {
    & $uart -Command "bash $remote/run_m347_asset_memory.sh $digest" -LogPath 'tmp/m347/asset_memory_uart.log' -TimeoutSeconds 420 -MarkerPrefix '__M347_ASSET_RC_'
} -CollectAction {
    & 'C:\Users\30429\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe' -B (Join-Path $PSScriptRoot 'm347_workflow.py') collect
    if ($LASTEXITCODE -ne 0) { throw 'Collector failed; repair only, no board rerun' }
}
Write-Output 'M347_ASSET_MEMORY_SYNCHRONIZED_PASS'
