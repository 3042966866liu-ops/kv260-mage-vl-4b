[CmdletBinding()]
param()
$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest
$workspace = (Resolve-Path (Join-Path $PSScriptRoot '../..')).Path
$local = 'deployment/mage_vl4b/optimization_v1/candidates/M345-fixed-video-01'
$remote = '/home/ubuntu/m345_fixed_video_01'
$manifest = Get-Content -LiteralPath (Join-Path $workspace "$local/PACKAGE_MANIFEST.json") -Raw -Encoding UTF8 | ConvertFrom-Json
foreach ($name in (@('PACKAGE_MANIFEST.json') + @($manifest.files | ForEach-Object path))) {
    & (Join-Path $workspace 'scripts/m212_uart_put_file_chunked.ps1') -LocalPath "$local/$name" -RemotePath "$remote/$name" -LogPrefix "tmp/m345/upload_$($name.Replace('.','_'))" -ChunkBytes 1800 -TimeoutSeconds 25
    if (-not $?) { throw "M345 upload failed: $name" }
}
Write-Output 'M345_VIDEO_TRANSFER_PASS'
