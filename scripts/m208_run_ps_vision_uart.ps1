[CmdletBinding()]
param([string]$Port='COM3',[string]$ExpectedFtdiSerial='XFL1PL5N11BJB',[string]$Attempt='01',[int]$TimeoutSeconds=6000)
$ErrorActionPreference='Stop';Set-StrictMode -Version Latest
$workspace=(Resolve-Path (Join-Path $PSScriptRoot '..')).Path
$python='C:\Users\30429\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe'
$build=Get-Content -LiteralPath (Join-Path $workspace 'deployment\mage_vl4b\M208_PS_VISION_BOOTSTRAP_RESULT.json') -Raw|ConvertFrom-Json
$package=(Resolve-Path (Join-Path $workspace $build.directory)).Path
$manifestPath=Join-Path $package 'PACKAGE_MANIFEST.json';$manifest=Get-Content -LiteralPath $manifestPath -Raw|ConvertFrom-Json
$manifestHash=(Get-FileHash -Algorithm SHA256 -LiteralPath $manifestPath).Hash.ToLowerInvariant()
if($manifestHash-ne$build.package_manifest_sha256){throw'M208_BOOTSTRAP_HASH_FAIL'}
$remote='/home/ubuntu/tellme_m120_m89x2_20260901/m208_gate'
& (Join-Path $PSScriptRoot 'm75c_uart_command.ps1') -Command 'sudo -n true' -Port $Port -ExpectedFtdiSerial $ExpectedFtdiSerial -LogPath "tmp\m208_ps_vision\sudo_${Attempt}.log" -TimeoutSeconds 30
foreach($entry in @($manifest.files)+@([pscustomobject]@{path='PACKAGE_MANIFEST.json'})){
 $name=[string]$entry.path;$local=(Resolve-Path (Join-Path $package $name)).Path.Substring($workspace.Length+1)
 & (Join-Path $PSScriptRoot 'm75c_uart_put_file_base64.ps1') -LocalPath $local -RemotePath "$remote/$name" -Port $Port -ExpectedFtdiSerial $ExpectedFtdiSerial -LogPath "tmp\m208_ps_vision\upload_${Attempt}_$($name.Replace('/','_')).log" -TimeoutSeconds 240
}
& (Join-Path $PSScriptRoot 'm75c_uart_command.ps1') -Command "python3 $remote/m208_verify_bootstrap.py --root $remote --expected-manifest-sha256 $manifestHash" -Port $Port -ExpectedFtdiSerial $ExpectedFtdiSerial -LogPath "tmp\m208_ps_vision\verify_${Attempt}.log" -TimeoutSeconds 180
$runLog="tmp\m208_ps_vision\run_${Attempt}.log";$formal="deployment\mage_vl4b\M208_M207_PS_VISION_BOARD_RESULT_${Attempt}.json"
try{& (Join-Path $PSScriptRoot 'm75c_uart_command.ps1') -Command "sudo -n bash $remote/m208_run_ps_vision.sh" -Port $Port -ExpectedFtdiSerial $ExpectedFtdiSerial -LogPath $runLog -TimeoutSeconds $TimeoutSeconds}catch{Write-Warning $_}
& $python (Join-Path $PSScriptRoot 'm208_collect_ps_vision_uart.py') --log (Join-Path $workspace $runLog) --result (Join-Path $workspace $formal)
if($LASTEXITCODE-ne 0){throw"M208 gate failed; formal result preserved at $formal"}
Write-Output 'M208_PS_VISION_UART_PASS'
