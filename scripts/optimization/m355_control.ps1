[CmdletBinding()]
param([ValidateSet('SelfTest','Upload','Run','Collect')][string]$Mode)
$ErrorActionPreference='Stop'
Set-StrictMode -Version Latest
function Invoke-GateAndCollect {
    param([scriptblock]$GateAction,[scriptblock]$CollectAction)
    $gateError=$null
    try { & $GateAction } catch { $gateError=$_ }
    & $CollectAction
    if ($gateError) { throw $gateError }
}
if ($Mode -eq 'SelfTest') {
    $script:collected=$false;$caught=$false
    try { Invoke-GateAndCollect { throw 'EXPECTED_GATE_FAIL' } { $script:collected=$true } }
    catch { if ($_.Exception.Message -ne 'EXPECTED_GATE_FAIL') { throw };$caught=$true }
    if (-not ($script:collected -and $caught)) { throw 'Failure skipped collection' }
    try { Invoke-GateAndCollect {} { throw 'EXPECTED_COLLECT_FAIL' };throw 'Collection failure ignored' }
    catch { if ($_.Exception.Message -ne 'EXPECTED_COLLECT_FAIL') { throw } }
    $tokens=$null;$parseErrors=$null
    [void][System.Management.Automation.Language.Parser]::ParseFile($PSCommandPath,[ref]$tokens,[ref]$parseErrors)
    if ($parseErrors.Count) { throw 'Parse error' }
    Write-Output 'M355_CONTROL_SELF_TEST_PASS failure-collects collection-failure-stops'
    exit 0
}
$workspace=(Resolve-Path (Join-Path $PSScriptRoot '../..')).Path
$local='deployment/mage_vl4b/optimization_v1/candidates/M355-device-phase-01'
$remote='/home/ubuntu/m355_device_phase_01'
$pkg=Join-Path $workspace $local
$uart=Join-Path $workspace 'scripts/m75c_uart_command.ps1'
$python='C:\Users\30429\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe'
if ($Mode -eq 'Collect') {
    & $uart -Command 'sudo -n true' -LogPath 'tmp/m355/sudo_recollect_uart.log' -TimeoutSeconds 15 -MarkerPrefix '__M355_RECOVER_SUDO_RC_'
    & $uart -Command "sudo -n /usr/local/share/pynq-venv/bin/python3 -B $remote/m355_export_result.py" -LogPath 'tmp/m355/recollect_uart.log' -TimeoutSeconds 90 -MarkerPrefix '__M355_EXPORT_RC_'
    & $python -B (Join-Path $PSScriptRoot 'm355_workflow.py') collect 'tmp/m355/recollect_uart.log'
    if ($LASTEXITCODE -ne 0) { throw 'Recovery failed; never rerun diagnostic' }
    exit 0
}
$board=Get-Content -LiteralPath (Join-Path $workspace 'deployment/mage_vl4b/BOARD_GATE_RESULT.json') -Raw -Encoding UTF8 | ConvertFrom-Json
$prior=$board.latest_m355_device_phase_preparation
if ((Get-FileHash -LiteralPath (Join-Path $workspace $prior.result) -Algorithm SHA256).Hash.ToLowerInvariant() -ne $prior.sha256) { throw 'Prior raw SHA differs' }
foreach ($name in @('CURRENT_STATE.md','docsMILESTONES.md')) {
    if (-not (Get-Content -LiteralPath (Join-Path $workspace $name) -Raw -Encoding UTF8).Contains($prior.sha256)) { throw 'Prerequisite not synchronized' }
}
$digest=(Get-FileHash -LiteralPath (Join-Path $pkg 'PACKAGE_MANIFEST.json') -Algorithm SHA256).Hash.ToLowerInvariant()
if ($digest -ne $prior.manifest_sha256) { throw 'Manifest changed' }
if ($Mode -eq 'Upload') {
    $m=Get-Content -LiteralPath (Join-Path $pkg 'PACKAGE_MANIFEST.json') -Raw -Encoding UTF8 | ConvertFrom-Json
    foreach ($name in (@('PACKAGE_MANIFEST.json')+@($m.files | ForEach-Object path))) {
        & (Join-Path $workspace 'scripts/m212_uart_put_file_chunked.ps1') -LocalPath "$local/$name" -RemotePath "$remote/$name" -LogPrefix "tmp/m355/upload_$($name.Replace('.','_'))" -ChunkBytes 900 -TimeoutSeconds 25
    }
    Write-Output 'M355_TRANSFER_PASS'
    exit 0
}
if ($Mode -ne 'Run') { throw 'Explicit mode required' }
if ((Test-Path -LiteralPath (Join-Path $workspace 'tmp/m355/device_phase_uart.log')) -or (Test-Path -LiteralPath (Join-Path $workspace 'deployment/mage_vl4b/optimization_v1/runs/M355-device-phase-board-01/BOARD_RESULT.json'))) { throw 'Existing result/run log; collect only' }
& $uart -Command "bash -n $remote/run_m355_device_phase.sh" -LogPath 'tmp/m355/syntax_uart.log' -TimeoutSeconds 15 -MarkerPrefix '__M355_SYNTAX_RC_'
& $uart -Command 'sudo -n true' -LogPath 'tmp/m355/sudo_before_run_uart.log' -TimeoutSeconds 15 -MarkerPrefix '__M355_SUDO_RC_'
Invoke-GateAndCollect {
    & $uart -Command "bash $remote/run_m355_device_phase.sh $digest --enable-device-phase-probe" -LogPath 'tmp/m355/device_phase_uart.log' -TimeoutSeconds 600 -MarkerPrefix '__M355_PHASE_RC_'
} {
    & $python -B (Join-Path $PSScriptRoot 'm355_workflow.py') collect 'tmp/m355/device_phase_uart.log'
    if ($LASTEXITCODE -ne 0) { throw 'Collector failed; recover original bytes only' }
}
Write-Output 'M355_DEVICE_PHASE_RESULT_SYNCHRONIZED'
