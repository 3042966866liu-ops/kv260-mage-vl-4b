[CmdletBinding()]
param([ValidateSet('SelfTest','List','Upload','Run','Collect')][string]$Mode)
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
    try { Invoke-GateAndCollect { throw 'EXPECTED_FAIL' } { $script:collected=$true } }
    catch { if ($_.Exception.Message -ne 'EXPECTED_FAIL') { throw };$caught=$true }
    if (-not ($caught -and $script:collected)) { throw 'Failure skipped collection' }
    try { Invoke-GateAndCollect {} { throw 'EXPECTED_COLLECT_FAIL' };throw 'Ignored collection failure' }
    catch { if ($_.Exception.Message -ne 'EXPECTED_COLLECT_FAIL') { throw } }
    $tokens=$null;$errors=$null
    [void][System.Management.Automation.Language.Parser]::ParseFile($PSCommandPath,[ref]$tokens,[ref]$errors)
    if ($errors.Count) { throw 'Controller syntax rejected' }
    Write-Output 'M391_CONTROL_SELF_TEST_PASS';exit 0
}
$workspace=(Resolve-Path (Join-Path $PSScriptRoot '../..')).Path
$local='deployment/mage_vl4b/optimization_v1/candidates/M391-silu-real-input-component-01'
$remote='/home/ubuntu/m391_silu_component_candidate_01'
$package=Join-Path $workspace $local
$manifest=Get-Content -LiteralPath (Join-Path $package 'PACKAGE_MANIFEST.json') -Raw -Encoding UTF8 | ConvertFrom-Json
$digest=(Get-FileHash -LiteralPath (Join-Path $package 'PACKAGE_MANIFEST.json') -Algorithm SHA256).Hash.ToLowerInvariant()
$names=@('PACKAGE_MANIFEST.json')+@($manifest.files | ForEach-Object path)
if ($Mode -eq 'List') { ConvertTo-Json -InputObject $names -Compress;exit 0 }
$board=Get-Content -LiteralPath (Join-Path $workspace 'deployment/mage_vl4b/BOARD_GATE_RESULT.json') -Raw -Encoding UTF8 | ConvertFrom-Json
foreach ($key in @('latest_m391_silu_preparation','latest_m391_silu_support','latest_m390_capture_closure')) {
    $e=$board.$key
    if ((Get-FileHash -LiteralPath (Join-Path $workspace $e.result) -Algorithm SHA256).Hash.ToLowerInvariant() -ne $e.sha256) { throw 'Prerequisite drift' }
    foreach ($name in @('CURRENT_STATE.md','docsMILESTONES.md')) {
        if (-not (Get-Content -LiteralPath (Join-Path $workspace $name) -Raw -Encoding UTF8).Contains($e.sha256)) { throw 'Prerequisite not synchronized' }
    }
}
if ($board.latest_m391_silu_preparation.manifest_sha256 -ne $digest -or $board.latest_m391_silu_support.manifest_sha256 -ne $digest) { throw 'Manifest drift' }
$support=Get-Content -LiteralPath (Join-Path $workspace $board.latest_m391_silu_support.result) -Raw -Encoding UTF8 | ConvertFrom-Json
foreach ($p in $support.source_sha256.PSObject.Properties) {
    if ((Get-FileHash -LiteralPath (Join-Path $PSScriptRoot $p.Name) -Algorithm SHA256).Hash.ToLowerInvariant() -ne $p.Value) { throw 'Support source drift' }
}
foreach ($row in $manifest.files) {
    $p=Join-Path $package $row.path
    if ((Get-Item -LiteralPath $p).Length -ne $row.bytes -or (Get-FileHash -LiteralPath $p -Algorithm SHA256).Hash.ToLowerInvariant() -ne $row.sha256) { throw 'Payload drift' }
}
$uart=Join-Path $workspace 'scripts/m75c_uart_command.ps1'
$python='C:\Users\30429\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe'
$workflow=Join-Path $PSScriptRoot 'm391_workflow.py'
if ($Mode -eq 'Upload') {
    & $uart -Command "test ! -e $remote" -LogPath 'tmp/m391/package_absence_uart.log' -TimeoutSeconds 15 -MarkerPrefix '__M391_ABSENT_RC_'
    if (-not $?) { throw 'Existing package cannot be overwritten' }
    foreach ($name in $names) {
        & (Join-Path $workspace 'scripts/m212_uart_put_file_chunked.ps1') -LocalPath "$local/$name" -RemotePath "$remote/$name" -LogPrefix "tmp/m391/upload_$($name.Replace('.','_'))" -ChunkBytes 900 -TimeoutSeconds 25
        if (-not $?) { throw "File upload rejected: $name" }
        Write-Output "M391_FILE_TRANSFERRED $name"
    }
    & $uart -Command "sudo -n bash -n $remote/run_m391_silu.sh" -LogPath 'tmp/m391/runner_syntax_uart.log' -TimeoutSeconds 15 -MarkerPrefix '__M391_SYNTAX_RC_'
    if (-not $?) { throw 'Root syntax rejected' }
    & $python -X utf8 -B $workflow transfer
    if ($LASTEXITCODE -ne 0) { throw 'Transfer sync rejected' }
    exit 0
}
if ($Mode -eq 'Collect') {
    & $uart -Command "sudo -n env PYTHONDONTWRITEBYTECODE=1 /usr/local/share/pynq-venv/bin/python -B $remote/m391_export.py" -LogPath 'tmp/m391/recollect_uart.log' -TimeoutSeconds 180 -MarkerPrefix '__M391_EXPORT_RC_'
    if (-not $?) { throw 'Saved export rejected; no gate repeat' }
    & $python -X utf8 -B $workflow collect 'tmp/m391/recollect_uart.log'
    if ($LASTEXITCODE -ne 0) { throw 'Saved collection rejected' }
    exit 0
}
if ($Mode -ne 'Run') { throw 'Explicit mode required' }
$e=$board.latest_m391_silu_transfer
if ($e.manifest_sha256 -ne $digest -or (Get-FileHash -LiteralPath (Join-Path $workspace $e.result) -Algorithm SHA256).Hash.ToLowerInvariant() -ne $e.sha256) { throw 'Transfer drift' }
foreach ($name in @('CURRENT_STATE.md','docsMILESTONES.md')) {
    if (-not (Get-Content -LiteralPath (Join-Path $workspace $name) -Raw -Encoding UTF8).Contains($e.sha256)) { throw 'Transfer not synchronized' }
}
if ((Test-Path (Join-Path $workspace 'tmp/m391/component_uart.log')) -or (Test-Path (Join-Path $workspace 'deployment/mage_vl4b/optimization_v1/runs/M391-silu-component-board-01/BOARD_RESULT.json'))) { throw 'Original execution exists; Collect only' }
& $uart -Command 'sudo -n true' -LogPath 'tmp/m391/sudo_before_component_uart.log' -TimeoutSeconds 15 -MarkerPrefix '__M391_GATE_SUDO_RC_'
if (-not $?) { throw 'Sudo expired; no gate' }
Invoke-GateAndCollect {
    & $uart -Command "sudo -n env M391_ENABLE_COMPONENT=1 bash $remote/run_m391_silu.sh $digest Run" -LogPath 'tmp/m391/component_uart.log' -TimeoutSeconds 180 -MarkerPrefix '__M391_COMPONENT_RC_'
    if (-not $?) { throw 'Original gate/export failed; still collect' }
} {
    & $python -X utf8 -B $workflow collect 'tmp/m391/component_uart.log'
    if ($LASTEXITCODE -ne 0) { throw 'Collection failed; saved recovery only' }
}
Write-Output 'M391_COMPONENT_SYNCHRONIZED'
