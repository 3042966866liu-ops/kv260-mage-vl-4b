[CmdletBinding()]
param([ValidateSet('SelfTest','Upload','Run','Collect')][string]$Mode)
$ErrorActionPreference='Stop'
Set-StrictMode -Version Latest
if ($Mode -eq 'SelfTest') {
    $tokens=$null;$errors=$null
    [void][System.Management.Automation.Language.Parser]::ParseFile($PSCommandPath,[ref]$tokens,[ref]$errors)
    if ($errors.Count) { throw 'Syntax rejected' }
    $captured=$null;$collected=$false
    try { throw 'Intentional gate failure' } catch { $captured=$_ }
    $collected=$true
    if (-not $collected -or -not $captured) { throw 'Failure collection control rejected' }
    Write-Output 'M406_CONTROL_SELF_TEST_PASS';exit 0
}
$workspace=(Resolve-Path (Join-Path $PSScriptRoot '../..')).Path
$local='deployment/mage_vl4b/optimization_v1/candidates/M406-vision-cost-observer-02'
$remote='/home/ubuntu/m406_vision_cost_candidate_02'
$package=Join-Path $workspace $local
$manifest=Get-Content -LiteralPath (Join-Path $package 'PACKAGE_MANIFEST.json') -Raw -Encoding UTF8 | ConvertFrom-Json
$digest=(Get-FileHash -LiteralPath (Join-Path $package 'PACKAGE_MANIFEST.json') -Algorithm SHA256).Hash.ToLowerInvariant()
$board=Get-Content -LiteralPath (Join-Path $workspace 'deployment/mage_vl4b/BOARD_GATE_RESULT.json') -Raw -Encoding UTF8 | ConvertFrom-Json
$e=$board.latest_m406_vision_support
if ($e.manifest_sha256 -ne $digest -or (Get-FileHash -LiteralPath (Join-Path $workspace $e.result) -Algorithm SHA256).Hash.ToLowerInvariant() -ne $e.sha256) { throw 'Support drift' }
foreach ($n in @('CURRENT_STATE.md','docsMILESTONES.md')) {
    if (-not (Get-Content -LiteralPath (Join-Path $workspace $n) -Raw -Encoding UTF8).Contains($e.sha256)) { throw 'Support not synchronized' }
}
$support=Get-Content -LiteralPath (Join-Path $workspace $e.result) -Raw -Encoding UTF8 | ConvertFrom-Json
foreach ($p in $support.source_sha256.PSObject.Properties) {
    if ((Get-FileHash -LiteralPath (Join-Path $PSScriptRoot $p.Name) -Algorithm SHA256).Hash.ToLowerInvariant() -ne $p.Value) { throw 'Host source drift' }
}
foreach ($row in $manifest.files) {
    $p=Join-Path $package $row.path
    if ((Get-Item -LiteralPath $p).Length -ne $row.bytes -or (Get-FileHash -LiteralPath $p -Algorithm SHA256).Hash.ToLowerInvariant() -ne $row.sha256) { throw 'Payload drift' }
}
$uart=Join-Path $workspace 'scripts/m75c_uart_command.ps1'
$python='C:\Users\30429\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe'
$workflow=Join-Path $PSScriptRoot 'm406_workflow02.py'
if ($Mode -eq 'Upload') {
    & $uart -Command 'sudo -n true' -LogPath 'tmp/m40602/sudo_upload_03.log' -TimeoutSeconds 15 -MarkerPrefix '__M406_SUDO_RC_'
    if (-not $?) { throw 'Authorization required; no upload' }
    & $uart -Command "test ! -e $remote" -LogPath 'tmp/m40602/absence.log' -TimeoutSeconds 15 -MarkerPrefix '__M406_ABSENT_RC_'
    if (-not $?) { throw 'Existing observer cannot be overwritten' }
    foreach ($name in (@('PACKAGE_MANIFEST.json')+@($manifest.files | ForEach-Object path))) {
        & (Join-Path $workspace 'scripts/m212_uart_put_file_chunked.ps1') -LocalPath "$local/$name" -RemotePath "$remote/$name" -LogPrefix "tmp/m40602/upload_$($name.Replace('.','_'))" -ChunkBytes 900 -TimeoutSeconds 25
        if (-not $?) { throw "Upload rejected: $name" }
        Write-Output "M406_FILE_TRANSFERRED $name"
    }
    & $uart -Command "sudo -n bash -n $remote/run_m406_vision.sh" -LogPath 'tmp/m40602/syntax.log' -TimeoutSeconds 15 -MarkerPrefix '__M406_SYNTAX_RC_'
    if (-not $?) { throw 'Runner syntax rejected' }
    & $python -X utf8 -B $workflow transfer
    if ($LASTEXITCODE -ne 0) { throw 'Transfer sync rejected' };exit 0
}
if ($Mode -eq 'Collect') {
    & $uart -Command "sudo -n env PYTHONDONTWRITEBYTECODE=1 bash $remote/run_m406_vision.sh $digest Collect" -LogPath 'tmp/m40602/recollect.log' -TimeoutSeconds 180 -MarkerPrefix '__M406_EXPORT_RC_'
    if (-not $?) { throw 'Saved export rejected; no repeat' }
    & $python -X utf8 -B $workflow collect 'tmp/m40602/recollect.log'
    if ($LASTEXITCODE -ne 0) { throw 'Collection rejected' };exit 0
}
if ($Mode -ne 'Run') { throw 'Explicit mode required' }
$e=$board.latest_m406_vision_transfer
if ($e.manifest_sha256 -ne $digest -or (Get-FileHash -LiteralPath (Join-Path $workspace $e.result) -Algorithm SHA256).Hash.ToLowerInvariant() -ne $e.sha256) { throw 'Transfer drift' }
foreach ($n in @('CURRENT_STATE.md','docsMILESTONES.md')) {
    if (-not (Get-Content -LiteralPath (Join-Path $workspace $n) -Raw -Encoding UTF8).Contains($e.sha256)) { throw 'Transfer not synchronized' }
}
if ((Test-Path (Join-Path $workspace 'tmp/m40602/run.log')) -or (Test-Path (Join-Path $workspace 'deployment/mage_vl4b/optimization_v1/runs/M406-vision-cost-board-02/BOARD_RESULT.json'))) { throw 'Original observation exists; Collect only' }
& $uart -Command 'sudo -n true' -LogPath 'tmp/m40602/sudo_run.log' -TimeoutSeconds 15 -MarkerPrefix '__M406_SUDO_RC_'
if (-not $?) { throw 'Sudo expired; observation not started' }
$gateError=$null
try {
    & $uart -Command "sudo -n env M406_ENABLE_PS_VISION=1 PYTHONDONTWRITEBYTECODE=1 bash $remote/run_m406_vision.sh $digest Run" -LogPath 'tmp/m40602/run.log' -TimeoutSeconds 780 -MarkerPrefix '__M406_RUN_RC_'
    if (-not $?) { throw 'Observation/export failed' }
} catch { $gateError=$_ }
& $python -X utf8 -B $workflow collect 'tmp/m40602/run.log'
if ($LASTEXITCODE -ne 0) { throw 'Collection failed; recover saved bytes only' }
if ($gateError) { throw $gateError }
Write-Output 'M406_CAPTURE_SYNCHRONIZED'
