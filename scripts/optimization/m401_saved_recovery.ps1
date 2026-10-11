[CmdletBinding()]
param([ValidateSet('Upload','Collect')][string]$Mode)
$ErrorActionPreference='Stop'
Set-StrictMode -Version Latest
$workspace=(Resolve-Path (Join-Path $PSScriptRoot '../..')).Path
$local='deployment/mage_vl4b/optimization_v1/candidates/M401-saved-recovery-01'
$remote='/home/ubuntu/m401_saved_recovery_package_01'
$package=Join-Path $workspace $local
$digest=(Get-FileHash -LiteralPath (Join-Path $package 'PACKAGE_MANIFEST.json') -Algorithm SHA256).Hash.ToLowerInvariant()
$manifest=Get-Content -LiteralPath (Join-Path $package 'PACKAGE_MANIFEST.json') -Raw -Encoding UTF8 | ConvertFrom-Json
foreach ($row in $manifest.files) {
    $path=Join-Path $package $row.path
    if ((Get-Item -LiteralPath $path).Length -ne $row.bytes -or (Get-FileHash -LiteralPath $path -Algorithm SHA256).Hash.ToLowerInvariant() -ne $row.sha256) { throw 'Recovery payload drift' }
}
$uart=Join-Path $workspace 'scripts/m75c_uart_command.ps1'
if ($Mode -eq 'Upload') {
    & $uart -Command 'sudo -n true' -LogPath 'tmp/m401/recovery_sudo.log' -TimeoutSeconds 15 -MarkerPrefix '__M401_RECOVERY_SUDO_RC_'
    if (-not $?) { throw 'Sudo expired; stop collection' }
    & $uart -Command "test ! -e $remote" -LogPath 'tmp/m401/recovery_absence.log' -TimeoutSeconds 15 -MarkerPrefix '__M401_RECOVERY_ABSENT_RC_'
    if (-not $?) { throw 'Immutable recovery package already exists' }
    foreach ($name in @('PACKAGE_MANIFEST.json','m401_saved_export.py')) {
        & (Join-Path $workspace 'scripts/m212_uart_put_file_chunked.ps1') -LocalPath "$local/$name" -RemotePath "$remote/$name" -LogPrefix "tmp/m401/recovery_$($name.Replace('.','_'))" -ChunkBytes 900 -TimeoutSeconds 25
        if (-not $?) { throw 'Recovery upload rejected' }
    }
    exit 0
}
if ($Mode -ne 'Collect') { throw 'Explicit mode required' }
& $uart -Command "sudo -n env PYTHONDONTWRITEBYTECODE=1 /usr/local/share/pynq-venv/bin/python -B $remote/m401_saved_export.py $digest --collect-saved" -LogPath 'tmp/m401/saved_recovery_uart.log' -TimeoutSeconds 60 -MarkerPrefix '__M401_SAVED_RECOVER_RC_'
if (-not $?) { throw 'Saved export rejected; do not rerun hardware' }
