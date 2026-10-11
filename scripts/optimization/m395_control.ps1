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
    Write-Output 'M395_CONTROL_SELF_TEST_PASS';exit 0
}
$workspace=(Resolve-Path (Join-Path $PSScriptRoot '../..')).Path
$local='deployment/mage_vl4b/optimization_v1/candidates/M395-silu-performance-01'
$remote='/home/ubuntu/m395_silu_performance_candidate_01'
$package=Join-Path $workspace $local
$manifest=Get-Content -LiteralPath (Join-Path $package 'PACKAGE_MANIFEST.json') -Raw -Encoding UTF8 | ConvertFrom-Json
$digest=(Get-FileHash -LiteralPath (Join-Path $package 'PACKAGE_MANIFEST.json') -Algorithm SHA256).Hash.ToLowerInvariant()
$oldManifest=Get-Content -LiteralPath (Join-Path $workspace 'deployment/mage_vl4b/optimization_v1/candidates/M388-ps-performance-01/PACKAGE_MANIFEST.json') -Raw -Encoding UTF8 | ConvertFrom-Json
$oldEntries=@{}
foreach ($row in $oldManifest.files) { $oldEntries[$row.path]=$row.sha256+':'+$row.bytes }
$delta=@($manifest.files | Where-Object { (-not $oldEntries.ContainsKey($_.path)) -or $oldEntries[$_.path] -ne ($_.sha256+':'+$_.bytes) } | ForEach-Object path)
if ($Mode -eq 'List') { ConvertTo-Json -InputObject (@('PACKAGE_MANIFEST.json')+$delta) -Compress;exit 0 }
$uart=Join-Path $workspace 'scripts/m75c_uart_command.ps1'
$python='C:\Users\30429\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe'
$workflow=Join-Path $PSScriptRoot 'm395_workflow.py'
$board=Get-Content -LiteralPath (Join-Path $workspace 'deployment/mage_vl4b/BOARD_GATE_RESULT.json') -Raw -Encoding UTF8 | ConvertFrom-Json
foreach ($key in @('latest_m395_silu_performance_preparation','latest_m395_silu_performance_support')) {
    $e=$board.$key
    if ($e.manifest_sha256 -ne $digest -or (Get-FileHash -LiteralPath (Join-Path $workspace $e.result) -Algorithm SHA256).Hash.ToLowerInvariant() -ne $e.sha256) { throw 'Prerequisite drift' }
    foreach ($n in @('CURRENT_STATE.md','docsMILESTONES.md')) {
        if (-not (Get-Content -LiteralPath (Join-Path $workspace $n) -Raw -Encoding UTF8).Contains($e.sha256)) { throw 'Prerequisite not synchronized' }
    }
}
$supportRaw=Get-Content -LiteralPath (Join-Path $workspace $board.latest_m395_silu_performance_support.result) -Raw -Encoding UTF8 | ConvertFrom-Json
foreach ($p in $supportRaw.source_sha256.PSObject.Properties) {
    if ((Get-FileHash -LiteralPath (Join-Path $PSScriptRoot $p.Name) -Algorithm SHA256).Hash.ToLowerInvariant() -ne $p.Value) { throw 'Support source drift' }
}
foreach ($row in $manifest.files) {
    $path=Join-Path $package $row.path
    if ((Get-Item -LiteralPath $path).Length -ne $row.bytes -or (Get-FileHash -LiteralPath $path -Algorithm SHA256).Hash.ToLowerInvariant() -ne $row.sha256) { throw 'Payload drift' }
}
if ($Mode -eq 'Upload') {
    & $uart -Command 'sudo -n true' -LogPath 'tmp/m395/sudo_upload_precheck_01.log' -TimeoutSeconds 15 -MarkerPrefix '__M395_UPLOAD_SUDO_RC_'
    if (-not $?) { throw 'Sudo expired; no upload or gate' }
    & $uart -Command "test ! -e $remote" -LogPath 'tmp/m395/package_absence_uart.log' -TimeoutSeconds 15 -MarkerPrefix '__M395_ABSENT_RC_'
    if (-not $?) { throw 'Existing package cannot be overwritten' }
    foreach ($name in (@('PACKAGE_MANIFEST.json')+$delta)) {
        & (Join-Path $workspace 'scripts/m212_uart_put_file_chunked.ps1') -LocalPath "$local/$name" -RemotePath "$remote/$name" -LogPrefix "tmp/m395/upload_$($name.Replace('.','_'))" -ChunkBytes 900 -TimeoutSeconds 25
        if (-not $?) { throw "File upload rejected: $name" }
        Write-Output "M395_FILE_TRANSFERRED $name"
    }
    & $uart -Command "sudo -n env PYTHONDONTWRITEBYTECODE=1 /usr/local/share/pynq-venv/bin/python -B $remote/m395_assemble.py $digest" -LogPath 'tmp/m395/assembly_uart.log' -TimeoutSeconds 30 -MarkerPrefix '__M395_ASSEMBLY_RC_'
    if (-not $?) { throw 'Assembly rejected' }
    & $uart -Command "sudo -n bash -n $remote/run_m395_light_video.sh" -LogPath 'tmp/m395/root_syntax_uart.log' -TimeoutSeconds 15 -MarkerPrefix '__M395_SYNTAX_RC_'
    if (-not $?) { throw 'Root syntax rejected' }
    & $python -X utf8 -B $workflow transfer
    if ($LASTEXITCODE -ne 0) { throw 'Transfer sync rejected' }
    exit 0
}
if ($Mode -eq 'Collect') {
    & $uart -Command "sudo -n env PYTHONDONTWRITEBYTECODE=1 /usr/local/share/pynq-venv/bin/python -B $remote/m395_export_result.py B1" -LogPath 'tmp/m395/recollect_uart.log' -TimeoutSeconds 180 -MarkerPrefix '__M395_EXPORT_RC_'
    if (-not $?) { throw 'Saved export rejected; no gate repeat' }
    & $python -X utf8 -B $workflow collect 'tmp/m395/recollect_uart.log'
    if ($LASTEXITCODE -ne 0) { throw 'Saved collection rejected' }
    exit 0
}
if ($Mode -ne 'Run') { throw 'Explicit mode required' }
$e=$board.latest_m395_silu_performance_transfer
if ($e.manifest_sha256 -ne $digest -or (Get-FileHash -LiteralPath (Join-Path $workspace $e.result) -Algorithm SHA256).Hash.ToLowerInvariant() -ne $e.sha256) { throw 'Transfer evidence drift' }
foreach ($n in @('CURRENT_STATE.md','docsMILESTONES.md')) {
    if (-not (Get-Content -LiteralPath (Join-Path $workspace $n) -Raw -Encoding UTF8).Contains($e.sha256)) { throw 'Transfer not synchronized' }
}
if ((Test-Path (Join-Path $workspace 'tmp/m395/component_uart.log')) -or (Test-Path (Join-Path $workspace 'deployment/mage_vl4b/optimization_v1/runs/M395-silu-performance-board-01/BOARD_RESULT.json'))) { throw 'Original execution exists; collect only' }
& $uart -Command "bash -n $remote/run_m395_light_video.sh" -LogPath 'tmp/m395/runner_syntax_uart.log' -TimeoutSeconds 15 -MarkerPrefix '__M395_SYNTAX_RC_'
if (-not $?) { throw 'Runner syntax rejected' }
& $uart -Command 'sudo -n true' -LogPath 'tmp/m395/sudo_before_component_uart.log' -TimeoutSeconds 15 -MarkerPrefix '__M395_GATE_SUDO_RC_'
if (-not $?) { throw 'Sudo expired; no gate' }
Invoke-GateAndCollect {
    & $uart -Command "sudo -n env M395_ENABLE_LIGHT_VIDEO=1 bash $remote/run_m395_light_video.sh $digest Run B1" -LogPath 'tmp/m395/component_uart.log' -TimeoutSeconds 3900 -MarkerPrefix '__M395_COMPONENT_RC_'
    if (-not $?) { throw 'Original gate/export failed; still collect' }
} {
    & $python -X utf8 -B $workflow collect 'tmp/m395/component_uart.log'
    if ($LASTEXITCODE -ne 0) { throw 'Collection failed; saved recovery only' }
}
Write-Output 'M395_CAPTURE_SYNCHRONIZED'
