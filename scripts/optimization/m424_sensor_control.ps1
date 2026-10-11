[CmdletBinding()]
param([ValidateSet('SelfTest','Upload','Run','Collect')][string]$Mode)
$ErrorActionPreference='Stop'
Set-StrictMode -Version Latest
if ($Mode -eq 'SelfTest') {
    $tokens=$null;$errors=$null
    [void][System.Management.Automation.Language.Parser]::ParseFile($PSCommandPath,[ref]$tokens,[ref]$errors)
    if ($errors.Count) { throw 'Syntax rejected' }
    Write-Output 'M404_SENSOR_CONTROL_SYNTAX_PASS';exit 0
}
$workspace=(Resolve-Path (Join-Path $PSScriptRoot '../..')).Path
$local='deployment/mage_vl4b/optimization_v1/candidates/M404-sensor-catalogue-01'
$remote='/home/ubuntu/m404_sensor_catalogue_candidate_01'
$package=Join-Path $workspace $local
$manifest=Get-Content -LiteralPath (Join-Path $package 'PACKAGE_MANIFEST.json') -Raw -Encoding UTF8 | ConvertFrom-Json
$digest=(Get-FileHash -LiteralPath (Join-Path $package 'PACKAGE_MANIFEST.json') -Algorithm SHA256).Hash.ToLowerInvariant()
$board=Get-Content -LiteralPath (Join-Path $workspace 'deployment/mage_vl4b/BOARD_GATE_RESULT.json') -Raw -Encoding UTF8 | ConvertFrom-Json
$e=$board.latest_m424_environment_sensor_recovery
if ($e.manifest_sha256 -ne $digest -or (Get-FileHash -LiteralPath (Join-Path $workspace $e.result) -Algorithm SHA256).Hash.ToLowerInvariant() -ne $e.sha256) { throw 'Preparation/support drift' }
foreach ($n in @('CURRENT_STATE.md','docsMILESTONES.md')) {
    if (-not (Get-Content -LiteralPath (Join-Path $workspace $n) -Raw -Encoding UTF8).Contains($e.sha256)) { throw 'Prerequisite not synchronized' }
}
$support=Get-Content -LiteralPath (Join-Path $workspace $e.result) -Raw -Encoding UTF8 | ConvertFrom-Json
foreach ($p in $support.source_sha256.PSObject.Properties) {
    if ((Get-FileHash -LiteralPath (Join-Path $PSScriptRoot $p.Name) -Algorithm SHA256).Hash.ToLowerInvariant() -ne $p.Value) { throw 'Support source drift' }
}
foreach ($row in $manifest.files) {
    $p=Join-Path $package $row.path
    if ((Get-Item -LiteralPath $p).Length -ne $row.bytes -or (Get-FileHash -LiteralPath $p -Algorithm SHA256).Hash.ToLowerInvariant() -ne $row.sha256) { throw 'Payload drift' }
}
$uart=Join-Path $workspace 'scripts/m75c_uart_command.ps1'
$python='C:\Users\30429\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe'
$workflow=Join-Path $PSScriptRoot 'm424_sensor_workflow.py'
if ($Mode -eq 'Upload') {
    if (Test-Path (Join-Path $workspace 'tmp/m424sensor01/sudo_upload.log')) { throw 'Original authorization log exists' }
    & $uart -Command 'sudo -n true' -LogPath 'tmp/m424sensor01/sudo_upload.log' -TimeoutSeconds 15 -MarkerPrefix '__M404_SENSOR_SUDO_RC_'
    if (-not $?) { throw 'Authorization required; no upload' }
    & $uart -Command "test ! -e $remote" -LogPath 'tmp/m424sensor01/absence.log' -TimeoutSeconds 15 -MarkerPrefix '__M404_SENSOR_ABSENT_RC_'
    if (-not $?) { throw 'Existing observer cannot be overwritten' }
    foreach ($name in (@('PACKAGE_MANIFEST.json')+@($manifest.files | ForEach-Object path))) {
        & (Join-Path $workspace 'scripts/m212_uart_put_file_chunked.ps1') -LocalPath "$local/$name" -RemotePath "$remote/$name" -LogPrefix "tmp/m424sensor01/upload_$($name.Replace('.','_'))" -ChunkBytes 900 -TimeoutSeconds 25
        if (-not $?) { throw "Upload rejected: $name" }
        Write-Output "M404_SENSOR_FILE_TRANSFERRED $name"
    }
    & $uart -Command "bash -n $remote/run_m404_sensor.sh" -LogPath 'tmp/m424sensor01/syntax.log' -TimeoutSeconds 15 -MarkerPrefix '__M404_SENSOR_SYNTAX_RC_'
    if (-not $?) { throw 'Runner syntax rejected' }
    & $python -X utf8 -B $workflow transfer
    if ($LASTEXITCODE -ne 0) { throw 'Transfer sync rejected' }
    exit 0
}
if ($Mode -eq 'Collect') {
    & $uart -Command "sudo -n env PYTHONDONTWRITEBYTECODE=1 bash $remote/run_m404_sensor.sh $digest Collect" -LogPath 'tmp/m424sensor01/recollect.log' -TimeoutSeconds 30 -MarkerPrefix '__M404_SENSOR_EXPORT_RC_'
    if (-not $?) { throw 'Saved export rejected; no repeat' }
    & $python -X utf8 -B $workflow collect 'tmp/m424sensor01/recollect.log'
    if ($LASTEXITCODE -ne 0) { throw 'Collection rejected' };exit 0
}
if ($Mode -ne 'Run') { throw 'Explicit mode required' }
$e=$board.latest_m404_sensor_transfer
if ($e.manifest_sha256 -ne $digest -or (Get-FileHash -LiteralPath (Join-Path $workspace $e.result) -Algorithm SHA256).Hash.ToLowerInvariant() -ne $e.sha256) { throw 'Transfer evidence drift' }
foreach ($n in @('CURRENT_STATE.md','docsMILESTONES.md')) {
    if (-not (Get-Content -LiteralPath (Join-Path $workspace $n) -Raw -Encoding UTF8).Contains($e.sha256)) { throw 'Transfer not synchronized' }
}
if ((Test-Path (Join-Path $workspace 'tmp/m424sensor01/run.log')) -or (Test-Path (Join-Path $workspace 'deployment/mage_vl4b/optimization_v1/runs/M404-sensor-board-01/BOARD_RESULT.json'))) { throw 'Original observation exists; Collect only' }
& $uart -Command 'sudo -n true' -LogPath 'tmp/m424sensor01/sudo_run.log' -TimeoutSeconds 15 -MarkerPrefix '__M404_SENSOR_SUDO_RC_'
if (-not $?) { throw 'Sudo expired; observer not started' }
$gateError=$null
try {
    & $uart -Command "sudo -n env M404_ENABLE_READONLY_SENSOR=1 PYTHONDONTWRITEBYTECODE=1 bash $remote/run_m404_sensor.sh $digest Run" -LogPath 'tmp/m424sensor01/run.log' -TimeoutSeconds 30 -MarkerPrefix '__M404_SENSOR_OBSERVE_RC_'
    if (-not $?) { throw 'Observation/export failed' }
} catch { $gateError=$_ }
& $python -X utf8 -B $workflow collect 'tmp/m424sensor01/run.log'
if ($LASTEXITCODE -ne 0) { throw 'Collection failed; saved recovery only' }
if ($gateError) { throw $gateError }
Write-Output 'M404_SENSOR_CAPTURE_SYNCHRONIZED'
