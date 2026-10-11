$ErrorActionPreference='Stop'
$taskRoot=(Resolve-Path (Join-Path $PSScriptRoot '../..')).Path
$taskPython='C:\Users\30429\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe'
$taskUart=Join-Path $taskRoot 'scripts/m75c_uart_command.ps1'
& $taskPython -B (Join-Path $PSScriptRoot 'm368_saved_recovery.py') Package
if($LASTEXITCODE -ne 0){throw 'Recovery preparation failed'}
& $taskUart -Command 'sudo -n true' -LogPath 'tmp/m368_saved_recovery_01/sudo.log' -TimeoutSeconds 15 -MarkerPrefix '__M368_RECOVERY_SUDO_RC_'
$taskPackage='deployment/mage_vl4b/optimization_v1/candidates/M368-saved-byte-recovery-01'
$taskDigest=(Get-FileHash (Join-Path $taskRoot "$taskPackage/PACKAGE_MANIFEST.json") -Algorithm SHA256).Hash.ToLowerInvariant()
foreach($taskName in @('PACKAGE_MANIFEST.json','export_saved.py','SHA256SUMS')){
 & (Join-Path $taskRoot 'scripts/m212_uart_put_file_chunked.ps1') -LocalPath "$taskPackage/$taskName" -RemotePath "/home/ubuntu/m368_saved_recovery_01/$taskName" -LogPrefix "tmp/m368_saved_recovery_01/upload_$($taskName.Replace('.','_'))" -ChunkBytes 900 -TimeoutSeconds 25
}
& $taskUart -Command "sudo -n /usr/local/share/pynq-venv/bin/python -B /home/ubuntu/m368_saved_recovery_01/export_saved.py $taskDigest" -LogPath 'tmp/m368_saved_recovery_01/recover.log' -TimeoutSeconds 60 -MarkerPrefix '__M368_RECOVERY_RC_'
& $taskPython -B (Join-Path $PSScriptRoot 'm368_saved_recovery.py') Finish
if($LASTEXITCODE -ne 0){throw 'Saved byte recovery failed; no hardware rerun'}
