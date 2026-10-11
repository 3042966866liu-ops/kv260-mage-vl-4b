[CmdletBinding()]
param()
$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest
$workspace = (Resolve-Path (Join-Path $PSScriptRoot '../..')).Path
$local = 'deployment/mage_vl4b/optimization_v1/candidates/M342-prefetch-fixture-01'
$remote = '/home/ubuntu/m342_prefetch_fixture_01'
$manifest = Get-Content -LiteralPath (Join-Path $workspace "$local/PACKAGE_MANIFEST.json") -Raw | ConvertFrom-Json
$names = @('PACKAGE_MANIFEST.json') + @($manifest.files | ForEach-Object path)
foreach ($name in $names) {
    & (Join-Path $workspace 'scripts/m212_uart_put_file_chunked.ps1') -LocalPath "$local/$name" -RemotePath "$remote/$name" -LogPrefix "tmp/m342/upload_$($name.Replace('.','_'))" -ChunkBytes 1800 -TimeoutSeconds 25
    if (-not $?) { throw "M342 fixture gate upload failed: $name" }
}
Write-Output 'M342_FIXTURE_GATE_TRANSFER_PASS'
