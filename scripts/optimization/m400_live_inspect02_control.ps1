[CmdletBinding()]
param([ValidateSet('SelfTest','Upload','Run','Collect')][string]$Mode)
$ErrorActionPreference='Stop'
Set-StrictMode -Version Latest
if ($Mode -eq 'SelfTest') {
    $taskTokens=$null;$taskErrors=$null
    [void][System.Management.Automation.Language.Parser]::ParseFile($PSCommandPath,[ref]$taskTokens,[ref]$taskErrors)
    if ($taskErrors.Count) {throw 'CPU live_inspect controller parse failed'}
    Write-Output 'M400_CPU_LIVE_CONTROLLER_PARSE_PASS';exit 0
}
$taskRoot=(Resolve-Path (Join-Path $PSScriptRoot '../..')).Path
$taskLocal='deployment/mage_vl4b/optimization_v1/candidates/M400-owner-live-inspect-02'
$taskRemote='/home/ubuntu/m400_owner_live_inspect_package_02'
$taskPackage=Join-Path $taskRoot $taskLocal
$taskManifest=Get-Content -LiteralPath (Join-Path $taskPackage 'PACKAGE_MANIFEST.json') -Raw -Encoding UTF8|ConvertFrom-Json
$taskSha=(Get-FileHash -LiteralPath (Join-Path $taskPackage 'PACKAGE_MANIFEST.json') -Algorithm SHA256).Hash.ToLowerInvariant()
$taskBoard=Get-Content -LiteralPath (Join-Path $taskRoot 'deployment/mage_vl4b/BOARD_GATE_RESULT.json') -Raw -Encoding UTF8|ConvertFrom-Json
$taskReceipt=$taskBoard.latest_m400_owner_live_inspect_preparation_02
if ($taskReceipt.manifest_sha256 -ne $taskSha -or (Get-FileHash -LiteralPath (Join-Path $taskRoot $taskReceipt.result) -Algorithm SHA256).Hash.ToLowerInvariant() -ne $taskReceipt.sha256) {throw 'Sentinel preparation differs'}
foreach ($taskDoc in @('CURRENT_STATE.md','docsMILESTONES.md')) {
    if (-not (Get-Content -LiteralPath (Join-Path $taskRoot $taskDoc) -Raw -Encoding UTF8).Contains($taskReceipt.sha256)) {throw 'Preparation triad incomplete'}
}
$taskUart=Join-Path $taskRoot 'scripts/m75c_uart_command.ps1'
& $taskUart -Command 'sudo -n true' -LogPath "tmp/m400/live_inspect02_sudo_$Mode.log" -TimeoutSeconds 15 -MarkerPrefix '__M400_LIVE_SUDO_RC_'
if (-not $?) {throw 'Same-terminal sudo required; no further actions'}
if ($Mode -eq 'Upload') {
    & $taskUart -Command "test ! -e $taskRemote" -LogPath 'tmp/m400/live_inspect02_absence.log' -TimeoutSeconds 15 -MarkerPrefix '__M400_LIVE_ABSENT_RC_'
    if (-not $?) {throw 'Existing live_inspect package cannot be overwritten'}
    foreach ($taskName in (@('PACKAGE_MANIFEST.json')+@($taskManifest.files|ForEach-Object path))) {
        & (Join-Path $taskRoot 'scripts/m212_uart_put_file_chunked.ps1') -LocalPath "$taskLocal/$taskName" -RemotePath "$taskRemote/$taskName" -LogPrefix "tmp/m400/live_inspect02_upload_$($taskName.Replace('.','_'))" -ChunkBytes 900 -TimeoutSeconds 25
        if (-not $?) {throw "Sentinel upload failed: $taskName"}
        Write-Output "M400_LIVE_FILE_SHA_PASS $taskName"
    }
    & $taskUart -Command "sudo -n bash -n $taskRemote/run_m400_live_inspect.sh" -LogPath 'tmp/m400/live_inspect02_syntax.log' -TimeoutSeconds 15 -MarkerPrefix '__M400_LIVE_SYNTAX_RC_'
    if (-not $?) {throw 'Sentinel runner syntax failed'}
    Write-Output 'M400_LIVE_UPLOAD_COMPLETE_NO_OVERLAY';exit 0
}
if ($Mode -eq 'Run') {
    if (Test-Path -LiteralPath (Join-Path $taskRoot 'tmp/m400/live_inspect02_run.log')) {throw 'Sentinel execution exists; collect only'}
    & $taskUart -Command "sudo -n bash $taskRemote/run_m400_live_inspect.sh $taskSha" -LogPath 'tmp/m400/live_inspect02_run.log' -TimeoutSeconds 40 -MarkerPrefix '__M400_LIVE_RUN_RC_'
    if (-not $?) {throw 'CPU live_inspect failed; collect original log only, no FPGA attach'}
    Write-Output 'M400_LIVE_RUN_COMPLETE';exit 0
}
if ($Mode -eq 'Collect') {
    & $taskUart -Command "sudo -n env PYTHONDONTWRITEBYTECODE=1 /usr/local/share/pynq-venv/bin/python -B $taskRemote/m400_live_inspect_driver.py Collect" -LogPath 'tmp/m400/live_inspect02_collect.log' -TimeoutSeconds 40 -MarkerPrefix '__M400_LIVE_EXPORT_RC_'
    if (-not $?) {throw 'Saved live_inspect export failed'}
    exit 0
}
throw 'Explicit mode required'
