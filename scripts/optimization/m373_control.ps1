[CmdletBinding()]
param([ValidateSet('SelfTest','Check','Upload','Run','Collect')][string]$Mode)
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
    $script:collected=$false; $caught=$false
    try { Invoke-GateAndCollect { throw 'EXPECTED_GATE_FAIL' } { $script:collected=$true } }
    catch { if ($_.Exception.Message -ne 'EXPECTED_GATE_FAIL') { throw }; $caught=$true }
    if (-not ($caught -and $script:collected)) { throw 'Gate failure skipped collection' }
    try { Invoke-GateAndCollect {} { throw 'EXPECTED_COLLECT_FAIL' }; throw 'Collector failure ignored' }
    catch { if ($_.Exception.Message -ne 'EXPECTED_COLLECT_FAIL') { throw } }
    $tokens=$null;$parseErrors=$null
    [void][System.Management.Automation.Language.Parser]::ParseFile($PSCommandPath,[ref]$tokens,[ref]$parseErrors)
    if ($parseErrors.Count) { throw 'Controller parse error' }
    Write-Output 'M373_CONTROL_SELF_TEST_PASS'
    exit 0
}
$workspace=(Resolve-Path (Join-Path $PSScriptRoot '../..')).Path
$local='deployment/mage_vl4b/optimization_v1/candidates/M373-future-wait-component-01'
$remote='/home/ubuntu/m373_future_wait_component_01'
$package=Join-Path $workspace $local
$manifest=Get-Content -LiteralPath (Join-Path $package 'PACKAGE_MANIFEST.json') -Raw -Encoding UTF8 | ConvertFrom-Json
$digest=(Get-FileHash -LiteralPath (Join-Path $package 'PACKAGE_MANIFEST.json') -Algorithm SHA256).Hash.ToLowerInvariant()
$uart=Join-Path $workspace 'scripts/m75c_uart_command.ps1'
$python='C:\Users\30429\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe'
$workflow=Join-Path $PSScriptRoot 'm373_workflow.py'
if ($Mode -eq 'Check') {
    & $uart -Command 'sudo -n true' -LogPath 'tmp/m373/sudo_precheck_02.log' -TimeoutSeconds 15 -MarkerPrefix '__M373_CHECK_SUDO_RC_'
    if (-not $?) { throw 'Sudo expired; no upload or gate' }
    exit 0
}
$board=Get-Content -LiteralPath (Join-Path $workspace 'deployment/mage_vl4b/BOARD_GATE_RESULT.json') -Raw -Encoding UTF8 | ConvertFrom-Json
$prep=$board.latest_m373_future_wait_preparation
if ($prep.manifest_sha256 -ne $digest) { throw 'Manifest prerequisite differs' }
if ((Get-FileHash -LiteralPath (Join-Path $workspace $prep.result) -Algorithm SHA256).Hash.ToLowerInvariant() -ne $prep.sha256) { throw 'Preparation raw differs' }
foreach ($name in @('CURRENT_STATE.md','docsMILESTONES.md')) {
    $state=Get-Content -LiteralPath (Join-Path $workspace $name) -Raw -Encoding UTF8
    if (-not $state.Contains($prep.sha256)) { throw 'Preparation not synchronized' }
}
foreach ($row in $manifest.files) {
    $path=Join-Path $package $row.path
    if ((Get-FileHash -LiteralPath $path -Algorithm SHA256).Hash.ToLowerInvariant() -ne $row.sha256 -or (Get-Item -LiteralPath $path).Length -ne $row.bytes) { throw 'Local payload differs' }
}
if ($Mode -eq 'Upload') {
    $authorization=Get-Content -LiteralPath (Join-Path $workspace 'tmp/m373/sudo_precheck_02.log') -Raw -Encoding UTF8
    if (-not $authorization.Contains('__M373_CHECK_SUDO_RC_0__')) { throw 'Fresh human recovery check required' }
    foreach ($name in (@('PACKAGE_MANIFEST.json')+@($manifest.files | ForEach-Object path))) {
        & (Join-Path $workspace 'scripts/m212_uart_put_file_chunked.ps1') -LocalPath "$local/$name" -RemotePath "$remote/$name" -LogPrefix "tmp/m373/upload_$($name.Replace('.','_'))" -ChunkBytes 900 -TimeoutSeconds 25
        if (-not $?) { throw "Upload failed: $name" }
        Write-Output "M373_FILE_TRANSFERRED $name"
    }
    & $python -X utf8 -B $workflow transfer
    if ($LASTEXITCODE -ne 0) { throw 'Transfer evidence failed; no gate' }
    exit 0
}
if ($Mode -eq 'Collect') {
    & $uart -Command "sudo -n env PYTHONDONTWRITEBYTECODE=1 /usr/local/share/pynq-venv/bin/python3 -B $remote/m373_export_result.py" -LogPath 'tmp/m373/component_recollect_uart.log' -TimeoutSeconds 60 -MarkerPrefix '__M373_EXPORT_RC_'
    if (-not $?) { throw 'Export failed; recover only' }
    & $python -X utf8 -B $workflow collect 'tmp/m373/component_recollect_uart.log'
    if ($LASTEXITCODE -ne 0) { throw 'Evidence collection failed; no rerun' }
    exit 0
}
if ($Mode -ne 'Run') { throw 'Explicit mode required' }
$transfer=$board.latest_m373_future_wait_transfer
if ($transfer.manifest_sha256 -ne $digest) { throw 'Transfer evidence differs' }
if ((Get-FileHash -LiteralPath (Join-Path $workspace $transfer.result) -Algorithm SHA256).Hash.ToLowerInvariant() -ne $transfer.sha256) { throw 'Transfer raw differs' }
foreach ($name in @('CURRENT_STATE.md','docsMILESTONES.md')) {
    if (-not (Get-Content -LiteralPath (Join-Path $workspace $name) -Raw -Encoding UTF8).Contains($transfer.sha256)) { throw 'Transfer not synchronized' }
}
if (Test-Path -LiteralPath (Join-Path $workspace 'deployment/mage_vl4b/optimization_v1/runs/M373-future-wait-board-01/BOARD_RESULT.json')) { throw 'Result exists; collect only' }
if (Test-Path -LiteralPath (Join-Path $workspace 'tmp/m373/component_uart.log')) { throw 'Original run log exists; collect only' }
& $uart -Command "bash -n $remote/run_m373_component.sh" -LogPath 'tmp/m373/runner_syntax_uart.log' -TimeoutSeconds 15 -MarkerPrefix '__M373_SYNTAX_RC_'
if (-not $?) { throw 'Runner syntax failed' }
& $uart -Command 'sudo -n true' -LogPath 'tmp/m373/sudo_before_component_uart.log' -TimeoutSeconds 15 -MarkerPrefix '__M373_GATE_SUDO_RC_'
if (-not $?) { throw 'Sudo expired; no gate' }
Invoke-GateAndCollect {
    & $uart -Command "bash $remote/run_m373_component.sh $digest --enable-fixture-gate" -LogPath 'tmp/m373/component_uart.log' -TimeoutSeconds 60 -MarkerPrefix '__M373_COMPONENT_RC_'
    if (-not $?) { throw 'Original gate/export failed; collector still required' }
} {
    & $python -X utf8 -B $workflow collect 'tmp/m373/component_uart.log'
    if ($LASTEXITCODE -ne 0) { throw 'Collector failed; recover only' }
}
Write-Output 'M373_CPU_COMPONENT_SYNCHRONIZED'
