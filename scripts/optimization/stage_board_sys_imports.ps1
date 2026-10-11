[CmdletBinding()]
param([ValidateSet(1,2,3,4)][int]$Revision=2,[ValidateRange(1,99)][int]$Attempt=3)
$ErrorActionPreference='Stop'
Set-StrictMode -Version Latest
$workspace=(Resolve-Path (Join-Path $PSScriptRoot '..\..')).Path
$pwsh='C:\Users\30429\.cache\codex-runtimes\codex-primary-runtime\dependencies\native\powershell\pwsh.exe'
$local=('deployment/mage_vl4b/optimization_v1/candidates/OP01-SYS-{0:00}' -f $Revision)
$remote=('/home/ubuntu/tellme_m120_m89x2_20260901/optimization_v1/OP01-SYS-{0:00}' -f $Revision)
$logs=('tmp/op01_sys_import{0:00}' -f $Attempt)
$result=('/home/ubuntu/tellme_m120_m89x2_20260901/optimization_v1/results/sys_import{0:00}.json' -f $Attempt)
$manifest=Join-Path $workspace "$local/PACKAGE_MANIFEST.json"
$digest=(Get-FileHash -LiteralPath $manifest -Algorithm SHA256).Hash.ToLowerInvariant()
$members=Get-Content -LiteralPath $manifest -Raw | ConvertFrom-Json
foreach($item in $members.files){
    if((Get-FileHash -LiteralPath (Join-Path $workspace "$local/$($item.path)") -Algorithm SHA256).Hash.ToLowerInvariant() -ne $item.sha256){throw 'Package drift'}
}
$lockPath=Join-Path $workspace 'deployment/mage_vl4b/optimization_v1/control.lock'
$lock=[IO.File]::Open($lockPath,[IO.FileMode]::CreateNew,[IO.FileAccess]::Write,[IO.FileShare]::None)
try {
    & $pwsh -NoProfile -File scripts/m255_require_uart_shell.ps1 -LogPath "$logs/shell.log"
    if($LASTEXITCODE -ne 0){throw 'UART shell unavailable'}
    foreach($name in @('PACKAGE_MANIFEST.json')+@($members.files.path)){
        & $pwsh -NoProfile -File scripts/m212_uart_put_file_chunked.ps1 -LocalPath "$local/$name" -RemotePath "$remote/$name" -LogPrefix "$logs/upload_$name" | Out-Null
        if($LASTEXITCODE -ne 0){throw "Upload failed: $name"}
        Write-Output "OP01_SYS_MEMBER_VERIFIED $name"
    }
    & $pwsh -NoProfile -File scripts/m75c_uart_command.ps1 -Command 'sudo -n true' -LogPath "$logs/sudo.log"
    if($LASTEXITCODE -ne 0){throw 'Result directory requires authorized root; do not run'}
    $command="sudo -n bash $remote/run_board_sys.sh --manifest-sha256 $digest --result $result --imports-only"
    & $pwsh -NoProfile -File scripts/m75c_uart_command.ps1 -Command $command -LogPath "$logs/run.log" -TimeoutSeconds 120 -MarkerPrefix '__OP01_IMPORT_RC_'
    exit $LASTEXITCODE
} finally {$lock.Dispose();Remove-Item -LiteralPath $lockPath}
