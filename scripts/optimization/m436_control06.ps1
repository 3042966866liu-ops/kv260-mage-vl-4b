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
    'M436_CONTROL_SELF_TEST_PASS';exit 0
}
$workspace=(Resolve-Path (Join-Path $PSScriptRoot '../..')).Path
New-Item -ItemType Directory -Force -Path (Join-Path $workspace 'tmp/m43602/board') | Out-Null
$relative='deployment/mage_vl4b/optimization_v1/candidates/M436-weight-read-observation-03'
$package=Join-Path $workspace $relative
$remote='/home/ubuntu/m436_weight_read_candidate_01'
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
foreach ($key in @('latest_m434_read_path_audit','latest_m432_integrated_board','latest_m435_IO_preparation','latest_m435_IO_support','latest_m436_IO_preparation')) { VerifyEvidence $key }
$support=Get-Content -Raw -Encoding UTF8 -LiteralPath (Join-Path $workspace $board.latest_m435_IO_support.result) | ConvertFrom-Json
if ($support.manifest_sha256 -ne $board.latest_m435_IO_preparation.manifest_sha256) { throw 'Support package differs' }
foreach ($p in $support.source_sha256.PSObject.Properties) {
    if ((Get-FileHash -LiteralPath (Join-Path $PSScriptRoot $p.Name) -Algorithm SHA256).Hash.ToLowerInvariant() -ne $p.Value) { throw 'Supported host source differs' }
}
VerifyEvidence 'latest_m436_route_support'
$routeSupport=Get-Content -Raw -Encoding UTF8 -LiteralPath (Join-Path $workspace $board.latest_m436_route_support.result) | ConvertFrom-Json
if ($routeSupport.manifest_sha256 -ne $digest -or $routeSupport.candidate_remote -ne $remote -or $routeSupport.evidence_remote -eq $remote) { throw 'Route support differs' }
foreach ($p in $routeSupport.host_sources.PSObject.Properties) {
    if ((Get-FileHash -LiteralPath (Join-Path $PSScriptRoot $p.Name) -Algorithm SHA256).Hash.ToLowerInvariant() -ne $p.Value) { throw 'Route host source differs' }
}
VerifyEvidence 'latest_m436_IO_transfer'
if ($board.latest_m436_IO_transfer.manifest_sha256 -ne '1fa013addfb4db1351d9155a3ffc7c041009d57bafa1dd5128d30ee003405ed7') { throw 'Assembly source transfer differs' }
VerifyEvidence 'latest_m435_authorization_precheck'
$auth=Get-Content -Raw -Encoding UTF8 -LiteralPath (Join-Path $workspace $board.latest_m435_authorization_precheck.result) | ConvertFrom-Json
foreach ($p in $auth.resume_sources.PSObject.Properties) {
    if ((Get-FileHash -LiteralPath (Join-Path $PSScriptRoot $p.Name) -Algorithm SHA256).Hash.ToLowerInvariant() -ne $p.Value) { throw 'Resumed authorization source differs' }
}
foreach ($row in $manifest.files) {
    $p=Join-Path $package $row.path
    if ((Get-Item -LiteralPath $p).Length -ne $row.bytes -or (Get-FileHash -LiteralPath $p -Algorithm SHA256).Hash.ToLowerInvariant() -ne $row.sha256) { throw 'Payload drift' }
}
$uart=Join-Path $workspace 'scripts/m75c_uart_command.ps1'
$python='C:\Users\30429\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe'
$workflow=Join-Path $PSScriptRoot 'm436_workflow02.py'
if ($Mode -eq 'Upload') {
    if (Test-Path (Join-Path $workspace 'tmp/m43602/board/sudo_upload_resume05.log')) { throw 'Original authorization log exists' }
    & $uart -Command 'sudo -n true' -LogPath 'tmp/m43602/board/sudo_upload_resume05.log' -TimeoutSeconds 15 -MarkerPrefix '__M435_SUDO_RC_'
    if (-not $?) { throw 'Authorization required; no upload' }
    & $uart -Command "test ! -e $remote" -LogPath 'tmp/m43602/board/absence.log' -TimeoutSeconds 15 -MarkerPrefix '__M435_ABSENT_RC_'
    if (-not $?) { throw 'Existing package cannot be overwritten' }
    $old=Get-Content -LiteralPath (Join-Path $workspace 'deployment/mage_vl4b/optimization_v1/candidates/M435-weight-read-observation-02/PACKAGE_MANIFEST.json') -Raw -Encoding UTF8 | ConvertFrom-Json
    $delta=@($manifest.files | Where-Object { $item=$_; -not @($old.files | Where-Object { $_.path -eq $item.path -and $_.sha256 -eq $item.sha256 -and $_.bytes -eq $item.bytes }).Count } | ForEach-Object path)
    foreach ($name in (@('PACKAGE_MANIFEST.json')+$delta)) {
        & (Join-Path $workspace 'scripts/m212_uart_put_file_chunked.ps1') -LocalPath "$relative/$name" -RemotePath "$remote/$name" -LogPrefix "tmp/m43602/board/upload_$($name.Replace('.','_'))" -ChunkBytes 900 -TimeoutSeconds 25
        if (-not $?) { throw "Transfer failed: $name" }
        "M435_FILE_TRANSFERRED $name"
        & $uart -Command 'sudo -n true' -LogPath "tmp/m43602/board/refresh_$($name.Replace('.','_')).log" -TimeoutSeconds 15 -MarkerPrefix '__M435_SUDO_RC_'
        if (-not $?) { throw 'Sudo expired; upload stopped' }
    }
    & $uart -Command "sudo -n /usr/local/share/pynq-venv/bin/python -B $remote/m435_assemble.py $digest" -LogPath 'tmp/m43602/board/assembly.log' -TimeoutSeconds 30 -MarkerPrefix '__M435_ASSEMBLY_RC_'
    if (-not $?) { throw 'Assembly rejected' }
    & $uart -Command "sudo -n bash -n $remote/run_m435.sh" -LogPath 'tmp/m43602/board/syntax.log' -TimeoutSeconds 15 -MarkerPrefix '__M435_SYNTAX_RC_'
    if (-not $?) { throw 'Runner syntax rejected' }
    & $python -X utf8 -B $workflow transfer
    if ($LASTEXITCODE -ne 0) { throw 'Transfer evidence rejected' };exit 0
}
if ($Mode -eq 'Collect') {
    if (Test-Path (Join-Path $workspace 'tmp/m43602/board/recollect.log')) { throw 'Saved recovery log exists' }
    & $uart -Command "sudo -n env PYTHONDONTWRITEBYTECODE=1 bash $remote/run_m435.sh $digest Collect" -LogPath 'tmp/m43602/board/recollect.log' -TimeoutSeconds 1080 -MarkerPrefix '__M435_EXPORT_RC_'
    if (-not $?) { throw 'Saved export failed; no hardware repeat' }
    & $python -X utf8 -B $workflow collect 'tmp/m43602/board/recollect.log'
    if ($LASTEXITCODE -ne 0) { throw 'Saved collection failed' };exit 0
}
if ($Mode -ne 'Run') { throw 'Explicit mode required' }
VerifyEvidence 'latest_m436_route_transfer'
if ($board.latest_m436_route_transfer.manifest_sha256 -ne $digest) { throw 'Transfer identity differs' }
if ((Test-Path (Join-Path $workspace 'tmp/m43602/board/run.log')) -or (Test-Path (Join-Path $workspace 'deployment/mage_vl4b/optimization_v1/runs/M436-IO-observation-board-02/BOARD_RESULT.json'))) { throw 'Original run exists; Collect only' }
& $uart -Command 'sudo -n true' -LogPath 'tmp/m43602/board/sudo_run.log' -TimeoutSeconds 15 -MarkerPrefix '__M435_SUDO_RC_'
if (-not $?) { throw 'Sudo expired; no gate execution' }
$gateError=$null
try {
    & $uart -Command "sudo -n env M435_ENABLE_INTEGRATED_VIDEO=1 PYTHONDONTWRITEBYTECODE=1 bash $remote/run_m435.sh $digest Run" -LogPath 'tmp/m43602/board/run.log' -TimeoutSeconds 2100 -MarkerPrefix '__M435_RUN_RC_'
    if (-not $?) { throw 'Saved-feature language gate/export failed' }
} catch { $gateError=$_ }
& $python -X utf8 -B $workflow collect 'tmp/m43602/board/run.log'
if ($LASTEXITCODE -ne 0) { throw 'Collection rejected; recover saved bytes only' }
if ($gateError) { throw $gateError }
'M435_INTEGRATED_NUMERICAL_SYNCHRONIZED'


