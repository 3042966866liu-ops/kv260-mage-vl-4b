$ErrorActionPreference='Stop'
Set-StrictMode -Version Latest
$pwsh='C:\Users\30429\.cache\codex-runtimes\codex-primary-runtime\dependencies\native\powershell\pwsh.exe'
$board=Get-Content deployment/mage_vl4b/optimization_v1/gates/G01-decode-replay/attempt_01/board_result.json -Raw|ConvertFrom-Json
if($board.status -ne 'MEASURED'){throw 'No verified replay capture'}
$logs='tmp/op01_replay_capture01';$lockPath='deployment/mage_vl4b/optimization_v1/control.lock'
$lock=[IO.File]::Open((Join-Path (Get-Location) $lockPath),[IO.FileMode]::CreateNew,[IO.FileAccess]::Write,[IO.FileShare]::None)
try {
    $local='scripts/optimization/export_replay_capture.py';$remote='/home/ubuntu/export_replay_capture01.py'
    & $pwsh -NoProfile -File scripts/m212_uart_put_file_chunked.ps1 -LocalPath $local -RemotePath $remote -LogPrefix "$logs/upload" | Out-Null
    if($LASTEXITCODE -ne 0){throw 'Upload failed'}
    $hash=(Get-FileHash $local).Hash.ToLowerInvariant()
    & $pwsh -NoProfile -File scripts/m75c_uart_command.ps1 -Command "/usr/local/share/pynq-venv/bin/python -B $remote $hash $($board.capture_manifest_sha256)" -LogPath "$logs/run.log" -TimeoutSeconds 120 -MarkerPrefix '__CAPTURE_RC_'
    exit $LASTEXITCODE
} finally {$lock.Dispose();Remove-Item -LiteralPath $lockPath}
