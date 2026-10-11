$ErrorActionPreference='Stop'
Set-StrictMode -Version Latest
$pwsh='C:\Users\30429\.cache\codex-runtimes\codex-primary-runtime\dependencies\native\powershell\pwsh.exe'
$lockPath='deployment/mage_vl4b/optimization_v1/control.lock'
$lock=[IO.File]::Open((Join-Path (Get-Location) $lockPath),[IO.FileMode]::CreateNew,[IO.FileAccess]::Write,[IO.FileShare]::None)
try {
    & $pwsh -NoProfile -File scripts/m255_require_uart_shell.ps1 -LogPath tmp/op01_sys_import06/shell.log
    if($LASTEXITCODE -ne 0){throw 'No shell'}
    $items=@(
        @('scripts/optimization/stage_sys05_delta.py','stage.py'),
        @('deployment/mage_vl4b/optimization_v1/candidates/OP01-SYS-05/PACKAGE_MANIFEST.json','PACKAGE_MANIFEST.json'),
        @('deployment/mage_vl4b/optimization_v1/candidates/OP01-SYS-05/transfer_trace.py','transfer_trace.py')
    )
    foreach($item in $items){
        & $pwsh -NoProfile -File scripts/m212_uart_put_file_chunked.ps1 -LocalPath $item[0] -RemotePath "/home/ubuntu/sys05_delta/$($item[1])" -LogPrefix "tmp/op01_sys_import06/upload_$($item[1])" | Out-Null
        if($LASTEXITCODE -ne 0){throw 'Delta upload failed'}
    }
    $scriptHash=(Get-FileHash scripts/optimization/stage_sys05_delta.py).Hash.ToLowerInvariant()
    $manifestHash=(Get-FileHash deployment/mage_vl4b/optimization_v1/candidates/OP01-SYS-05/PACKAGE_MANIFEST.json).Hash.ToLowerInvariant()
    & $pwsh -NoProfile -File scripts/m75c_uart_command.ps1 -Command "/usr/local/share/pynq-venv/bin/python -B /home/ubuntu/sys05_delta/stage.py $scriptHash $manifestHash" -LogPath tmp/op01_sys_import06/stage.log -TimeoutSeconds 60
    if($LASTEXITCODE -ne 0){throw 'Clean delta stage failed'}
    $remote='/home/ubuntu/tellme_m120_m89x2_20260901/optimization_v1/OP01-SYS-05'
    # Import-only checks do not require root. Use a user-owned result path.
    & $pwsh -NoProfile -File scripts/m75c_uart_command.ps1 -Command "bash $remote/run_board_sys.sh --manifest-sha256 $manifestHash --result /home/ubuntu/sys05_delta/import06.json --imports-only" -LogPath tmp/op01_sys_import06/run.log -TimeoutSeconds 120 -MarkerPrefix '__OP01_IMPORT_RC_'
    exit $LASTEXITCODE
} finally {$lock.Dispose();Remove-Item -LiteralPath $lockPath}
