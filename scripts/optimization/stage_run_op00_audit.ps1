[CmdletBinding()]
param()
$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest
$workspace = (Resolve-Path (Join-Path $PSScriptRoot '..\..')).Path
$pwsh = 'C:\Users\30429\.cache\codex-runtimes\codex-primary-runtime\dependencies\native\powershell\pwsh.exe'
$packageRel = 'deployment\mage_vl4b\optimization_v1\candidates\OP00-audit-01'
$remote = '/home/ubuntu/tellme_m120_m89x2_20260901/optimization_v1/OP00-audit-01'
$manifestPath = Join-Path $workspace "$packageRel\PACKAGE_MANIFEST.json"
$manifestHash = (Get-FileHash -LiteralPath $manifestPath -Algorithm SHA256).Hash.ToLowerInvariant()
if ($manifestHash -ne '062ba312660f570c5f502a9b70f3257dcc206638c8ccf499a87bc5ecd99fcd74') { throw 'Package drift' }
$lockPath = Join-Path $workspace 'deployment\mage_vl4b\optimization_v1\control.lock'
$lockStream = [IO.File]::Open($lockPath,[IO.FileMode]::CreateNew,[IO.FileAccess]::Write,[IO.FileShare]::None)
try {
    & $pwsh -NoProfile -File (Join-Path $workspace 'scripts\m255_require_uart_shell.ps1') -LogPath 'tmp/op00_audit01/shell.log'
    if ($LASTEXITCODE -ne 0) { throw 'Existing UART shell required' }
    & $pwsh -NoProfile -File (Join-Path $workspace 'scripts\m75c_uart_command.ps1') -Command 'sudo -n true' -LogPath 'tmp/op00_audit01/sudo.log'
    if ($LASTEXITCODE -ne 0) { throw 'Same-UART authorization expired; no upload' }
    foreach ($name in @('PACKAGE_MANIFEST.json','op00_board_audit.py','run_op00_board_audit.sh')) {
        & $pwsh -NoProfile -File (Join-Path $workspace 'scripts\m212_uart_put_file_chunked.ps1') -LocalPath "$packageRel\$name" -RemotePath "$remote/$name" -LogPrefix "tmp/op00_audit01/upload_$name"
        if ($LASTEXITCODE -ne 0) { throw "Upload failed: $name" }
    }
    $command = "sudo -n bash $remote/run_op00_board_audit.sh $manifestHash /home/ubuntu/tellme_m120_m89x2_20260901/optimization_v1/results/audit01.json"
    & $pwsh -NoProfile -File (Join-Path $workspace 'scripts\m75c_uart_command.ps1') -Command $command -LogPath 'tmp/op00_audit01/run.log' -TimeoutSeconds 55 -MarkerPrefix '__OP00_AUDIT_RC_'
    $gateCode = $LASTEXITCODE
    Write-Output "OP00_AUDIT_RAW_LAUNCH_EXIT=$gateCode"
    exit $gateCode
} finally {
    $lockStream.Dispose()
    Remove-Item -LiteralPath $lockPath
}
