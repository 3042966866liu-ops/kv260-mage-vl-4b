[CmdletBinding()]
param()
$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest
$workspace = (Resolve-Path (Join-Path $PSScriptRoot '../..')).Path
$local = 'deployment/mage_vl4b/optimization_v1/candidates/M341-build-id-01'
$remote = '/home/ubuntu/m341_build_id_01'
$manifest = Get-Content -LiteralPath (Join-Path $workspace "$local/PACKAGE_MANIFEST.json") -Raw | ConvertFrom-Json
$names = @('PACKAGE_MANIFEST.json') + @($manifest.files | ForEach-Object path)
foreach ($name in $names) {
    & (Join-Path $workspace 'scripts/m212_uart_put_file_chunked.ps1') -LocalPath "$local/$name" -RemotePath "$remote/$name" -LogPrefix "tmp/m341/upload_$($name.Replace('.','_'))" -ChunkBytes 1800 -TimeoutSeconds 25
    if (-not $?) { throw "M341 build gate upload failed: $name" }
}
Write-Output 'M341_BUILD_GATE_TRANSFER_PASS'
