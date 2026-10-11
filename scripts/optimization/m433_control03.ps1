[CmdletBinding()]
param([ValidateSet('SelfTest','Upload','Run','Collect')][string]$Mode)
$ErrorActionPreference='Stop'
Set-StrictMode -Version Latest
if ($Mode -eq 'SelfTest') {
    $tokens=$null;$errors=$null
    [void][System.Management.Automation.Language.Parser]::ParseFile($PSCommandPath,[ref]$tokens,[ref]$errors)
    if ($errors.Count) { throw 'Control syntax rejected' }
    $gateError=$null;$collected=$false
    try { throw 'Intentional gate failure' } catch { $gateError=$_ }
    $collected=$true
    if (-not $gateError -or -not $collected) { throw 'Failure skipped collection' }
    'M433_CONTROL_SELF_TEST_PASS';exit 0
}
$workspace=(Resolve-Path (Join-Path $PSScriptRoot '../..')).Path
$relative='deployment/mage_vl4b/optimization_v1/candidates/M433-late11-complete-request-warm-01'
$package=Join-Path $workspace $relative
$remote='/home/ubuntu/m433_late11_warm_candidate_01'
$manifest=Get-Content -LiteralPath (Join-Path $package 'PACKAGE_MANIFEST.json') -Raw -Encoding UTF8 | ConvertFrom-Json
$digest=(Get-FileHash -LiteralPath (Join-Path $package 'PACKAGE_MANIFEST.json') -Algorithm SHA256).Hash.ToLowerInvariant()
$board=Get-Content -LiteralPath (Join-Path $workspace 'deployment/mage_vl4b/BOARD_GATE_RESULT.json') -Raw -Encoding UTF8 | ConvertFrom-Json
function VerifyEvidence([string]$key) {
    $e=$board.$key
    if ((Get-FileHash -LiteralPath (Join-Path $workspace $e.result) -Algorithm SHA256).Hash.ToLowerInvariant() -ne $e.sha256) { throw 'Prerequisite drift' }
    foreach ($n in @('CURRENT_STATE.md','docsMILESTONES.md')) {
        if (-not (Get-Content -LiteralPath (Join-Path $workspace $n) -Raw -Encoding UTF8).Contains($e.sha256)) { throw 'Prerequisite not synchronized' }
    }
}
foreach ($key in @('latest_m432_integrated_board','latest_m432_integrated_closure','latest_m433_complete_request_protocol','latest_m433_complete_request_preparation','latest_m433_timed_provider_component','latest_m433_performance_support')) { VerifyEvidence $key }
VerifyEvidence 'latest_m433_authorization_precheck'
$recovery=Get-Content -Raw -Encoding UTF8 -LiteralPath (Join-Path $workspace $board.latest_m433_authorization_precheck.result) | ConvertFrom-Json
foreach ($p in $recovery.resume_sources.PSObject.Properties) { if ((Get-FileHash -LiteralPath (Join-Path $PSScriptRoot $p.Name) -Algorithm SHA256).Hash.ToLowerInvariant() -ne $p.Value) { throw 'Resumed authorization control changed' } }
VerifyEvidence 'latest_m433_actual_transfer_support'
$finalSupport=Get-Content -Raw -Encoding UTF8 -LiteralPath (Join-Path $workspace $board.latest_m433_actual_transfer_support.result) | ConvertFrom-Json
if ($finalSupport.manifest_sha256 -ne $digest -or -not $finalSupport.actual_assembly_pass -or -not $finalSupport.actual_transfer_pass) { throw 'Assembly/transfer support incomplete' }
foreach ($p in $finalSupport.source_sha256.PSObject.Properties) { if ((Get-FileHash -LiteralPath (Join-Path $PSScriptRoot $p.Name) -Algorithm SHA256).Hash.ToLowerInvariant() -ne $p.Value) { throw 'Final control identity changed' } }
$support=Get-Content -LiteralPath (Join-Path $workspace $board.latest_m433_performance_support.result) -Raw -Encoding UTF8 | ConvertFrom-Json
if ($support.manifest_sha256 -ne $digest) { throw 'Support/package identity differs' }
foreach ($p in $support.source_sha256.PSObject.Properties) {
    if ((Get-FileHash -LiteralPath (Join-Path $PSScriptRoot $p.Name) -Algorithm SHA256).Hash.ToLowerInvariant() -ne $p.Value) { throw 'Host control/support source changed' }
}
foreach ($row in $manifest.files) {
    $p=Join-Path $package $row.path
    if ((Get-Item -LiteralPath $p).Length -ne $row.bytes -or (Get-FileHash -LiteralPath $p -Algorithm SHA256).Hash.ToLowerInvariant() -ne $row.sha256) { throw 'Payload drift' }
}
$uart=Join-Path $workspace 'scripts/m75c_uart_command.ps1'
$python='C:\Users\30429\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe'
$workflow=Join-Path $PSScriptRoot 'm433_workflow.py'
if ($Mode -eq 'Upload') {
    if (Test-Path (Join-Path $workspace 'tmp/m43301/board/sudo_upload_resume01.log')) { throw 'Original authorization log exists' }
    & $uart -Command 'sudo -n true' -LogPath 'tmp/m43301/board/sudo_upload_resume01.log' -TimeoutSeconds 15 -MarkerPrefix '__M433_SUDO_RC_'
    if (-not $?) { throw 'Authorization required; no upload' }
    & $uart -Command "test ! -e $remote" -LogPath 'tmp/m43301/board/absence.log' -TimeoutSeconds 15 -MarkerPrefix '__M433_ABSENT_RC_'
    if (-not $?) { throw 'Existing package cannot be overwritten' }
    $old=Get-Content -LiteralPath (Join-Path $workspace 'deployment/mage_vl4b/optimization_v1/candidates/M432-late11-integrated-video-02/PACKAGE_MANIFEST.json') -Raw -Encoding UTF8 | ConvertFrom-Json
    $delta=@($manifest.files | Where-Object { $item=$_; -not @($old.files | Where-Object { $_.path -eq $item.path -and $_.sha256 -eq $item.sha256 -and $_.bytes -eq $item.bytes }).Count } | ForEach-Object path)
    foreach ($name in (@('PACKAGE_MANIFEST.json')+$delta)) {
        & (Join-Path $workspace 'scripts/m212_uart_put_file_chunked.ps1') -LocalPath "$relative/$name" -RemotePath "$remote/$name" -LogPrefix "tmp/m43301/board/upload_$($name.Replace('.','_'))" -ChunkBytes 900 -TimeoutSeconds 25
        if (-not $?) { throw "Transfer failed: $name" }
        "M433_FILE_TRANSFERRED $name"
        & $uart -Command 'sudo -n true' -LogPath "tmp/m43301/board/refresh_$($name.Replace('.','_')).log" -TimeoutSeconds 15 -MarkerPrefix '__M433_SUDO_RC_'
        if (-not $?) { throw 'Sudo expired; upload stopped' }
    }
    & $uart -Command "sudo -n /usr/local/share/pynq-venv/bin/python -B $remote/m433_assemble.py $digest" -LogPath 'tmp/m43301/board/assembly.log' -TimeoutSeconds 30 -MarkerPrefix '__M433_ASSEMBLY_RC_'
    if (-not $?) { throw 'Assembly rejected' }
    & $uart -Command "sudo -n bash -n $remote/run_m433.sh" -LogPath 'tmp/m43301/board/syntax.log' -TimeoutSeconds 15 -MarkerPrefix '__M433_SYNTAX_RC_'
    if (-not $?) { throw 'Runner syntax rejected' }
    & $python -X utf8 -B $workflow transfer
    if ($LASTEXITCODE -ne 0) { throw 'Transfer evidence rejected' };exit 0
}
if ($Mode -eq 'Collect') {
    if (Test-Path (Join-Path $workspace 'tmp/m43301/board/recollect.log')) { throw 'Saved recovery log exists' }
    & $uart -Command "sudo -n env PYTHONDONTWRITEBYTECODE=1 bash $remote/run_m433.sh $digest Collect" -LogPath 'tmp/m43301/board/recollect.log' -TimeoutSeconds 1080 -MarkerPrefix '__M433_EXPORT_RC_'
    if (-not $?) { throw 'Saved export failed; no hardware repeat' }
    & $python -X utf8 -B $workflow collect 'tmp/m43301/board/recollect.log'
    if ($LASTEXITCODE -ne 0) { throw 'Saved collection failed' };exit 0
}
if ($Mode -ne 'Run') { throw 'Explicit mode required' }
VerifyEvidence 'latest_m433_performance_transfer'
if ($board.latest_m433_performance_transfer.manifest_sha256 -ne $digest) { throw 'Transfer identity differs' }
if ((Test-Path (Join-Path $workspace 'tmp/m43301/board/run.log')) -or (Test-Path (Join-Path $workspace 'deployment/mage_vl4b/optimization_v1/runs/M433-warm-performance-board-01/BOARD_RESULT.json'))) { throw 'Original run exists; Collect only' }
& $uart -Command 'sudo -n true' -LogPath 'tmp/m43301/board/sudo_run.log' -TimeoutSeconds 15 -MarkerPrefix '__M433_SUDO_RC_'
if (-not $?) { throw 'Sudo expired; no gate execution' }
$gateError=$null
try {
    & $uart -Command "sudo -n env M433_ENABLE_INTEGRATED_VIDEO=1 PYTHONDONTWRITEBYTECODE=1 bash $remote/run_m433.sh $digest Run" -LogPath 'tmp/m43301/board/run.log' -TimeoutSeconds 4200 -MarkerPrefix '__M433_RUN_RC_'
    if (-not $?) { throw 'Saved-feature language gate/export failed' }
} catch { $gateError=$_ }
& $python -X utf8 -B $workflow collect 'tmp/m43301/board/run.log'
if ($LASTEXITCODE -ne 0) { throw 'Collection rejected; recover saved bytes only' }
if ($gateError) { throw $gateError }
'M433_INTEGRATED_NUMERICAL_SYNCHRONIZED'
