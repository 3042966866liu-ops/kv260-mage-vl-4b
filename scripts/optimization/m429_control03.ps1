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
    'M429_CONTROL_SELF_TEST_PASS';exit 0
}
$workspace=(Resolve-Path (Join-Path $PSScriptRoot '../..')).Path
$relative='deployment/mage_vl4b/optimization_v1/candidates/M429-late11-visual-PL-numeric-02'
$package=Join-Path $workspace $relative
$remote='/home/ubuntu/m429_late11_visual_candidate_02'
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
foreach ($key in @('latest_m427_half_closure','latest_m428_saved_language_closure','latest_m429_streamed_scope_component','latest_m429_final_packet','latest_m429_numeric_support')) { VerifyEvidence $key }
$support=Get-Content -LiteralPath (Join-Path $workspace $board.latest_m429_numeric_support.result) -Raw -Encoding UTF8 | ConvertFrom-Json
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
$workflow=Join-Path $PSScriptRoot 'm429_workflow03.py'
VerifyEvidence 'latest_m429_authorization_precheck'
$auth=Get-Content -LiteralPath (Join-Path $workspace $board.latest_m429_authorization_precheck.result) -Raw -Encoding UTF8 | ConvertFrom-Json
foreach ($p in $auth.resume_source_sha256.PSObject.Properties) {
    if ((Get-FileHash -LiteralPath (Join-Path $PSScriptRoot $p.Name) -Algorithm SHA256).Hash.ToLowerInvariant() -ne $p.Value) { throw 'Resume source changed' }
}
if ($Mode -eq 'Upload') {
    if (Test-Path (Join-Path $workspace 'tmp/m42903/sudo_upload.log')) { throw 'Original authorization log exists' }
    & $uart -Command 'sudo -n true' -LogPath 'tmp/m42903/sudo_upload.log' -TimeoutSeconds 15 -MarkerPrefix '__M429_SUDO_RC_'
    if (-not $?) { throw 'Authorization required; no upload' }
    & $uart -Command "test ! -e $remote" -LogPath 'tmp/m42903/absence.log' -TimeoutSeconds 15 -MarkerPrefix '__M429_ABSENT_RC_'
    if (-not $?) { throw 'Existing packet cannot be overwritten' }
    foreach ($name in (@('PACKAGE_MANIFEST.json')+@($manifest.files | ForEach-Object path))) {
        & (Join-Path $workspace 'scripts/m212_uart_put_file_chunked.ps1') -LocalPath "$relative/$name" -RemotePath "$remote/$name" -LogPrefix "tmp/m42903/upload_$($name.Replace('.','_'))" -ChunkBytes 900 -TimeoutSeconds 25
        if (-not $?) { throw "Transfer failed: $name" }
        "M429_FILE_TRANSFERRED $name"
        & $uart -Command 'sudo -n true' -LogPath "tmp/m42903/refresh_$($name.Replace('.','_')).log" -TimeoutSeconds 15 -MarkerPrefix '__M429_SUDO_RC_'
        if (-not $?) { throw 'Sudo expired; upload stopped' }
    }
    & $uart -Command "sudo -n bash -n $remote/run_m429.sh" -LogPath 'tmp/m42903/syntax.log' -TimeoutSeconds 15 -MarkerPrefix '__M429_SYNTAX_RC_'
    if (-not $?) { throw 'Runner syntax rejected' }
    & $python -X utf8 -B $workflow transfer
    if ($LASTEXITCODE -ne 0) { throw 'Transfer evidence rejected' };exit 0
}
if ($Mode -eq 'Collect') {
    if (Test-Path (Join-Path $workspace 'tmp/m42903/recollect.log')) { throw 'Original recovery log exists' }
    & $uart -Command "sudo -n env PYTHONDONTWRITEBYTECODE=1 bash $remote/run_m429.sh $digest Collect" -LogPath 'tmp/m42903/recollect.log' -TimeoutSeconds 900 -MarkerPrefix '__M429_EXPORT_RC_'
    if (-not $?) { throw 'Saved export failed; no model repeat' }
    & $python -X utf8 -B $workflow collect 'tmp/m42903/recollect.log'
    if ($LASTEXITCODE -ne 0) { throw 'Saved collection failed' };exit 0
}
if ($Mode -ne 'Run') { throw 'Explicit mode required' }
VerifyEvidence 'latest_m429_late11_visual_transfer'
if ($board.latest_m429_late11_visual_transfer.manifest_sha256 -ne $digest) { throw 'Transfer identity differs' }
if ((Test-Path (Join-Path $workspace 'tmp/m42903/run.log')) -or (Test-Path (Join-Path $workspace 'deployment/mage_vl4b/optimization_v1/runs/M429-late11-visual-PL-board-01/BOARD_RESULT.json'))) { throw 'Original run exists; Collect only' }
& $uart -Command 'sudo -n true' -LogPath 'tmp/m42903/sudo_run.log' -TimeoutSeconds 15 -MarkerPrefix '__M429_SUDO_RC_'
if (-not $?) { throw 'Sudo expired; no execution' }
$gateError=$null
try {
    & $uart -Command "sudo -n env M429_ENABLE_PL_NUMERICAL=1 PYTHONDONTWRITEBYTECODE=1 bash $remote/run_m429.sh $digest Run" -LogPath 'tmp/m42903/run.log' -TimeoutSeconds 1800 -MarkerPrefix '__M429_RUN_RC_'
    if (-not $?) { throw 'Visual PL numerical gate/export failed' }
} catch { $gateError=$_ }
& $python -X utf8 -B $workflow collect 'tmp/m42903/run.log'
if ($LASTEXITCODE -ne 0) { throw 'Collection rejected; recover saved bytes only' }
if ($gateError) { throw $gateError }
'M429_VISUAL_PL_NUMERICAL_SYNCHRONIZED'
