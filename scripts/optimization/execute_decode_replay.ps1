$ErrorActionPreference='Stop'
Set-StrictMode -Version Latest
$pwsh='C:\Users\30429\.cache\codex-runtimes\codex-primary-runtime\dependencies\native\powershell\pwsh.exe'
$remote='/home/ubuntu/tellme_m120_m89x2_20260901/optimization_v1/OP01-REPLAY-01'
$logs='tmp/op01_replay01';$lockPath='deployment/mage_vl4b/optimization_v1/control.lock'
$gate=Get-Content deployment/mage_vl4b/optimization_v1/gates/G01-replay-import/attempt_01/result.json -Raw|ConvertFrom-Json
$hash=(Get-FileHash deployment/mage_vl4b/optimization_v1/candidates/OP01-REPLAY-01/PACKAGE_MANIFEST.json).Hash.ToLowerInvariant()
if($gate.status -ne 'PASS_IMPORT_RESTORE_ONLY' -or $gate.summary.package_manifest_sha256 -ne $hash){throw 'Import identity missing'}
$lock=[IO.File]::Open((Join-Path (Get-Location) $lockPath),[IO.FileMode]::CreateNew,[IO.FileAccess]::Write,[IO.FileShare]::None)
try {
    & $pwsh -NoProfile -File scripts/m255_require_uart_shell.ps1 -LogPath "$logs/shell.log"
    if($LASTEXITCODE -ne 0){throw 'UART shell unavailable'}
    & $pwsh -NoProfile -File scripts/m75c_uart_command.ps1 -Command 'sudo -n true' -LogPath "$logs/sudo.log" -TimeoutSeconds 15 -MarkerPrefix '__REPLAY_SUDO_RC_'
    if($LASTEXITCODE -ne 0){throw 'Sudo authorization missing; no FPGA loaded'}
    & $pwsh -NoProfile -File scripts/m75c_uart_command.ps1 -Command "sudo -n bash $remote/run_board_replay.sh --manifest-sha256 $hash --result /home/ubuntu/op01_replay01.json" -LogPath "$logs/run.log" -TimeoutSeconds 600 -MarkerPrefix '__REPLAY_RC_'
    exit $LASTEXITCODE
} finally {$lock.Dispose();Remove-Item -LiteralPath $lockPath}
