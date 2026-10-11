[CmdletBinding()]
param([string]$Port='COM3',[string]$ExpectedFtdiSerial='XFL1PL5N11BJB',[string]$Attempt='01',[int]$TimeoutSeconds=1800)
$ErrorActionPreference='Stop'; Set-StrictMode -Version Latest
$workspace=(Resolve-Path (Join-Path $PSScriptRoot '..')).Path
$build=Get-Content -LiteralPath (Join-Path $workspace 'deployment\mage_vl4b\M193_PILLOW_BOOTSTRAP_RESULT.json') -Raw|ConvertFrom-Json
$package=(Resolve-Path -LiteralPath (Join-Path $workspace $build.directory)).Path
$manifestPath=Join-Path $package 'PACKAGE_MANIFEST.json'; $manifest=Get-Content -LiteralPath $manifestPath -Raw|ConvertFrom-Json
$manifestHash=(Get-FileHash -Algorithm SHA256 -LiteralPath $manifestPath).Hash.ToLowerInvariant()
if($build.status-ne'PASS' -or $manifestHash-ne$build.package_manifest_sha256){throw'M193_BOOTSTRAP_FAIL'}
$remote='/home/ubuntu/tellme_m120_m89x2_20260901/m193_bootstrap'
& (Join-Path $PSScriptRoot 'm75c_uart_command.ps1') -Command 'sudo -n true' -Port $Port -ExpectedFtdiSerial $ExpectedFtdiSerial -LogPath "tmp\m193_pillow\sudo_${Attempt}.log" -TimeoutSeconds 30
foreach($entry in @($manifest.files)+@([pscustomobject]@{path='PACKAGE_MANIFEST.json'})){
  $name=[string]$entry.path
  & (Join-Path $PSScriptRoot 'm75c_uart_put_file_base64.ps1') -LocalPath ((Resolve-Path (Join-Path $package $name)).Path.Substring($workspace.Length+1)) -RemotePath "$remote/$name" -Port $Port -ExpectedFtdiSerial $ExpectedFtdiSerial -LogPath "tmp\m193_pillow\upload_${Attempt}_${name}.log" -TimeoutSeconds 180
}
& (Join-Path $PSScriptRoot 'm75c_uart_command.ps1') -Command "python3 $remote/m193_verify_bootstrap.py --root $remote --expected-manifest-sha256 $manifestHash" -Port $Port -ExpectedFtdiSerial $ExpectedFtdiSerial -LogPath "tmp\m193_pillow\verify_${Attempt}.log" -TimeoutSeconds 180
& (Join-Path $PSScriptRoot 'm75c_uart_command.ps1') -Command "sudo -n bash $remote/m193_run_pillow_repair.sh" -Port $Port -ExpectedFtdiSerial $ExpectedFtdiSerial -LogPath "tmp\m193_pillow\repair_${Attempt}.log" -TimeoutSeconds $TimeoutSeconds
