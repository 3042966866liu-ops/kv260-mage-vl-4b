[CmdletBinding()]
param()
$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest
$workspace = (Resolve-Path (Join-Path $PSScriptRoot '..\..')).Path
$pwsh = 'C:\Users\30429\.cache\codex-runtimes\codex-primary-runtime\dependencies\native\powershell\pwsh.exe'
$local = 'deployment\mage_vl4b\optimization_v1\candidates\OP00-model-inventory-01'
$remote = '/home/ubuntu/tellme_m120_m89x2_20260901/optimization_v1/OP00-model-inventory-01'
$digest = 'a6ac2b6cad9202b2185140453640f34f52a9bc33122938dbae93e43ef2e4df3f'
$manifest = Join-Path $workspace "$local\PACKAGE_MANIFEST.json"
if ((Get-FileHash -LiteralPath $manifest -Algorithm SHA256).Hash.ToLowerInvariant() -ne $digest) { throw 'Package drift' }
$members = Get-Content -LiteralPath $manifest -Raw | ConvertFrom-Json
$lockPath = Join-Path $workspace 'deployment\mage_vl4b\optimization_v1\control.lock'
$lock = [IO.File]::Open($lockPath,[IO.FileMode]::CreateNew,[IO.FileAccess]::Write,[IO.FileShare]::None)
try {
    & $pwsh -NoProfile -File scripts/m255_require_uart_shell.ps1 -LogPath tmp/op00_model_inventory01/shell.log
    if ($LASTEXITCODE -ne 0) { throw 'UART shell unavailable' }
    & $pwsh -NoProfile -File scripts/m75c_uart_command.ps1 -Command 'sudo -n true' -LogPath tmp/op00_model_inventory01/sudo.log
    if ($LASTEXITCODE -ne 0) { throw 'UART authorization expired; not run' }
    foreach ($name in @('PACKAGE_MANIFEST.json') + @($members.files.path)) {
        & $pwsh -NoProfile -File scripts/m212_uart_put_file_chunked.ps1 -LocalPath "$local\$name" -RemotePath "$remote/$name" -LogPrefix "tmp/op00_model_inventory01/upload_$name"
        if ($LASTEXITCODE -ne 0) { throw "Upload failed: $name" }
    }
    $command = "sudo -n env PYTHONDONTWRITEBYTECODE=1 /usr/local/share/pynq-venv/bin/python $remote/op00_model_inventory.py --manifest-sha256 $digest --result /home/ubuntu/tellme_m120_m89x2_20260901/optimization_v1/results/model_inventory01.json"
    & $pwsh -NoProfile -File scripts/m75c_uart_command.ps1 -Command $command -LogPath tmp/op00_model_inventory01/run.log -TimeoutSeconds 300 -MarkerPrefix '__OP00_MODEL_RC_'
    $gateCode = $LASTEXITCODE
    Write-Output "OP00_MODEL_RAW_EXIT=$gateCode"
    exit $gateCode
} finally {
    $lock.Dispose()
    Remove-Item -LiteralPath $lockPath
}
