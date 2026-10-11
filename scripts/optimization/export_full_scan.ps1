$ErrorActionPreference='Stop'
Set-StrictMode -Version Latest
$pwsh='C:\Users\30429\.cache\codex-runtimes\codex-primary-runtime\dependencies\native\powershell\pwsh.exe'
$logs='tmp/op01_full_file_scan01'
$text=Get-Content "$logs/run.log" -Raw
if($text -notmatch '__FULL_SCAN_RC_[01]__'){throw 'Scan not terminal'}
$summary=($text.Split(@('FULL_SCAN_JSON_BEGIN'),[StringSplitOptions]::None)[1].Split(@('FULL_SCAN_JSON_END'),[StringSplitOptions]::None)[0])|ConvertFrom-Json
$lockPath='deployment/mage_vl4b/optimization_v1/control.lock'
$lock=[IO.File]::Open((Join-Path (Get-Location) $lockPath),[IO.FileMode]::CreateNew,[IO.FileAccess]::Write,[IO.FileShare]::None)
try {
    $local='scripts/optimization/export_full_scan.py';$remote='/home/ubuntu/op01_full_file_scan_01/export.py'
    & $pwsh -NoProfile -File scripts/m212_uart_put_file_chunked.ps1 -LocalPath $local -RemotePath $remote -LogPrefix "$logs/upload_export" | Out-Null
    if($LASTEXITCODE -ne 0){throw 'Export upload failed'}
    $hash=(Get-FileHash $local).Hash.ToLowerInvariant()
    & $pwsh -NoProfile -File scripts/m75c_uart_command.ps1 -Command "/usr/local/share/pynq-venv/bin/python -B $remote $hash $($summary.result_sha256)" -LogPath "$logs/export.log" -TimeoutSeconds 60 -MarkerPrefix '__SCAN_EXPORT_RC_'
    exit $LASTEXITCODE
} finally {$lock.Dispose();Remove-Item -LiteralPath $lockPath}
