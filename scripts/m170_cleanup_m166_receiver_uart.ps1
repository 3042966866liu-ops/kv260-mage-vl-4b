[CmdletBinding()]
param([string]$Port='COM3',[string]$ExpectedFtdiSerial='XFL1PL5N11BJB',[string]$Attempt='01')
$ErrorActionPreference='Stop';Set-StrictMode -Version Latest
$workspace=(Resolve-Path (Join-Path $PSScriptRoot '..')).Path
$local='scripts\m170_cleanup_m166_receiver.py';$path=(Resolve-Path -LiteralPath (Join-Path $workspace $local)).Path;$hash=(Get-FileHash -Algorithm SHA256 -LiteralPath $path).Hash.ToLowerInvariant()
$remote='/home/ubuntu/tellme_m120_m89x2_20260901/bootstrap/m170_cleanup_m166_receiver.py';$upload="tmp\m170_cleanup\upload_${Attempt}_uart.log";$run="tmp\m170_cleanup\run_${Attempt}_uart.log"
foreach($r in @($upload,$run)){if(Test-Path -LiteralPath (Join-Path $workspace $r)){throw "M170 output exists: $r"}}
& (Join-Path $PSScriptRoot 'm75c_uart_put_file_base64.ps1') -LocalPath $local -RemotePath $remote -Port $Port -ExpectedFtdiSerial $ExpectedFtdiSerial -LogPath $upload -TimeoutSeconds 120
& (Join-Path $PSScriptRoot 'm75c_uart_command.ps1') -Command "python3 $remote $hash" -Port $Port -ExpectedFtdiSerial $ExpectedFtdiSerial -LogPath $run -TimeoutSeconds 120
if((Get-Content -LiteralPath (Join-Path $workspace $run)-Raw)-notmatch'M170_M166_EXACT_RECEIVER_CLEANUP_PASS'){throw 'M170 cleanup marker missing'}
Write-Output 'M170_M166_RECEIVER_CLEANUP_UART_PASS'
