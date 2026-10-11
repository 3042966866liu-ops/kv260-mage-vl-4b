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
    Write-Output 'M374_CONTROL_SELF_TEST_PASS'
    exit 0
}
$workspace=(Resolve-Path (Join-Path $PSScriptRoot '../..')).Path
$local='deployment/mage_vl4b/optimization_v1/candidates/M374-layer-future-wait-01'
$remote='/home/ubuntu/m374_layer_future_wait_candidate_01'
$package=Join-Path $workspace $local
$manifest=Get-Content -LiteralPath (Join-Path $package 'PACKAGE_MANIFEST.json') -Raw -Encoding UTF8 | ConvertFrom-Json
$digest=(Get-FileHash -LiteralPath (Join-Path $package 'PACKAGE_MANIFEST.json') -Algorithm SHA256).Hash.ToLowerInvariant()
$uart=Join-Path $workspace 'scripts/m75c_uart_command.ps1'
$python='C:\Users\30429\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe'
$workflow=Join-Path $PSScriptRoot 'm374_workflow.py'
if ($Mode -eq 'Check') {
    & $uart -Command 'sudo -n true' -LogPath 'tmp/m374/sudo_precheck_01.log' -TimeoutSeconds 15 -MarkerPrefix '__M374_CHECK_SUDO_RC_'
    if (-not $?) { throw 'Sudo expired; no upload or gate' }
    exit 0
}
$board=Get-Content -LiteralPath (Join-Path $workspace 'deployment/mage_vl4b/BOARD_GATE_RESULT.json') -Raw -Encoding UTF8 | ConvertFrom-Json
$prep=$board.latest_m374_layer_wait_preparation
$support=$board.latest_m374_layer_wait_support
if ($support.manifest_sha256 -ne $digest -or (Get-FileHash -LiteralPath (Join-Path $workspace $support.result) -Algorithm SHA256).Hash.ToLowerInvariant() -ne $support.sha256) { throw 'Support prerequisite differs' }
if ($prep.manifest_sha256 -ne $digest) { throw 'Manifest prerequisite differs' }
if ((Get-FileHash -LiteralPath (Join-Path $workspace $prep.result) -Algorithm SHA256).Hash.ToLowerInvariant() -ne $prep.sha256) { throw 'Preparation raw differs' }
foreach ($name in @('CURRENT_STATE.md','docsMILESTONES.md')) {
    $state=Get-Content -LiteralPath (Join-Path $workspace $name) -Raw -Encoding UTF8
    if (-not ($state.Contains($prep.sha256) -and $state.Contains($support.sha256))) { throw 'Preparation/support not synchronized' }
}
foreach ($row in $manifest.files) {
    $path=Join-Path $package $row.path
    if ((Get-FileHash -LiteralPath $path -Algorithm SHA256).Hash.ToLowerInvariant() -ne $row.sha256 -or (Get-Item -LiteralPath $path).Length -ne $row.bytes) { throw 'Local payload differs' }
}
if ($Mode -eq 'Upload') {
    $authorization=Get-Content -LiteralPath (Join-Path $workspace 'tmp/m374/sudo_precheck_01.log') -Raw -Encoding UTF8
    if (-not $authorization.Contains('__M374_PRECHECK_SUDO_RC_0__')) { throw 'Fresh human recovery check required' }
    & $uart -Command "test ! -e $remote" -LogPath 'tmp/m374/package_absence_uart.log' -TimeoutSeconds 15 -MarkerPrefix '__M374_ABSENT_RC_'
    if (-not $?) { throw 'Package exists; do not overwrite' }
    $oldManifest=Get-Content -LiteralPath (Join-Path $workspace 'deployment/mage_vl4b/optimization_v1/candidates/M365-staged-layer-03/PACKAGE_MANIFEST.json') -Raw -Encoding UTF8 | ConvertFrom-Json
    $oldEntries=@{}
    foreach ($entry in $oldManifest.files) { $oldEntries[$entry.path]=$entry.sha256 }
    $delta=@($manifest.files | Where-Object { -not $oldEntries.ContainsKey($_.path) -or $oldEntries[$_.path] -ne $_.sha256 } | ForEach-Object path)
    foreach ($name in (@('PACKAGE_MANIFEST.json')+$delta)) {
        & (Join-Path $workspace 'scripts/m212_uart_put_file_chunked.ps1') -LocalPath "$local/$name" -RemotePath "$remote/$name" -LogPrefix "tmp/m374/upload_$($name.Replace('.','_'))" -ChunkBytes 900 -TimeoutSeconds 25
        if (-not $?) { throw "Upload failed: $name" }
        Write-Output "M374_FILE_TRANSFERRED $name"
    }
    & $uart -Command "sudo -n env PYTHONDONTWRITEBYTECODE=1 /usr/local/share/pynq-venv/bin/python -B $remote/m374_assemble.py $digest" -LogPath 'tmp/m374/assembly_uart.log' -TimeoutSeconds 30 -MarkerPrefix '__M374_ASSEMBLY_RC_'
    if (-not $?) { throw 'Assembly failed; no gate' }
    & $uart -Command "sudo -n bash -n $remote/run_m374_staged_layer.sh" -LogPath 'tmp/m374/root_syntax_uart.log' -TimeoutSeconds 15 -MarkerPrefix '__M374_SYNTAX_RC_'
    if (-not $?) { throw 'Root bash-n failed' }
    & $python -X utf8 -B $workflow transfer
    if ($LASTEXITCODE -ne 0) { throw 'Transfer evidence failed; no gate' }
    exit 0
}
if ($Mode -eq 'Collect') {
    & $uart -Command "sudo -n env PYTHONDONTWRITEBYTECODE=1 /usr/local/share/pynq-venv/bin/python3 -B $remote/m374_export_result.py B1" -LogPath 'tmp/m374/component_recollect_uart.log' -TimeoutSeconds 60 -MarkerPrefix '__M374_EXPORT_RC_'
    if (-not $?) { throw 'Export failed; recover only' }
    & $python -X utf8 -B $workflow collect 'tmp/m374/component_recollect_uart.log'
    if ($LASTEXITCODE -ne 0) { throw 'Evidence collection failed; no rerun' }
    exit 0
}
if ($Mode -ne 'Run') { throw 'Explicit mode required' }
$transfer=$board.latest_m374_layer_wait_transfer
if ($transfer.manifest_sha256 -ne $digest) { throw 'Transfer evidence differs' }
if ((Get-FileHash -LiteralPath (Join-Path $workspace $transfer.result) -Algorithm SHA256).Hash.ToLowerInvariant() -ne $transfer.sha256) { throw 'Transfer raw differs' }
foreach ($name in @('CURRENT_STATE.md','docsMILESTONES.md')) {
    if (-not (Get-Content -LiteralPath (Join-Path $workspace $name) -Raw -Encoding UTF8).Contains($transfer.sha256)) { throw 'Transfer not synchronized' }
}
if (Test-Path -LiteralPath (Join-Path $workspace 'deployment/mage_vl4b/optimization_v1/runs/M374-layer-wait-board-01/BOARD_RESULT.json')) { throw 'Result exists; collect only' }
if (Test-Path -LiteralPath (Join-Path $workspace 'tmp/m374/component_uart.log')) { throw 'Original run log exists; collect only' }
& $uart -Command "bash -n $remote/run_m374_staged_layer.sh" -LogPath 'tmp/m374/runner_syntax_uart.log' -TimeoutSeconds 15 -MarkerPrefix '__M374_SYNTAX_RC_'
if (-not $?) { throw 'Runner syntax failed' }
& $uart -Command 'sudo -n true' -LogPath 'tmp/m374/sudo_before_component_uart.log' -TimeoutSeconds 15 -MarkerPrefix '__M374_GATE_SUDO_RC_'
if (-not $?) { throw 'Sudo expired; no gate' }
Invoke-GateAndCollect {
    & $uart -Command "sudo -n env M374_ENABLE_STAGED_LAYER=1 bash $remote/run_m374_staged_layer.sh $digest Run B1" -LogPath 'tmp/m374/component_uart.log' -TimeoutSeconds 900 -MarkerPrefix '__M374_COMPONENT_RC_'
    if (-not $?) { throw 'Original gate/export failed; collector still required' }
} {
    & $python -X utf8 -B $workflow collect 'tmp/m374/component_uart.log'
    if ($LASTEXITCODE -ne 0) { throw 'Collector failed; recover only' }
}
Write-Output 'M374_CPU_COMPONENT_SYNCHRONIZED'
