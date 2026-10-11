param([ValidateSet(1,2,5)][int]$Revision=2)
$ErrorActionPreference='Stop'
Set-StrictMode -Version Latest
$pwsh='C:\Users\30429\.cache\codex-runtimes\codex-primary-runtime\dependencies\native\powershell\pwsh.exe'
$logs=('tmp/op01_sys{0:00}' -f $Revision)
$log=Get-Content "$logs/run.log" -Raw
if($log -notmatch '__OP01_SYS_RC_[01]__'){throw 'SYS not terminal'}
$summary=($log.Split(@('OP01_SYS_JSON_BEGIN'),[StringSplitOptions]::None)[1].Split(@('OP01_SYS_JSON_END'),[StringSplitOptions]::None)[0]) | ConvertFrom-Json
$local='scripts/optimization/export_sys_result.py'
$remote=('/home/ubuntu/tellme_m120_m89x2_20260901/optimization_v1/OP01-result-export-{0:00}/export_sys_result.py' -f $Revision)
$hash=(Get-FileHash $local -Algorithm SHA256).Hash.ToLowerInvariant()
$lockPath='deployment/mage_vl4b/optimization_v1/control.lock'
$lock=[IO.File]::Open((Join-Path (Get-Location) $lockPath),[IO.FileMode]::CreateNew,[IO.FileAccess]::Write,[IO.FileShare]::None)
try {
 & $pwsh -NoProfile -File scripts/m212_uart_put_file_chunked.ps1 -LocalPath $local -RemotePath $remote -LogPrefix "$logs/upload_export" | Out-Null
 if($LASTEXITCODE -ne 0){throw 'Exporter upload failed'}
 & $pwsh -NoProfile -File scripts/m75c_uart_command.ps1 -Command "/usr/local/share/pynq-venv/bin/python $remote --self-sha256 $hash --result-sha256 $($summary.full_result_sha256) --revision $Revision" -LogPath "$logs/export.log" -TimeoutSeconds 60 -MarkerPrefix '__OP01_EXPORT_RC_'
 exit $LASTEXITCODE
} finally {$lock.Dispose();Remove-Item -LiteralPath $lockPath}
