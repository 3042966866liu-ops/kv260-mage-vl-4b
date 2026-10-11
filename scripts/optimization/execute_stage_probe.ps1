$ErrorActionPreference='Stop'
Set-StrictMode -Version Latest
$pwsh='C:\Users\30429\.cache\codex-runtimes\codex-primary-runtime\dependencies\native\powershell\pwsh.exe'
$local='deployment/mage_vl4b/optimization_v1/candidates/OP01-stage-01'
$remote='/home/ubuntu/tellme_m120_m89x2_20260901/optimization_v1/OP01-stage-01'
$hash=(Get-FileHash "$local/PACKAGE_MANIFEST.json" -Algorithm SHA256).Hash.ToLowerInvariant()
$lockPath=Join-Path (Get-Location) 'deployment/mage_vl4b/optimization_v1/control.lock'
$lock=[IO.File]::Open($lockPath,[IO.FileMode]::CreateNew,[IO.FileAccess]::Write,[IO.FileShare]::None)
try {
 & $pwsh -NoProfile -File scripts/m255_require_uart_shell.ps1 -LogPath tmp/op01_stage01/shell.log
 if($LASTEXITCODE -ne 0){throw 'UART unavailable'}
 & $pwsh -NoProfile -File scripts/m75c_uart_command.ps1 -Command 'sudo -n true' -LogPath tmp/op01_stage01/sudo.log
 if($LASTEXITCODE -ne 0){throw 'Authorization unavailable'}
 foreach($name in @('PACKAGE_MANIFEST.json','stage_transfer_probe.py','run_stage_probe.sh')){
  & $pwsh -NoProfile -File scripts/m212_uart_put_file_chunked.ps1 -LocalPath "$local/$name" -RemotePath "$remote/$name" -LogPrefix "tmp/op01_stage01/upload_$name" | Out-Null
  if($LASTEXITCODE -ne 0){throw "Upload failed: $name"}
 }
 & $pwsh -NoProfile -File scripts/m75c_uart_command.ps1 -Command "sudo -n bash $remote/run_stage_probe.sh --manifest-sha256 $hash --result /home/ubuntu/tellme_m120_m89x2_20260901/optimization_v1/results/stage01.json" -LogPath tmp/op01_stage01/run.log -TimeoutSeconds 240 -MarkerPrefix '__OP01_STAGE_RC_'
 exit $LASTEXITCODE
} finally {$lock.Dispose();Remove-Item -LiteralPath $lockPath}
