[CmdletBinding()]
param([ValidateSet('SelfTest','Upload','Run','Collect')][string]$Mode)
$ErrorActionPreference='Stop'
Set-StrictMode -Version Latest
if ($Mode -eq 'SelfTest') {
    $tokens=$null;$errors=$null
    [void][System.Management.Automation.Language.Parser]::ParseFile($PSCommandPath,[ref]$tokens,[ref]$errors)
    if ($errors.Count) { throw 'Control syntax rejected' }
    $caught=$null;$collected=$false
    try { throw 'Intentional gate failure' } catch { $caught=$_ }
    $collected=$true
    if (-not $caught -or -not $collected) { throw 'Failure skipped collector' }
    'M424_ENV_CONTROL_SELF_TEST_PASS';exit 0
}
$workspace=(Resolve-Path (Join-Path $PSScriptRoot '../..')).Path
$relative='deployment/mage_vl4b/optimization_v1/candidates/M424-environment-probe-01'
$package=Join-Path $workspace $relative
$remote='/home/ubuntu/m424_environment_candidate_01'
$digest=(Get-FileHash -LiteralPath (Join-Path $package 'PACKAGE_MANIFEST.json') -Algorithm SHA256).Hash.ToLowerInvariant()
$manifest=Get-Content -LiteralPath (Join-Path $package 'PACKAGE_MANIFEST.json') -Raw -Encoding UTF8 | ConvertFrom-Json
$board=Get-Content -LiteralPath (Join-Path $workspace 'deployment/mage_vl4b/BOARD_GATE_RESULT.json') -Raw -Encoding UTF8 | ConvertFrom-Json
function VerifyEvidence([string]$key) {
    $e=$board.$key
    if ((Get-FileHash -LiteralPath (Join-Path $workspace $e.result) -Algorithm SHA256).Hash.ToLowerInvariant() -ne $e.sha256) { throw 'Prerequisite SHA drift' }
    foreach ($n in @('CURRENT_STATE.md','docsMILESTONES.md')) {
        if (-not (Get-Content -LiteralPath (Join-Path $workspace $n) -Raw -Encoding UTF8).Contains($e.sha256)) { throw 'Prerequisite not synchronized' }
    }
}
foreach ($key in @('latest_m424_environment_preparation','latest_m424_environment_support','latest_m423_integrated_closure','latest_m424_warm_protocol','latest_m404_sensor_board')) { VerifyEvidence $key }
$support=Get-Content -LiteralPath (Join-Path $workspace $board.latest_m424_environment_support.result) -Raw -Encoding UTF8 | ConvertFrom-Json
if ($support.manifest_sha256 -ne $digest) { throw 'Support/package identity differs' }
foreach ($p in $support.source_sha256.PSObject.Properties) {
    if ((Get-FileHash -LiteralPath (Join-Path $PSScriptRoot $p.Name) -Algorithm SHA256).Hash.ToLowerInvariant() -ne $p.Value) { throw 'Host source changed' }
}
foreach ($row in $manifest.files) {
    $p=Join-Path $package $row.path
    if ((Get-Item -LiteralPath $p).Length -ne $row.bytes -or (Get-FileHash -LiteralPath $p -Algorithm SHA256).Hash.ToLowerInvariant() -ne $row.sha256) { throw 'Payload drift' }
}
$uart=Join-Path $workspace 'scripts/m75c_uart_command.ps1'
$python='C:\Users\30429\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe'
$workflow=Join-Path $PSScriptRoot 'm424_environment_workflow.py'
if ($Mode -eq 'Upload') {
    if (Test-Path (Join-Path $workspace 'tmp/m424environment01/sudo_upload.log')) { throw 'Original auth receipt exists' }
    & $uart -Command 'sudo -n true' -LogPath 'tmp/m424environment01/sudo_upload.log' -TimeoutSeconds 15 -MarkerPrefix '__M424_ENV_SUDO_RC_'
    if (-not $?) { throw 'Sudo expired; no transfer' }
    & $uart -Command "test ! -e $remote" -LogPath 'tmp/m424environment01/absence.log' -TimeoutSeconds 15 -MarkerPrefix '__M424_ENV_ABSENT_RC_'
    if (-not $?) { throw 'Existing packet cannot be overwritten' }
    foreach ($name in (@('PACKAGE_MANIFEST.json')+@($manifest.files | ForEach-Object path))) {
        & (Join-Path $workspace 'scripts/m212_uart_put_file_chunked.ps1') -LocalPath "$relative/$name" -RemotePath "$remote/$name" -LogPrefix "tmp/m424environment01/upload_$($name.Replace('.','_'))" -ChunkBytes 900 -TimeoutSeconds 25
        if (-not $?) { throw "Transfer rejected: $name" }
        "M424_ENV_FILE_TRANSFERRED $name"
    }
    & $uart -Command "bash -n $remote/run_m424_environment.sh" -LogPath 'tmp/m424environment01/syntax.log' -TimeoutSeconds 15 -MarkerPrefix '__M424_ENV_SYNTAX_RC_'
    if (-not $?) { throw 'Runner syntax failed' }
    & $python -X utf8 -B $workflow transfer
    if ($LASTEXITCODE -ne 0) { throw 'Transfer evidence failed' };exit 0
}
if ($Mode -eq 'Collect') {
    if (Test-Path (Join-Path $workspace 'tmp/m424environment01/recollect.log')) { throw 'Original recovery log exists' }
    & $uart -Command "sudo -n env PYTHONDONTWRITEBYTECODE=1 bash $remote/run_m424_environment.sh $digest Collect" -LogPath 'tmp/m424environment01/recollect.log' -TimeoutSeconds 30 -MarkerPrefix '__M424_ENV_EXPORT_RC_'
    if (-not $?) { throw 'Saved export failed; no rerun' }
    & $python -X utf8 -B $workflow collect 'tmp/m424environment01/recollect.log'
    if ($LASTEXITCODE -ne 0) { throw 'Saved result collection failed' };exit 0
}
if ($Mode -ne 'Run') { throw 'Explicit mode required' }
VerifyEvidence 'latest_m424_environment_transfer'
if ($board.latest_m424_environment_transfer.manifest_sha256 -ne $digest) { throw 'Transfer packet differs' }
if ((Test-Path (Join-Path $workspace 'tmp/m424environment01/run.log')) -or (Test-Path (Join-Path $workspace 'deployment/mage_vl4b/optimization_v1/runs/M424-environment-board-01/BOARD_RESULT.json'))) { throw 'Original run exists; Collect only' }
& $uart -Command 'sudo -n true' -LogPath 'tmp/m424environment01/sudo_run.log' -TimeoutSeconds 15 -MarkerPrefix '__M424_ENV_SUDO_RC_'
if (-not $?) { throw 'Sudo expired; observation not started' }
$gateError=$null
try {
    & $uart -Command "sudo -n env M424_ENABLE_READONLY_ENV=1 PYTHONDONTWRITEBYTECODE=1 bash $remote/run_m424_environment.sh $digest Run" -LogPath 'tmp/m424environment01/run.log' -TimeoutSeconds 30 -MarkerPrefix '__M424_ENV_RUN_RC_'
    if (-not $?) { throw 'Observation failed' }
} catch { $gateError=$_ }
& $python -X utf8 -B $workflow collect 'tmp/m424environment01/run.log'
if ($LASTEXITCODE -ne 0) { throw 'Original result incomplete; saved recovery only' }
if ($gateError) { throw $gateError }
'M424_ENVIRONMENT_SYNCHRONIZED'
