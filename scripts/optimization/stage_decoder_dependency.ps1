[CmdletBinding()]
param()
$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest
$workspace = (Resolve-Path (Join-Path $PSScriptRoot '..\..')).Path
$pwsh = 'C:\Users\30429\.cache\codex-runtimes\codex-primary-runtime\dependencies\native\powershell\pwsh.exe'
$local = 'deployment\mage_vl4b\optimization_v1\candidates\OP00-decoder-dependency-01'
$remote = '/home/ubuntu/tellme_m120_m89x2_20260901/optimization_v1/OP00-decoder-dependency-01'
$manifest = Join-Path $workspace "$local\PACKAGE_MANIFEST.json"
$digest = (Get-FileHash -LiteralPath $manifest -Algorithm SHA256).Hash.ToLowerInvariant()
$members = Get-Content -LiteralPath $manifest -Raw | ConvertFrom-Json
foreach ($item in $members.files) {
    if ((Get-FileHash -LiteralPath (Join-Path $workspace "$local\$($item.path)") -Algorithm SHA256).Hash.ToLowerInvariant() -ne $item.sha256) { throw 'Package drift' }
}
$lockPath = Join-Path $workspace 'deployment\mage_vl4b\optimization_v1\control.lock'
$lock = [IO.File]::Open($lockPath,[IO.FileMode]::CreateNew,[IO.FileAccess]::Write,[IO.FileShare]::None)
try {
    & $pwsh -NoProfile -File scripts/m255_require_uart_shell.ps1 -LogPath tmp/op00_decoder_dependency01/shell.log
    if ($LASTEXITCODE -ne 0) { throw 'UART shell unavailable' }
    & $pwsh -NoProfile -File scripts/m75c_uart_command.ps1 -Command 'sudo -n true' -LogPath tmp/op00_decoder_dependency01/sudo.log
    if ($LASTEXITCODE -ne 0) { throw 'UART authorization expired; not run' }
    foreach ($name in @('PACKAGE_MANIFEST.json') + @($members.files.path)) {
        & $pwsh -NoProfile -File scripts/m212_uart_put_file_chunked.ps1 -LocalPath "$local\$name" -RemotePath "$remote/$name" -LogPrefix "tmp/op00_decoder_dependency01/upload_$name" | Out-Null
        if ($LASTEXITCODE -ne 0) { throw "Upload failed: $name" }
        Write-Output "BOOTSTRAP_FILE_VERIFIED $name"
    }
    $command = "sudo -n bash $remote/run_decoder_dependency.sh --manifest-sha256 $digest"
    & $pwsh -NoProfile -File scripts/m75c_uart_command.ps1 -Command $command -LogPath tmp/op00_decoder_dependency01/run.log -TimeoutSeconds 660 -MarkerPrefix '__OP00_DECODER_RC_'
    $gateCode = $LASTEXITCODE
    Write-Output "OP00_DECODER_RAW_EXIT=$gateCode"
    exit $gateCode
} finally {
    $lock.Dispose()
    Remove-Item -LiteralPath $lockPath
}
