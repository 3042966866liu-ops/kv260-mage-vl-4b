$ErrorActionPreference='Stop'
Set-StrictMode -Version Latest
$pwsh='C:\Users\30429\.cache\codex-runtimes\codex-primary-runtime\dependencies\native\powershell\pwsh.exe'
$remote='/home/ubuntu/op01_checkpoint_preflight_01';$logs='tmp/op01_checkpoint_preflight01'
$lockPath='deployment/mage_vl4b/optimization_v1/control.lock'
$lock=[IO.File]::Open((Join-Path (Get-Location) $lockPath),[IO.FileMode]::CreateNew,[IO.FileAccess]::Write,[IO.FileShare]::None)
try {
    & $pwsh -NoProfile -File scripts/m255_require_uart_shell.ps1 -LogPath "$logs/shell.log"
    if($LASTEXITCODE -ne 0){throw 'UART shell unavailable'}
    $plan='deployment/mage_vl4b/optimization_v1/runs/OP01-checkpoint-preflight-01/plan.json'
    $script='scripts/optimization/checkpoint_preflight.py'
    foreach($item in @(@($plan,'plan.json'),@($script,'probe.py'))){
        & $pwsh -NoProfile -File scripts/m212_uart_put_file_chunked.ps1 -LocalPath $item[0] -RemotePath "$remote/$($item[1])" -LogPrefix "$logs/upload_$($item[1])" | Out-Null
        if($LASTEXITCODE -ne 0){throw 'Checkpoint probe upload failed'}
    }
    $scriptHash=(Get-FileHash $script).Hash.ToLowerInvariant();$planHash=(Get-FileHash $plan).Hash.ToLowerInvariant()
    & $pwsh -NoProfile -File scripts/m75c_uart_command.ps1 -Command "/usr/local/share/pynq-venv/bin/python -B $remote/probe.py $scriptHash $planHash" -LogPath "$logs/run.log" -TimeoutSeconds 120 -MarkerPrefix '__CHECKPOINT_RC_'
    exit $LASTEXITCODE
} finally {$lock.Dispose();Remove-Item -LiteralPath $lockPath}
