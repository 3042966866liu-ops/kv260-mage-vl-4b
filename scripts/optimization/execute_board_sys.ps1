[CmdletBinding()]
param([ValidateSet(1,2,3,5)][int]$Revision=2,[ValidateRange(1,99)][int]$ImportAttempt=3)
$ErrorActionPreference='Stop'
Set-StrictMode -Version Latest
$workspace=(Resolve-Path (Join-Path $PSScriptRoot '..\..')).Path
$pwsh='C:\Users\30429\.cache\codex-runtimes\codex-primary-runtime\dependencies\native\powershell\pwsh.exe'
$gate=Get-Content -LiteralPath (Join-Path $workspace ('deployment/mage_vl4b/optimization_v1/gates/G01-SYS-imports/attempt_{0:00}/result.json' -f $ImportAttempt)) -Raw | ConvertFrom-Json
if($gate.status -ne 'PASS'){throw 'Imports not verified'}
$manifest=Join-Path $workspace ('deployment/mage_vl4b/optimization_v1/candidates/OP01-SYS-{0:00}/PACKAGE_MANIFEST.json' -f $Revision)
$digest=(Get-FileHash -LiteralPath $manifest -Algorithm SHA256).Hash.ToLowerInvariant()
if($digest -ne $gate.board.package_manifest_sha256){throw 'Import candidate identity changed'}
if($Revision -ge 3 -and -not $gate.board.decode_trace_interface_verified){throw 'Decode diagnostic interfaces not verified'}
if($Revision -eq 5){
    $smoke=Get-Content deployment/mage_vl4b/optimization_v1/gates/G01-diagnostic-smoke/attempt_01/result.json -Raw | ConvertFrom-Json
    if($smoke.status -ne 'PASS_SOFTWARE_ONLY' -or $smoke.board.package_manifest_sha256 -ne $digest){throw 'Diagnostic smoke identity mismatch'}
}
$remote=('/home/ubuntu/tellme_m120_m89x2_20260901/optimization_v1/OP01-SYS-{0:00}' -f $Revision)
$logs=('tmp/op01_sys{0:00}' -f $Revision)
$result=('/home/ubuntu/tellme_m120_m89x2_20260901/optimization_v1/results/sys{0:00}.json' -f $Revision)
$lockPath=Join-Path $workspace 'deployment/mage_vl4b/optimization_v1/control.lock'
$lock=[IO.File]::Open($lockPath,[IO.FileMode]::CreateNew,[IO.FileAccess]::Write,[IO.FileShare]::None)
try {
    & $pwsh -NoProfile -File scripts/m255_require_uart_shell.ps1 -LogPath "$logs/shell.log"
    if($LASTEXITCODE -ne 0){throw 'UART shell unavailable'}
    & $pwsh -NoProfile -File scripts/m75c_uart_command.ps1 -Command 'sudo -n true' -LogPath "$logs/sudo.log"
    if($LASTEXITCODE -ne 0){throw 'Authorization missing; no overlay attempted'}
    $command="sudo -n bash $remote/run_board_sys.sh --manifest-sha256 $digest --result $result --max-new-tokens 2"
    if($Revision -ge 3){
        $checkpoint=('/home/ubuntu/tellme_m120_m89x2_20260901/optimization_v1/decode_checkpoints/SYS{0:00}-prefill' -f $Revision)
        $command+=" --decode-diagnostic --checkpoint-directory $checkpoint"
    }
    & $pwsh -NoProfile -File scripts/m75c_uart_command.ps1 -Command $command -LogPath "$logs/run.log" -TimeoutSeconds 7300 -MarkerPrefix '__OP01_SYS_RC_'
    exit $LASTEXITCODE
} finally {$lock.Dispose();Remove-Item -LiteralPath $lockPath}
