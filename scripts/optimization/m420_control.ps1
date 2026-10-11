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
    Write-Output 'M420_CONTROL_SELF_TEST_PASS';exit 0
}
$workspace=(Resolve-Path (Join-Path $PSScriptRoot '../..')).Path
$local='deployment/mage_vl4b/optimization_v1/candidates/M420-layers12-13-full-visual-02'
$remote='/home/ubuntu/m420_combination_visual_candidate_02'
$package=Join-Path $workspace $local
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
foreach ($key in @('latest_m419_complete_mlp_board03','latest_m419_complete_mlp_closure03','latest_m414_layer12_visual_closure','latest_m415_saved_feature_language_closure','latest_m420_combination_plan','latest_m420_combination_preparation02','latest_m420_combination_support')) { VerifyEvidence $key }
$support=Get-Content -LiteralPath (Join-Path $workspace $board.latest_m420_combination_support.result) -Raw -Encoding UTF8 | ConvertFrom-Json
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
$workflow=Join-Path $PSScriptRoot 'm420_workflow02.py'
if ($Mode -eq 'Upload') {
    if (Test-Path (Join-Path $workspace 'tmp/m42001/sudo_upload.log')) { throw 'Authorization log exists; preserve original' }
    & $uart -Command 'sudo -n true' -LogPath 'tmp/m42001/sudo_upload.log' -TimeoutSeconds 15 -MarkerPrefix '__M420_SUDO_RC_'
    if (-not $?) { throw 'Authorization required; no upload' }
    & $uart -Command "test ! -e $remote" -LogPath 'tmp/m42001/absence.log' -TimeoutSeconds 15 -MarkerPrefix '__M420_ABSENT_RC_'
    if (-not $?) { throw 'Existing package cannot be overwritten' }
    foreach ($name in (@('PACKAGE_MANIFEST.json')+@($manifest.files | ForEach-Object path))) {
        & (Join-Path $workspace 'scripts/m212_uart_put_file_chunked.ps1') -LocalPath "$local/$name" -RemotePath "$remote/$name" -LogPrefix "tmp/m42001/upload_$($name.Replace('.','_'))" -ChunkBytes 900 -TimeoutSeconds 25
        if (-not $?) { throw "Upload rejected: $name" }
        Write-Output "M420_FILE_TRANSFERRED $name"
        & $uart -Command 'sudo -n true' -LogPath "tmp/m42001/sudo_transfer_$($name.Replace('.','_')).log" -TimeoutSeconds 15 -MarkerPrefix '__M420_SUDO_RC_'
        if (-not $?) { throw 'Sudo expired; stop transfer without retry' }
    }
    & $uart -Command "sudo -n bash -n $remote/run_m420_mlp.sh" -LogPath 'tmp/m42001/syntax.log' -TimeoutSeconds 15 -MarkerPrefix '__M420_SYNTAX_RC_'
    if (-not $?) { throw 'Runner syntax rejected' }
    & $python -X utf8 -B $workflow transfer
    if ($LASTEXITCODE -ne 0) { throw 'Transfer sync rejected' };exit 0
}
if ($Mode -eq 'Collect') {
    if (Test-Path (Join-Path $workspace 'tmp/m42001/recollect.log')) { throw 'Existing saved export log preserved' }
    & $uart -Command "sudo -n env PYTHONDONTWRITEBYTECODE=1 bash $remote/run_m420_mlp.sh $digest Collect" -LogPath 'tmp/m42001/recollect.log' -TimeoutSeconds 240 -MarkerPrefix '__M420_EXPORT_RC_'
    if (-not $?) { throw 'Saved export rejected; no repeat' }
    & $python -X utf8 -B $workflow collect 'tmp/m42001/recollect.log'
    if ($LASTEXITCODE -ne 0) { throw 'Collection rejected' };exit 0
}
if ($Mode -ne 'Run') { throw 'Explicit mode required' }
VerifyEvidence 'latest_m420_combination_transfer'
if ($board.latest_m420_combination_transfer.manifest_sha256 -ne $digest) { throw 'Transfer drift' }
if ((Test-Path (Join-Path $workspace 'tmp/m42001/run.log')) -or (Test-Path (Join-Path $workspace 'deployment/mage_vl4b/optimization_v1/runs/M420-combination-board-01/BOARD_RESULT.json'))) { throw 'Original run exists; Collect only' }
& $uart -Command 'sudo -n true' -LogPath 'tmp/m42001/sudo_run.log' -TimeoutSeconds 15 -MarkerPrefix '__M420_SUDO_RC_'
if (-not $?) { throw 'Sudo expired; complete MLP not started' }
$gateError=$null
try {
    & $uart -Command "sudo -n env M420_ENABLE_MLP=1 PYTHONDONTWRITEBYTECODE=1 bash $remote/run_m420_mlp.sh $digest Run" -LogPath 'tmp/m42001/run.log' -TimeoutSeconds 1080 -MarkerPrefix '__M420_RUN_RC_'
    if (-not $?) { throw 'MLP gate/export failed' }
} catch { $gateError=$_ }
& $python -X utf8 -B $workflow collect 'tmp/m42001/run.log'
if ($LASTEXITCODE -ne 0) { throw 'Collection failed; recover saved bytes only' }
if ($gateError) { throw $gateError }
Write-Output 'M420_COMPLETE_MLP_SYNCHRONIZED'
