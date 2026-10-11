[CmdletBinding()]
param([ValidateSet('SelfTest','Upload','Run','Collect')][string]$Mode)
$ErrorActionPreference='Stop'
Set-StrictMode -Version Latest
if ($Mode -eq 'SelfTest') {
    $tokens=$null;$errors=$null
    [void][System.Management.Automation.Language.Parser]::ParseFile($PSCommandPath,[ref]$tokens,[ref]$errors)
    if ($errors.Count) { throw 'Syntax rejected' }
    $gateError=$null
    try { throw 'Intentional gate failure' } catch { $gateError=$_ }
    $collected=$true
    if (-not $collected -or -not $gateError) { throw 'Failure collection rejected' }
    Write-Output 'M416_CONTROL_SELF_TEST_PASS';exit 0
}
$workspace=(Resolve-Path (Join-Path $PSScriptRoot '../..')).Path
$local='deployment/mage_vl4b/optimization_v1/candidates/M416-layer13-PS-capture-01'
$remote='/home/ubuntu/m416_layer13_candidate_01'
$package=Join-Path $workspace $local
$manifest=Get-Content -LiteralPath (Join-Path $package 'PACKAGE_MANIFEST.json') -Raw -Encoding UTF8 | ConvertFrom-Json
$digest=(Get-FileHash -LiteralPath (Join-Path $package 'PACKAGE_MANIFEST.json') -Algorithm SHA256).Hash.ToLowerInvariant()
$board=Get-Content -LiteralPath (Join-Path $workspace 'deployment/mage_vl4b/BOARD_GATE_RESULT.json') -Raw -Encoding UTF8 | ConvertFrom-Json
$auth=$board.latest_m416_local_mlp_authorization_precheck
if ((Get-FileHash -LiteralPath (Join-Path $workspace $auth.result) -Algorithm SHA256).Hash.ToLowerInvariant() -ne $auth.sha256) { throw 'Authorization evidence drift' }
if ((Get-FileHash -LiteralPath $PSCommandPath -Algorithm SHA256).Hash.ToLowerInvariant() -ne $auth.controller02_sha256) { throw 'Recovery control identity drift' }
foreach ($n in @('CURRENT_STATE.md','docsMILESTONES.md')) {
    if (-not (Get-Content -LiteralPath (Join-Path $workspace $n) -Raw -Encoding UTF8).Contains($auth.sha256)) { throw 'Authorization evidence not synchronized' }
}
foreach ($key in @('latest_m416_bounded_expansion_plan','latest_m415_saved_feature_language_closure','latest_m416_local_mlp_preparation04','latest_m416_local_mlp_support04')) {
    $e=$board.$key
    if ((Get-FileHash -LiteralPath (Join-Path $workspace $e.result) -Algorithm SHA256).Hash.ToLowerInvariant() -ne $e.sha256) { throw 'Prerequisite drift' }
    foreach ($n in @('CURRENT_STATE.md','docsMILESTONES.md')) {
        if (-not (Get-Content -LiteralPath (Join-Path $workspace $n) -Raw -Encoding UTF8).Contains($e.sha256)) { throw 'Prerequisite not synchronized' }
    }
}
$support=Get-Content -LiteralPath (Join-Path $workspace $board.latest_m416_local_mlp_support04.result) -Raw -Encoding UTF8 | ConvertFrom-Json
if ($support.manifest_sha256 -ne $digest) { throw 'Support package drift' }
foreach ($p in $support.source_sha256.PSObject.Properties) {
    if ((Get-FileHash -LiteralPath (Join-Path $PSScriptRoot $p.Name) -Algorithm SHA256).Hash.ToLowerInvariant() -ne $p.Value) { throw 'Host source drift' }
}
foreach ($row in $manifest.files) {
    $p=Join-Path $package $row.path
    if ((Get-Item -LiteralPath $p).Length -ne $row.bytes -or (Get-FileHash -LiteralPath $p -Algorithm SHA256).Hash.ToLowerInvariant() -ne $row.sha256) { throw 'Payload drift' }
}
$uart=Join-Path $workspace 'scripts/m75c_uart_command.ps1'
$python='C:\Users\30429\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe'
$workflow=Join-Path $PSScriptRoot 'm416_workflow.py'
if ($Mode -eq 'Upload') {
    if (Test-Path (Join-Path $workspace 'tmp/m41601/sudo_upload02.log')) { throw 'Authorization log exists; preserve original' }
    & $uart -Command 'sudo -n true' -LogPath 'tmp/m41601/sudo_upload02.log' -TimeoutSeconds 15 -MarkerPrefix '__M416_SUDO_RC_'
    if (-not $?) { throw 'Authorization required; no upload' }
    & $uart -Command "test ! -e $remote" -LogPath 'tmp/m41601/absence.log' -TimeoutSeconds 15 -MarkerPrefix '__M416_ABSENT_RC_'
    if (-not $?) { throw 'Existing package cannot be overwritten' }
    foreach ($name in (@('PACKAGE_MANIFEST.json')+@($manifest.files | ForEach-Object path))) {
        & (Join-Path $workspace 'scripts/m212_uart_put_file_chunked.ps1') -LocalPath "$local/$name" -RemotePath "$remote/$name" -LogPrefix "tmp/m41601/upload_$($name.Replace('.','_'))" -ChunkBytes 900 -TimeoutSeconds 25
        if (-not $?) { throw "Upload rejected: $name" }
        Write-Output "M416_FILE_TRANSFERRED $name"
    }
    & $uart -Command "sudo -n bash -n $remote/run_m416_capture.sh" -LogPath 'tmp/m41601/syntax.log' -TimeoutSeconds 15 -MarkerPrefix '__M416_SYNTAX_RC_'
    if (-not $?) { throw 'Runner syntax rejected' }
    & $python -X utf8 -B $workflow transfer
    if ($LASTEXITCODE -ne 0) { throw 'Transfer sync rejected' };exit 0
}
if ($Mode -eq 'Collect') {
    & $uart -Command "sudo -n env PYTHONDONTWRITEBYTECODE=1 bash $remote/run_m416_capture.sh $digest Collect" -LogPath 'tmp/m41601/recollect.log' -TimeoutSeconds 180 -MarkerPrefix '__M416_EXPORT_RC_'
    if (-not $?) { throw 'Saved export rejected; no repeat' }
    & $python -X utf8 -B $workflow collect 'tmp/m41601/recollect.log'
    if ($LASTEXITCODE -ne 0) { throw 'Collection rejected' };exit 0
}
if ($Mode -ne 'Run') { throw 'Explicit mode required' }
$e=$board.latest_m416_local_mlp_transfer04
if ($e.manifest_sha256 -ne $digest -or (Get-FileHash -LiteralPath (Join-Path $workspace $e.result) -Algorithm SHA256).Hash.ToLowerInvariant() -ne $e.sha256) { throw 'Transfer drift' }
foreach ($n in @('CURRENT_STATE.md','docsMILESTONES.md')) {
    if (-not (Get-Content -LiteralPath (Join-Path $workspace $n) -Raw -Encoding UTF8).Contains($e.sha256)) { throw 'Transfer not synchronized' }
}
if ((Test-Path (Join-Path $workspace 'tmp/m41601/run.log')) -or (Test-Path (Join-Path $workspace 'deployment/mage_vl4b/optimization_v1/runs/M416-layer13-PS-board-01/BOARD_RESULT.json'))) { throw 'Original run exists; Collect only' }
& $uart -Command 'sudo -n true' -LogPath 'tmp/m41601/sudo_run.log' -TimeoutSeconds 15 -MarkerPrefix '__M416_SUDO_RC_'
if (-not $?) { throw 'Sudo expired; screen not started' }
$gateError=$null
try {
    & $uart -Command "sudo -n env M416_ENABLE_LOCAL_MLP=1 PYTHONDONTWRITEBYTECODE=1 bash $remote/run_m416_capture.sh $digest Run" -LogPath 'tmp/m41601/run.log' -TimeoutSeconds 780 -MarkerPrefix '__M416_RUN_RC_'
    if (-not $?) { throw 'Screen/export failed' }
} catch { $gateError=$_ }
& $python -X utf8 -B $workflow collect 'tmp/m41601/run.log'
if ($LASTEXITCODE -ne 0) { throw 'Collection failed; recover saved bytes only' }
if ($gateError) { throw $gateError }
Write-Output 'M416_CAPTURE_SYNCHRONIZED'
