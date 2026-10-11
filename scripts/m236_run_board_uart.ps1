[CmdletBinding()]
param([string]$Port='COM3',[string]$ExpectedFtdiSerial='XFL1PL5N11BJB',[string]$Attempt='01',[int]$TimeoutSeconds=420)
$ErrorActionPreference='Stop'
Set-StrictMode -Version Latest
$workspace=(Resolve-Path (Join-Path $PSScriptRoot '..')).Path
$python='C:\Users\30429\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe'
$buildPath=Join-Path $workspace 'deployment\mage_vl4b\M236_FUSED_PARSE_OVERLAP_BOARD_DELTA_RESULT.json'
$build=Get-Content -LiteralPath $buildPath -Raw|ConvertFrom-Json
if($build.status-ne'PASS'-or$build.gate-ne'M236-fused-parse-overlap-board-delta-build'){ throw 'M236 board delta build identity failed' }
$package=(Resolve-Path -LiteralPath (Join-Path $workspace $build.directory)).Path
$manifestPath=Join-Path $package 'PACKAGE_MANIFEST.json'
$manifest=Get-Content -LiteralPath $manifestPath -Raw|ConvertFrom-Json
$manifestHash=(Get-FileHash -Algorithm SHA256 -LiteralPath $manifestPath).Hash.ToLowerInvariant()
if($manifestHash-ne$build.package_manifest_sha256){ throw 'M236 package manifest hash mismatch' }
if($manifest.gate-ne'M236-fused-parse-overlap-runtime-board-delta'-or$manifest.base_build_id-ne'0x4D395832'){ throw 'M236 package identity failed' }
$base='/home/ubuntu/tellme_m120_m89x2_20260901/m175_m120_fixed_text_candidate'
$weights='/home/ubuntu/tellme_m120_m89x2_20260901/m120_fulltext_weights_0x4D395832'
$remote='/home/ubuntu/tellme_m120_m89x2_20260901/m236_fused_parse_overlap_delta'
$result="/home/ubuntu/tellme_m120_m89x2_20260901/results/m236_fused_parse_overlap_$Attempt"
$commandTool=Join-Path $PSScriptRoot 'm75c_uart_command.ps1'
$uploader=Join-Path $PSScriptRoot 'm212_uart_put_file_chunked.ps1'
$logRoot=Join-Path $workspace "tmp\m236_fused_parse_overlap\attempt_$Attempt"
$runLog=Join-Path $logRoot 'run_uart.log'
$formal=Join-Path $workspace "deployment\mage_vl4b\M236_FUSED_PARSE_OVERLAP_BOARD_RESULT_$Attempt.json"
if(Test-Path -LiteralPath $logRoot){ throw "M236 attempt log directory already exists: $logRoot" }
if(Test-Path -LiteralPath $formal){ throw "M236 formal result already exists: $formal" }
New-Item -ItemType Directory -Path $logRoot|Out-Null
& $commandTool -Command 'sudo -n true' -Port $Port -ExpectedFtdiSerial $ExpectedFtdiSerial -LogPath "tmp\m236_fused_parse_overlap\attempt_$Attempt\sudo_uart.log" -TimeoutSeconds 30
$entries=@([pscustomobject]@{path='PACKAGE_MANIFEST.json'})+@($manifest.files)
foreach($entry in $entries){
  $name=[string]$entry.path
  $localAbsolute=(Resolve-Path -LiteralPath (Join-Path $package $name)).Path
  $localRelative=$localAbsolute.Substring($workspace.Length+1)
  $safeName=$name.Replace('/','_')
  & $uploader -LocalPath $localRelative -RemotePath "$remote/$name" -Port $Port -ExpectedFtdiSerial $ExpectedFtdiSerial -LogPrefix "tmp\m236_fused_parse_overlap\attempt_$Attempt\upload_$safeName" -ChunkBytes 1800 -TimeoutSeconds 60
}
& $commandTool -Command "python3 $remote/m230_verify_package.py --root $remote --expected-manifest-sha256 $manifestHash" -Port $Port -ExpectedFtdiSerial $ExpectedFtdiSerial -LogPath "tmp\m236_fused_parse_overlap\attempt_$Attempt\verify_uart.log" -TimeoutSeconds 120
& $commandTool -Command "bash -n $remote/run_m236_board_gate.sh" -Port $Port -ExpectedFtdiSerial $ExpectedFtdiSerial -LogPath "tmp\m236_fused_parse_overlap\attempt_$Attempt\bash_n_uart.log" -TimeoutSeconds 60
$baseManifest=[string]$manifest.base_package_manifest_sha256
$runner="$remote/run_m236_board_gate.sh"
$boardCommand="sudo -n bash $runner $base $remote $weights/language_fourport $weights/lmhead_fourport $result $baseManifest $manifestHash"
$commandError=$null
try{
  & $commandTool -Command $boardCommand -Port $Port -ExpectedFtdiSerial $ExpectedFtdiSerial -LogPath "tmp\m236_fused_parse_overlap\attempt_$Attempt\run_uart.log" -TimeoutSeconds $TimeoutSeconds
}catch{
  $commandError=$_
}
& $python (Join-Path $PSScriptRoot 'm236_collect_board_uart.py') --log $runLog --result $formal --expected-manifest-sha256 $manifestHash
if($LASTEXITCODE-ne 0){ throw "M236 board gate failed; UART retained at $runLog" }
if($null-ne$commandError){ throw $commandError }
Write-Output 'M236_FUSED_PARSE_OVERLAP_BOARD_UART_PASS'
