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
    'M430_CONTROL_SELF_TEST_PASS';exit 0
}
$workspace=(Resolve-Path (Join-Path $PSScriptRoot '../..')).Path
$relative='deployment/mage_vl4b/optimization_v1/candidates/M430-late11-visual-warm-02'
$package=Join-Path $workspace $relative
$remote='/home/ubuntu/m430_late11_visual_warm_candidate_02'
$digest=(Get-FileHash -LiteralPath (Join-Path $package 'PACKAGE_MANIFEST.json') -Algorithm SHA256).Hash.ToLowerInvariant()
$manifest=Get-Content -LiteralPath (Join-Path $package 'PACKAGE_MANIFEST.json') -Raw -Encoding UTF8 | ConvertFrom-Json
$board=Get-Content -LiteralPath (Join-Path $workspace 'deployment/mage_vl4b/BOARD_GATE_RESULT.json') -Raw -Encoding UTF8 | ConvertFrom-Json
function VerifyEvidence([string]$key) {
    $e=$board.$key
    if ((Get-FileHash -LiteralPath (Join-Path $workspace $e.result) -Algorithm SHA256).Hash.ToLowerInvariant() -ne $e.sha256) { throw 'Prerequisite drift' }
    foreach ($n in @('CURRENT_STATE.md','docsMILESTONES.md')) {
        if (-not (Get-Content -LiteralPath (Join-Path $workspace $n) -Raw -Encoding UTF8).Contains($e.sha256)) { throw 'Prerequisite not synchronized' }
    }
}
foreach ($key in @('latest_m429_late11_visual_numerical_closure','latest_m430_complete_visual_protocol','latest_m430_timed_scope_component','latest_m430_complete_visual_packet','latest_m430_complete_visual_support')) { VerifyEvidence $key }
$support=Get-Content -LiteralPath (Join-Path $workspace $board.latest_m430_complete_visual_support.result) -Raw -Encoding UTF8 | ConvertFrom-Json
if ($support.manifest_sha256 -ne $digest) { throw 'Support/package differs' }
foreach ($p in $support.source_sha256.PSObject.Properties) {
    if ((Get-FileHash -LiteralPath (Join-Path $PSScriptRoot $p.Name) -Algorithm SHA256).Hash.ToLowerInvariant() -ne $p.Value) { throw 'Host control/support source changed' }
}
foreach ($row in $manifest.files) {
    $p=Join-Path $package $row.path
    if ((Get-Item -LiteralPath $p).Length -ne $row.bytes -or (Get-FileHash -LiteralPath $p -Algorithm SHA256).Hash.ToLowerInvariant() -ne $row.sha256) { throw 'Payload drift' }
}
$uart=Join-Path $workspace 'scripts/m75c_uart_command.ps1'
$python='C:\Users\30429\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe'
$workflow=Join-Path $PSScriptRoot 'm430_workflow.py'
if ($Mode -eq 'Upload') {
    if (Test-Path (Join-Path $workspace 'tmp/m43002/sudo_upload.log')) { throw 'Original authorization log exists' }
    & $uart -Command 'sudo -n true' -LogPath 'tmp/m43002/sudo_upload.log' -TimeoutSeconds 15 -MarkerPrefix '__M430_SUDO_RC_'
    if (-not $?) { throw 'Authorization required; no upload' }
    & $uart -Command "test ! -e $remote" -LogPath 'tmp/m43002/absence.log' -TimeoutSeconds 15 -MarkerPrefix '__M430_ABSENT_RC_'
    if (-not $?) { throw 'Existing packet cannot be overwritten' }
    foreach ($name in (@('PACKAGE_MANIFEST.json')+@($manifest.files | ForEach-Object path))) {
        & (Join-Path $workspace 'scripts/m212_uart_put_file_chunked.ps1') -LocalPath "$relative/$name" -RemotePath "$remote/$name" -LogPrefix "tmp/m43002/upload_$($name.Replace('.','_'))" -ChunkBytes 900 -TimeoutSeconds 25
        if (-not $?) { throw "Transfer failed: $name" }
        "M430_FILE_TRANSFERRED $name"
        & $uart -Command 'sudo -n true' -LogPath "tmp/m43002/refresh_$($name.Replace('.','_')).log" -TimeoutSeconds 15 -MarkerPrefix '__M430_SUDO_RC_'
        if (-not $?) { throw 'Sudo expired; upload stopped' }
    }
    & $uart -Command "sudo -n bash -n $remote/run_m430.sh" -LogPath 'tmp/m43002/syntax.log' -TimeoutSeconds 15 -MarkerPrefix '__M430_SYNTAX_RC_'
    if (-not $?) { throw 'Runner syntax rejected' }
    & $python -X utf8 -B $workflow transfer
    if ($LASTEXITCODE -ne 0) { throw 'Transfer evidence rejected' };exit 0
}
if ($Mode -eq 'Collect') {
    if (Test-Path (Join-Path $workspace 'tmp/m43002/recollect.log')) { throw 'Original recovery log exists' }
    & $uart -Command "sudo -n env PYTHONDONTWRITEBYTECODE=1 bash $remote/run_m430.sh $digest Collect" -LogPath 'tmp/m43002/recollect.log' -TimeoutSeconds 900 -MarkerPrefix '__M430_EXPORT_RC_'
    if (-not $?) { throw 'Saved export failed; no model repeat' }
    & $python -X utf8 -B $workflow collect 'tmp/m43002/recollect.log'
    if ($LASTEXITCODE -ne 0) { throw 'Saved collection failed' };exit 0
}
VerifyEvidence 'latest_m429_isolated_bootstrap_board'
if (-not $board.latest_m429_isolated_bootstrap_board.CPU_bootstrap_pass) { throw 'CPU bootstrap unresolved' }
if ($Mode -ne 'Run') { throw 'Explicit mode required' }
VerifyEvidence 'latest_m430_complete_visual_transfer'
if ($board.latest_m430_complete_visual_transfer.manifest_sha256 -ne $digest) { throw 'Transfer identity differs' }
if ((Test-Path (Join-Path $workspace 'tmp/m43002/run.log')) -or (Test-Path (Join-Path $workspace 'deployment/mage_vl4b/optimization_v1/runs/M430-complete-visual-warm-board-01/BOARD_RESULT.json'))) { throw 'Original run exists; Collect only' }
& $uart -Command 'sudo -n true' -LogPath 'tmp/m43002/sudo_run.log' -TimeoutSeconds 15 -MarkerPrefix '__M430_SUDO_RC_'
if (-not $?) { throw 'Sudo expired; no execution' }
$gateError=$null
try {
    & $uart -Command "sudo -n env M430_ENABLE_VISUAL_PERFORMANCE=1 PYTHONDONTWRITEBYTECODE=1 bash $remote/run_m430.sh $digest Run" -LogPath 'tmp/m43002/run.log' -TimeoutSeconds 2400 -MarkerPrefix '__M430_RUN_RC_'
    if (-not $?) { throw 'Visual PL numerical gate/export failed' }
} catch { $gateError=$_ }
& $python -X utf8 -B $workflow collect 'tmp/m43002/run.log'
if ($LASTEXITCODE -ne 0) { throw 'Collection rejected; recover saved bytes only' }
if ($gateError) { throw $gateError }
'M430_VISUAL_PL_NUMERICAL_SYNCHRONIZED'
