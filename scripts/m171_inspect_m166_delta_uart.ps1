[CmdletBinding()]
param([string]$Port='COM3',[string]$ExpectedFtdiSerial='XFL1PL5N11BJB',[string]$Attempt='01')
$ErrorActionPreference='Stop';Set-StrictMode -Version Latest
$workspace=(Resolve-Path (Join-Path $PSScriptRoot '..')).Path;$python='C:\Users\30429\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe'
$local='scripts\m171_inspect_m166_delta.py';$path=(Resolve-Path -LiteralPath (Join-Path $workspace $local)).Path;$hash=(Get-FileHash -Algorithm SHA256 -LiteralPath $path).Hash.ToLowerInvariant();$remote='/home/ubuntu/tellme_m120_m89x2_20260901/bootstrap/m171_inspect_m166_delta.py';$upload="tmp\m171_inspect\upload_${Attempt}_uart.log";$run="tmp\m171_inspect\run_${Attempt}_uart.log";$formal="deployment\mage_vl4b\M171_M166_DELTA_INSPECTION_RESULT_${Attempt}.json"
foreach($r in @($upload,$run,$formal)){if(Test-Path -LiteralPath (Join-Path $workspace $r)){throw "M171 output exists: $r"}}
& (Join-Path $PSScriptRoot 'm75c_uart_put_file_base64.ps1') -LocalPath $local -RemotePath $remote -Port $Port -ExpectedFtdiSerial $ExpectedFtdiSerial -LogPath $upload -TimeoutSeconds 120
& (Join-Path $PSScriptRoot 'm75c_uart_command.ps1') -Command "python3 $remote $hash" -Port $Port -ExpectedFtdiSerial $ExpectedFtdiSerial -LogPath $run -TimeoutSeconds 120
$text=Get-Content -LiteralPath (Join-Path $workspace $run)-Raw;$match=[regex]::Match($text,'__M171_DELTA_INSPECTION_BEGIN__\s*(\{.*?\})\s*__M171_DELTA_INSPECTION_END__','Singleline');if(-not$match.Success){throw 'M171 result marker missing'};$value=$match.Groups[1].Value|ConvertFrom-Json;$value|Add-Member uart_log $run;$value|Add-Member uart_log_sha256 ((Get-FileHash -Algorithm SHA256 -LiteralPath (Join-Path $workspace $run)).Hash.ToLowerInvariant());$value|ConvertTo-Json -Depth 8|Set-Content -LiteralPath (Join-Path $workspace $formal) -Encoding utf8
Write-Output ($value|ConvertTo-Json -Depth 8);Write-Output 'M171_M166_DELTA_INSPECTION_UART_PASS'
