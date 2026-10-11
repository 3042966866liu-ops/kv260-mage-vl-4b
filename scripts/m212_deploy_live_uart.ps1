[CmdletBinding()]
param([string]$Port='COM3',[string]$ExpectedFtdiSerial='XFL1PL5N11BJB',[string]$Attempt='01',[int]$TimeoutSeconds=900)
$ErrorActionPreference='Stop';Set-StrictMode -Version Latest
$workspace=(Resolve-Path (Join-Path $PSScriptRoot '..')).Path
$python='C:\Users\30429\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe'
$build=Get-Content -LiteralPath (Join-Path $workspace 'deployment\mage_vl4b\M212_LIVE_SERVICE_BOARD_DELTA_RESULT.json') -Raw|ConvertFrom-Json
$package=(Resolve-Path (Join-Path $workspace $build.directory)).Path
$manifestPath=Join-Path $package 'PACKAGE_MANIFEST.json';$manifest=Get-Content -LiteralPath $manifestPath -Raw|ConvertFrom-Json
$manifestHash=(Get-FileHash -Algorithm SHA256 -LiteralPath $manifestPath).Hash.ToLowerInvariant()
if($manifestHash-ne$build.package_manifest_sha256){throw 'M212_BOOTSTRAP_HASH_FAIL'}
$remote='/home/ubuntu/tellme_m120_m89x2_20260901/m212_live_delta'
& (Join-Path $PSScriptRoot 'm75c_uart_command.ps1') -Command 'sudo -n true' -Port $Port -ExpectedFtdiSerial $ExpectedFtdiSerial -LogPath "tmp\m212_live_service\sudo_${Attempt}.log" -TimeoutSeconds 30
# The manifest is the trust root and must arrive before any payload.  Use bounded
# UART lines for every file so Linux's canonical TTY line limit cannot truncate a
# large base64 command and leave the shell at a continuation prompt.
foreach($entry in @([pscustomobject]@{path='PACKAGE_MANIFEST.json'})+@($manifest.files)){
 $name=[string]$entry.path;$local=(Resolve-Path (Join-Path $package $name)).Path.Substring($workspace.Length+1)
 & (Join-Path $PSScriptRoot 'm212_uart_put_file_chunked.ps1') -LocalPath $local -RemotePath "$remote/$name" -Port $Port -ExpectedFtdiSerial $ExpectedFtdiSerial -LogPrefix "tmp\m212_live_service\upload_${Attempt}_$($name.Replace('/','_'))" -TimeoutSeconds 60
}
& (Join-Path $PSScriptRoot 'm75c_uart_command.ps1') -Command "python3 $remote/m212_verify_board_delta.py --root $remote --expected-manifest-sha256 $manifestHash" -Port $Port -ExpectedFtdiSerial $ExpectedFtdiSerial -LogPath "tmp\m212_live_service\verify_${Attempt}.log" -TimeoutSeconds 180
& (Join-Path $PSScriptRoot 'm75c_uart_command.ps1') -Command "bash -n $remote/m212_board_preflight_and_start.sh" -Port $Port -ExpectedFtdiSerial $ExpectedFtdiSerial -LogPath "tmp\m212_live_service\bash_n_${Attempt}.log" -TimeoutSeconds 60
$runLog="tmp\m212_live_service\run_${Attempt}.log";$formal="deployment\mage_vl4b\M212_LIVE_SERVICE_BOARD_RESULT_${Attempt}.json"
try{& (Join-Path $PSScriptRoot 'm75c_uart_command.ps1') -Command "sudo -n bash $remote/m212_board_preflight_and_start.sh $manifestHash" -Port $Port -ExpectedFtdiSerial $ExpectedFtdiSerial -LogPath $runLog -TimeoutSeconds $TimeoutSeconds}catch{Write-Warning $_}
& $python (Join-Path $PSScriptRoot 'm212_collect_board_result.py') --log (Join-Path $workspace $runLog) --result (Join-Path $workspace $formal)
if($LASTEXITCODE-ne 0){throw "M212 board service gate failed; formal result preserved at $formal"}
Write-Output 'M212_LIVE_SERVICE_UART_PASS'
