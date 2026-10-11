[CmdletBinding()]
param()
$ErrorActionPreference='Stop'
Set-StrictMode -Version Latest
$workspace=(Resolve-Path (Join-Path $PSScriptRoot '../..')).Path
$relative='deployment/mage_vl4b/optimization_v1/candidates/M427-saved-export-recovery-01'
$package=Join-Path $workspace $relative
$remote='/home/ubuntu/m427_saved_export_recovery_01'
$digest='84fb377b59b3d4d5567b79b254474ab9f53f3ee0de15136d71e91b96d4a6193b'
$board=Get-Content -LiteralPath (Join-Path $workspace 'deployment/mage_vl4b/BOARD_GATE_RESULT.json') -Raw -Encoding UTF8 | ConvertFrom-Json
foreach ($key in @('latest_m427_export_failure','latest_m427_export_recovery_preparation')) {
    $e=$board.$key
    if ((Get-FileHash -LiteralPath (Join-Path $workspace $e.result) -Algorithm SHA256).Hash.ToLowerInvariant() -ne $e.sha256) { throw 'Recovery prerequisite SHA differs' }
    foreach ($name in @('CURRENT_STATE.md','docsMILESTONES.md')) {
        if (-not (Get-Content -LiteralPath (Join-Path $workspace $name) -Raw -Encoding UTF8).Contains($e.sha256)) { throw 'Recovery prerequisite not synchronized' }
    }
}
if ((Get-FileHash -LiteralPath (Join-Path $package 'PACKAGE_MANIFEST.json') -Algorithm SHA256).Hash.ToLowerInvariant() -ne $digest) { throw 'Recovery packet manifest differs' }
$manifest=Get-Content -LiteralPath (Join-Path $package 'PACKAGE_MANIFEST.json') -Raw -Encoding UTF8 | ConvertFrom-Json
if ($manifest.file_count -ne 3) { throw 'Unexpected recovery payload' }
foreach ($row in $manifest.files) {
    $p=Join-Path $package $row.path
    if ((Get-Item -LiteralPath $p).Length -ne $row.bytes -or (Get-FileHash -LiteralPath $p -Algorithm SHA256).Hash.ToLowerInvariant() -ne $row.sha256) { throw 'Recovery payload differs' }
}
$uart=Join-Path $workspace 'scripts/m75c_uart_command.ps1'
if (Test-Path (Join-Path $workspace 'tmp/m427_recovery01/sudo.log')) { throw 'Original authorization log exists; saved-only new control needed' }
& $uart -Command 'sudo -n true' -LogPath 'tmp/m427_recovery01/sudo.log' -TimeoutSeconds 15 -MarkerPrefix '__M427_RECOVERY_SUDO_RC_'
if (-not $?) { throw 'Authorization required; no recovery upload' }
& $uart -Command "test ! -e $remote" -LogPath 'tmp/m427_recovery01/absence.log' -TimeoutSeconds 15 -MarkerPrefix '__M427_RECOVERY_ABSENT_RC_'
if (-not $?) { throw 'Existing recovery packet cannot be overwritten' }
foreach ($name in (@('PACKAGE_MANIFEST.json')+@($manifest.files | ForEach-Object path))) {
    & (Join-Path $workspace 'scripts/m212_uart_put_file_chunked.ps1') -LocalPath "$relative/$name" -RemotePath "$remote/$name" -LogPrefix "tmp/m427_recovery01/upload_$($name.Replace('.','_'))" -ChunkBytes 900 -TimeoutSeconds 25
    if (-not $?) { throw "Recovery transfer failed: $name" }
    "M427_RECOVERY_FILE_TRANSFERRED $name"
}
& $uart -Command "sudo -n bash -n $remote/collect_saved.sh" -LogPath 'tmp/m427_recovery01/syntax.log' -TimeoutSeconds 15 -MarkerPrefix '__M427_RECOVERY_SYNTAX_RC_'
if (-not $?) { throw 'Saved-only runner syntax/authorization rejected' }
& $uart -Command "sudo -n env PYTHONDONTWRITEBYTECODE=1 bash $remote/collect_saved.sh $digest" -LogPath 'tmp/m427_recovery01/export.log' -TimeoutSeconds 900 -MarkerPrefix '__M427_RECOVERY_EXPORT_RC_'
if (-not $?) { throw 'Saved export failed; no model repeat' }
& 'C:\Users\30429\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe' -X utf8 -B (Join-Path $PSScriptRoot 'm427_workflow02.py') collect 'tmp/m427_recovery01/export.log'
if ($LASTEXITCODE -ne 0) { throw 'Saved-byte collection rejected; no model repeat' }
'M427_SAVED_EXPORT_RECOVERY_COLLECTED'
