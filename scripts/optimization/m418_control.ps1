[CmdletBinding()]
param([ValidateSet('SelfTest','Upload','Descriptor','Chain','Collect')][string]$Mode,[ValidateSet('Descriptor','Chain')][string]$Gate='Descriptor')
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
    Write-Output 'M418_CONTROL_SELF_TEST_PASS';exit 0
}
$workspace=(Resolve-Path (Join-Path $PSScriptRoot '../..')).Path
$local='deployment/mage_vl4b/optimization_v1/candidates/M418-visual-linear-01'
$remote='/home/ubuntu/m418_visual_linear_candidate_01'
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
foreach ($key in @('latest_m407_visual_mlp_contract','latest_m407_visual_mlp_layout_closure','latest_m417_reference_board','latest_m417_reference_closure','latest_m418_visual_linear_preparation','latest_m418_visual_linear_support')) { VerifyEvidence $key }
$support=Get-Content -LiteralPath (Join-Path $workspace $board.latest_m418_visual_linear_support.result) -Raw -Encoding UTF8 | ConvertFrom-Json
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
$workflow=Join-Path $PSScriptRoot 'm418_workflow.py'
if ($Mode -eq 'Upload') {
    if (Test-Path (Join-Path $workspace 'tmp/m41801/sudo_upload.log')) { throw 'Authorization log exists; preserve original' }
    & $uart -Command 'sudo -n true' -LogPath 'tmp/m41801/sudo_upload.log' -TimeoutSeconds 15 -MarkerPrefix '__M418_SUDO_RC_'
    if (-not $?) { throw 'Authorization required; no upload' }
    & $uart -Command "test ! -e $remote" -LogPath 'tmp/m41801/absence.log' -TimeoutSeconds 15 -MarkerPrefix '__M418_ABSENT_RC_'
    if (-not $?) { throw 'Existing package cannot be overwritten' }
    foreach ($name in (@('PACKAGE_MANIFEST.json')+@($manifest.files | ForEach-Object path))) {
        & (Join-Path $workspace 'scripts/m212_uart_put_file_chunked.ps1') -LocalPath "$local/$name" -RemotePath "$remote/$name" -LogPrefix "tmp/m41801/upload_$($name.Replace('.','_'))" -ChunkBytes 900 -TimeoutSeconds 25
        if (-not $?) { throw "Upload rejected: $name" }
        Write-Output "M418_FILE_TRANSFERRED $name"
        & $uart -Command 'sudo -n true' -LogPath "tmp/m41801/sudo_transfer_$($name.Replace('.','_')).log" -TimeoutSeconds 15 -MarkerPrefix '__M418_SUDO_RC_'
        if (-not $?) { throw 'Sudo expired; stop transfer without retry' }
    }
    & $uart -Command "sudo -n bash -n $remote/run_m418_visual.sh" -LogPath 'tmp/m41801/syntax.log' -TimeoutSeconds 15 -MarkerPrefix '__M418_SYNTAX_RC_'
    if (-not $?) { throw 'Runner syntax rejected' }
    & $python -X utf8 -B $workflow transfer
    if ($LASTEXITCODE -ne 0) { throw 'Transfer sync rejected' };exit 0
}
$prior=$null
if ($Mode -eq 'Chain' -or ($Mode -eq 'Collect' -and $Gate -eq 'Chain')) {
    VerifyEvidence 'latest_m418_visual_descriptor'
    if ($board.latest_m418_visual_descriptor.status -ne 'PASS_M418_DESCRIPTOR') { throw 'Lower gate failed' }
    $prior=$board.latest_m418_visual_descriptor.sha256
}
if ($Mode -eq 'Collect') {
    $log="tmp/m41801/recollect_$Gate.log"
    if (Test-Path (Join-Path $workspace $log)) { throw 'Existing export log preserved; use independent collection log' }
    & $uart -Command "sudo -n env PYTHONDONTWRITEBYTECODE=1 bash $remote/run_m418_visual.sh $digest Collect $Gate" -LogPath $log -TimeoutSeconds 180 -MarkerPrefix '__M418_EXPORT_RC_'
    if (-not $?) { throw 'Saved export rejected; no computation repeat' }
    $collectArgs=@('-X','utf8','-B',$workflow,'collect',$Gate,$log)
    if ($prior) { $collectArgs+=@($prior) }
    & $python @collectArgs
    if ($LASTEXITCODE -ne 0) { throw 'Collection rejected' };exit 0
}
if ($Mode -notin @('Descriptor','Chain')) { throw 'Explicit mode required' }
VerifyEvidence 'latest_m418_visual_linear_transfer'
if ($board.latest_m418_visual_linear_transfer.manifest_sha256 -ne $digest) { throw 'Transfer package drift' }
$log="tmp/m41801/run_$Mode.log"
if ((Test-Path (Join-Path $workspace $log)) -or (Test-Path (Join-Path $workspace "deployment/mage_vl4b/optimization_v1/runs/M418-visual-$($Mode.ToLowerInvariant())-board-01/BOARD_RESULT.json"))) { throw 'Original run exists; Collect only' }
& $uart -Command 'sudo -n true' -LogPath "tmp/m41801/sudo_$Mode.log" -TimeoutSeconds 15 -MarkerPrefix '__M418_SUDO_RC_'
if (-not $?) { throw 'Sudo expired; hardware not started' }
$gateError=$null
try {
    & $uart -Command "sudo -n env M418_ENABLE_VISUAL=1 PYTHONDONTWRITEBYTECODE=1 bash $remote/run_m418_visual.sh $digest Run $Mode $prior" -LogPath $log -TimeoutSeconds 360 -MarkerPrefix '__M418_RUN_RC_'
    if (-not $?) { throw 'Gate/export failed' }
} catch { $gateError=$_ }
$collectArgs=@('-X','utf8','-B',$workflow,'collect',$Mode,$log)
if ($prior) { $collectArgs+=@($prior) }
& $python @collectArgs
if ($LASTEXITCODE -ne 0) { throw 'Collection failed; recover saved bytes only' }
if ($gateError) { throw $gateError }
Write-Output "M418_GATE_SYNCHRONIZED $Mode"
