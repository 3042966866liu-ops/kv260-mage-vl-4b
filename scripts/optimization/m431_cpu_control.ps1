[CmdletBinding()]
param([ValidateSet('SelfTest','Upload','Run','Collect')][string]$Mode)
$ErrorActionPreference='Stop'
Set-StrictMode -Version Latest
if ($Mode -eq 'SelfTest') {
    $tokens=$null;$errors=$null
    [void][System.Management.Automation.Language.Parser]::ParseFile($PSCommandPath,[ref]$tokens,[ref]$errors)
    if ($errors.Count) { throw 'Control parse rejected' }
    $saved=$null;$collected=$false
    try { throw 'Intentional gate failure' } catch { $saved=$_ }
    $collected=$true
    if (-not $saved -or -not $collected) { throw 'Collect skipped' }
    'M431_BOOTSTRAP_CONTROL_PASS';exit 0
}
$workspace=(Resolve-Path (Join-Path $PSScriptRoot '../..')).Path
$relative='deployment/mage_vl4b/optimization_v1/candidates/M431-borrowed-late11-CPU-02'
$package=Join-Path $workspace $relative
$remote='/home/ubuntu/m431_borrowed_CPU_candidate_02'
$digest=(Get-FileHash (Join-Path $package 'PACKAGE_MANIFEST.json') -Algorithm SHA256).Hash.ToLowerInvariant()
$manifest=Get-Content (Join-Path $package 'PACKAGE_MANIFEST.json') -Raw -Encoding UTF8 | ConvertFrom-Json
$board=Get-Content (Join-Path $workspace 'deployment/mage_vl4b/BOARD_GATE_RESULT.json') -Raw -Encoding UTF8 | ConvertFrom-Json
function Evidence([string]$key) {
    $e=$board.$key
    if ((Get-FileHash (Join-Path $workspace $e.result) -Algorithm SHA256).Hash.ToLowerInvariant() -ne $e.sha256) { throw 'Evidence changed' }
    foreach ($n in @('CURRENT_STATE.md','docsMILESTONES.md')) {
        if (-not (Get-Content (Join-Path $workspace $n) -Raw -Encoding UTF8).Contains($e.sha256)) { throw 'Evidence not synchronized' }
    }
}
foreach ($k in @('latest_m430_complete_visual_closure','latest_m431_borrowed_CPU_support')) { Evidence $k }
Evidence 'latest_m431_isolated_packet_component'
if (-not $board.latest_m430_complete_visual_closure.performance_pass) { throw 'Visual performance prerequisite failed' }
$support=Get-Content (Join-Path $workspace $board.latest_m431_borrowed_CPU_support.result) -Raw -Encoding UTF8 | ConvertFrom-Json
if ($support.manifest_sha256 -ne $digest) { throw 'Support/manifest differs' }
foreach ($p in $support.source_sha256.PSObject.Properties) {
    if ((Get-FileHash (Join-Path $PSScriptRoot $p.Name) -Algorithm SHA256).Hash.ToLowerInvariant() -ne $p.Value) { throw 'Actual control/collector changed' }
}
foreach ($row in $manifest.files) {
    $p=Join-Path $package $row.path
    if ((Get-Item $p).Length -ne $row.bytes -or (Get-FileHash $p -Algorithm SHA256).Hash.ToLowerInvariant() -ne $row.sha256) { throw 'Payload changed' }
}
$uart=Join-Path $workspace 'scripts/m75c_uart_command.ps1'
$python='C:\Users\30429\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe'
$hostTool=Join-Path $PSScriptRoot 'm431_cpu_host.py'
$folder='tmp/m431cpu01'
if ($Mode -eq 'Upload') {
    if (Test-Path (Join-Path $workspace "$folder/sudo_upload.log")) { throw 'Original authorization receipt exists' }
    & $uart -Command 'sudo -n true' -LogPath "$folder/sudo_upload.log" -TimeoutSeconds 15 -MarkerPrefix '__M431_BOOT_SUDO_RC_'
    if (-not $?) { throw 'Authorization required; no upload' }
    & $uart -Command "test ! -e $remote" -LogPath "$folder/absence.log" -TimeoutSeconds 15 -MarkerPrefix '__M431_BOOT_ABSENT_RC_'
    if (-not $?) { throw 'Existing packet preserved' }
    foreach ($name in (@('PACKAGE_MANIFEST.json')+@($manifest.files | ForEach-Object path))) {
        & (Join-Path $workspace 'scripts/m212_uart_put_file_chunked.ps1') -LocalPath "$relative/$name" -RemotePath "$remote/$name" -LogPrefix "$folder/upload_$($name.Replace('.','_'))" -ChunkBytes 900 -TimeoutSeconds 25
        if (-not $?) { throw "Transfer failed $name" }
        & $uart -Command 'sudo -n true' -LogPath "$folder/refresh_$($name.Replace('.','_')).log" -TimeoutSeconds 15 -MarkerPrefix '__M431_BOOT_SUDO_RC_'
        if (-not $?) { throw 'Sudo expired; upload stopped' }
    }
    & $uart -Command "sudo -n bash -n $remote/run_cpu.sh" -LogPath "$folder/syntax.log" -TimeoutSeconds 15 -MarkerPrefix '__M431_BOOT_SYNTAX_RC_'
    if (-not $?) { throw 'bash-n rejected' }
    & $python -X utf8 -B $hostTool transfer
    if ($LASTEXITCODE -ne 0) { throw 'Transfer evidence rejected' };exit 0
}
if ($Mode -eq 'Collect') {
    if (Test-Path (Join-Path $workspace "$folder/recollect.log")) { throw 'Recovery receipt exists' }
    & $uart -Command "sudo -n bash $remote/run_cpu.sh $digest Collect" -LogPath "$folder/recollect.log" -TimeoutSeconds 120 -MarkerPrefix '__M431_BOOT_EXPORT_RC_'
    if (-not $?) { throw 'Saved export rejected' }
    & $python -X utf8 -B $hostTool collect "$folder/recollect.log"
    if ($LASTEXITCODE -ne 0) { throw 'Collection rejected' };exit 0
}
if ($Mode -ne 'Run') { throw 'Explicit mode required' }
Evidence 'latest_m431_borrowed_CPU_transfer'
if ($board.latest_m431_borrowed_CPU_transfer.manifest_sha256 -ne $digest) { throw 'Wrong transferred packet' }
if ((Test-Path (Join-Path $workspace "$folder/run.log")) -or (Test-Path (Join-Path $workspace 'deployment/mage_vl4b/optimization_v1/runs/M431-borrowed-CPU-board-01/BOARD_RESULT.json'))) { throw 'Saved attempt: Collect only' }
& $uart -Command 'sudo -n true' -LogPath "$folder/sudo_run.log" -TimeoutSeconds 15 -MarkerPrefix '__M431_BOOT_SUDO_RC_'
if (-not $?) { throw 'Sudo expired; no execution' }
$saved=$null
try {
    & $uart -Command "sudo -n bash $remote/run_cpu.sh $digest --enable-CPU-bootstrap" -LogPath "$folder/run.log" -TimeoutSeconds 300 -MarkerPrefix '__M431_BOOT_RUN_RC_'
    if (-not $?) { throw 'CPU gate or export failed' }
} catch { $saved=$_ }
& $python -X utf8 -B $hostTool collect "$folder/run.log"
if ($LASTEXITCODE -ne 0) { throw 'Recovery only; no repeat CPU gate' }
if ($saved) { throw $saved }
'M431_BOOTSTRAP_SYNCHRONIZED'
