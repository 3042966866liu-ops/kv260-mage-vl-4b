[CmdletBinding()]
param()
$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest
$workspace = (Resolve-Path (Join-Path $PSScriptRoot '../..')).Path
$local = 'deployment/mage_vl4b/optimization_v1/candidates/M339-prefill-profile-04'
$remote = '/home/ubuntu/m339_prefill_profile_04'
$manifest = Get-Content -LiteralPath (Join-Path $workspace "$local/PACKAGE_MANIFEST.json") -Raw | ConvertFrom-Json
$names = @('PACKAGE_MANIFEST.json') + @($manifest.files | ForEach-Object path)
foreach ($name in $names) {
    & (Join-Path $workspace 'scripts/m212_uart_put_file_chunked.ps1') -LocalPath "$local/$name" -RemotePath "$remote/$name" -LogPrefix "tmp/m339/upload_$($name.Replace('.','_'))" -ChunkBytes 1800 -TimeoutSeconds 25
    if (-not $?) { throw "M339 upload failed: $name" }
}
Write-Output 'M339_PROFILE_PACKAGE_TRANSFER_PASS'
