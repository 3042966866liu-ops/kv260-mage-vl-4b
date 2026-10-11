[CmdletBinding()]
param()
$ErrorActionPreference='Stop'
Set-StrictMode -Version Latest
$workspace=(Resolve-Path (Join-Path $PSScriptRoot '..\..')).Path
$pwsh='C:\Users\30429\.cache\codex-runtimes\codex-primary-runtime\dependencies\native\powershell\pwsh.exe'
$local='scripts/optimization/export_board_input.py'
$remote='/home/ubuntu/tellme_m120_m89x2_20260901/optimization_v1/OP01-input-reference-01/export_board_input.py'
$digest=(Get-FileHash -LiteralPath (Join-Path $workspace $local) -Algorithm SHA256).Hash.ToLowerInvariant()
$lockPath=Join-Path $workspace 'deployment/mage_vl4b/optimization_v1/control.lock'
$lock=[IO.File]::Open($lockPath,[IO.FileMode]::CreateNew,[IO.FileAccess]::Write,[IO.FileShare]::None)
try {
    & $pwsh -NoProfile -File scripts/m255_require_uart_shell.ps1 -LogPath tmp/op01_input_reference01/shell.log
    if($LASTEXITCODE -ne 0){throw 'UART shell unavailable'}
    & $pwsh -NoProfile -File scripts/m212_uart_put_file_chunked.ps1 -LocalPath $local -RemotePath $remote -LogPrefix tmp/op01_input_reference01/upload | Out-Null
    if($LASTEXITCODE -ne 0){throw 'Upload failed'}
    & $pwsh -NoProfile -File scripts/m75c_uart_command.ps1 -Command "/usr/local/share/pynq-venv/bin/python -B $remote --self-sha256 $digest" -LogPath tmp/op01_input_reference01/run.log -TimeoutSeconds 90 -MarkerPrefix '__OP01_RGB_RC_'
    exit $LASTEXITCODE
} finally {$lock.Dispose(); Remove-Item -LiteralPath $lockPath}
