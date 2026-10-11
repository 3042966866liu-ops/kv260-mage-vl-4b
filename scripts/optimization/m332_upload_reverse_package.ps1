[CmdletBinding()]
param()

$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest
$workspace = (Resolve-Path (Join-Path $PSScriptRoot '../..')).Path
$local = 'deployment/mage_vl4b/optimization_v1/candidates/M332-parser-scale-video-03'
$remote = '/home/ubuntu/m332_parser_scale_video_pkg_03'
$uploader = Join-Path $workspace 'scripts/m212_uart_put_file_chunked.ps1'
$files = @('PACKAGE_MANIFEST.json', 'm236_prefill_runtime.py', 'run_fixed_video_ab.py', 'run_m332_video_variant.sh', 'SHA256SUMS')
foreach ($name in $files) {
    & $uploader -LocalPath "$local/$name" -RemotePath "$remote/$name" -LogPrefix "tmp/m332/reverse_upload_$($name.Replace('.','_'))" -ChunkBytes 1800 -TimeoutSeconds 45
    if (-not $?) { throw "M332 reverse upload failed: $name" }
}
Write-Output 'M332_REVERSE_PACKAGE_TRANSFER_PASS'
