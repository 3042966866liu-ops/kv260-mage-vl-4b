$ErrorActionPreference='Stop'
Set-StrictMode -Version Latest
$pwsh='C:\Users\30429\.cache\codex-runtimes\codex-primary-runtime\dependencies\native\powershell\pwsh.exe'
$local='deployment/mage_vl4b/optimization_v1/candidates/OP01-LIFECYCLE-01'
$remote='/home/ubuntu/tellme_m120_m89x2_20260901/optimization_v1/OP01-LIFECYCLE-01'
$logs='tmp/op01_lifecycle_import01';$lockPath='deployment/mage_vl4b/optimization_v1/control.lock'
$lock=[IO.File]::Open((Join-Path (Get-Location) $lockPath),[IO.FileMode]::CreateNew,[IO.FileAccess]::Write,[IO.FileShare]::None)
try {
    & $pwsh -NoProfile -File scripts/m255_require_uart_shell.ps1 -LogPath "$logs/shell.log"
    if($LASTEXITCODE -ne 0){throw 'UART shell unavailable'}
    $manifest=Get-Content "$local/PACKAGE_MANIFEST.json" -Raw|ConvertFrom-Json
    foreach($name in (@('PACKAGE_MANIFEST.json')+@($manifest.files.path))){
        & $pwsh -NoProfile -File scripts/m212_uart_put_file_chunked.ps1 -LocalPath "$local/$name" -RemotePath "$remote/$name" -LogPrefix "$logs/upload_$name" | Out-Null
        if($LASTEXITCODE -ne 0){throw 'Lifecycle package upload failed'}
    }
    $hash=(Get-FileHash "$local/PACKAGE_MANIFEST.json").Hash.ToLowerInvariant()
    & $pwsh -NoProfile -File scripts/m75c_uart_command.ps1 -Command "bash $remote/run_board_replay.sh --manifest-sha256 $hash --result /home/ubuntu/op01_lifecycle_import01.json --imports-only --lifecycle" -LogPath "$logs/run.log" -TimeoutSeconds 180 -MarkerPrefix '__LIFECYCLE_IMPORT_RC_'
    exit $LASTEXITCODE
} finally {$lock.Dispose();Remove-Item -LiteralPath $lockPath}
