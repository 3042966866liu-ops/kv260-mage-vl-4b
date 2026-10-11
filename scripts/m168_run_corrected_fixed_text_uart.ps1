[CmdletBinding()]
param([string]$Port='COM3',[string]$ExpectedFtdiSerial='XFL1PL5N11BJB',[string]$Attempt='01',[string]$Layer0Attempt='01',[int]$TimeoutSeconds=3600)
$ErrorActionPreference='Stop';Set-StrictMode -Version Latest
$workspace=(Resolve-Path (Join-Path $PSScriptRoot '..')).Path
$python='C:\Users\30429\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe'
$layer0Relative="deployment\mage_vl4b\M167_M120_CORRECTED_LAYER0_BOARD_RESULT_${Layer0Attempt}.json";$layer0Path=Join-Path $workspace $layer0Relative
if(-not(Test-Path -LiteralPath $layer0Path)){throw 'M168_LOCKED_UNTIL_M167_CORRECTED_LAYER0_PASS'}
$layer0=Get-Content -LiteralPath $layer0Path -Raw|ConvertFrom-Json
if($layer0.status-ne'PASS'-or $layer0.gate-ne'M144-M120-complete-layer0-boundary-acceptance'-or $layer0.candidate_build_id.ToLowerInvariant()-ne'0x4d395832'-or $layer0.package_manifest_sha256-ne'34662ca90cb45b9a1d34903538b030f28b1f9f70ece3f35e7ccbbaf6eb3bbf97'-or -not $layer0.board_acceptance_sha256){throw 'M168_M167_IDENTITY_FAIL'}
$root='/home/ubuntu/tellme_m120_m89x2_20260901';$candidate="$root/m165_m120_layer0_board_candidate";$weights="$root/m120_fulltext_weights_0x4D395832";$resultDir="$root/results/m168_fixed_text_${Attempt}";$acceptance="$root/results/m167_corrected_layer0_${Layer0Attempt}/layer0_acceptance.json"
$files=@(@{l='scripts\m168_verify_m167_predecessor.py';r="$root/bootstrap/m168_verify_m167_predecessor.py";n='predecessor'},@{l='scripts\m168_verify_absent_result.py';r="$root/bootstrap/m168_verify_absent_result.py";n='absence'},@{l='scripts\m168_run_corrected_fixed_text_e2e.sh';r="$root/bootstrap/m168_run_corrected_fixed_text_e2e.sh";n='runner'})
foreach($f in $files){$f.h=(Get-FileHash -Algorithm SHA256 -LiteralPath (Join-Path $workspace $f.l)).Hash.ToLowerInvariant();$log="tmp\m168_fixed_text\upload_$($f.n)_${Attempt}_uart.log";if(Test-Path -LiteralPath (Join-Path $workspace $log)){throw "M168 upload log exists: $log"};& (Join-Path $PSScriptRoot 'm75c_uart_put_file_base64.ps1') -LocalPath $f.l -RemotePath $f.r -Port $Port -ExpectedFtdiSerial $ExpectedFtdiSerial -LogPath $log -TimeoutSeconds 120}
$absenceLog="tmp\m168_fixed_text\absence_${Attempt}_uart.log";$runLog="tmp\m168_fixed_text\run_${Attempt}_uart.log";$formal="deployment\mage_vl4b\M168_M120_FIXED_TEXT_BOARD_RESULT_${Attempt}.json"
foreach($r in @($absenceLog,$runLog,$formal)){if(Test-Path -LiteralPath (Join-Path $workspace $r)){throw "M168 output exists: $r"}}
& (Join-Path $PSScriptRoot 'm75c_uart_command.ps1') -Command "python3 $($files[1].r) $resultDir $($files[1].h)" -Port $Port -ExpectedFtdiSerial $ExpectedFtdiSerial -LogPath $absenceLog -TimeoutSeconds 120
if((Get-Content -LiteralPath (Join-Path $workspace $absenceLog)-Raw)-notmatch'M168_RESULT_DIR_ABSENT'){throw 'M168_RESULT_ABSENCE_FAIL'}
$cmd="sudo -n bash $($files[2].r) $candidate $weights/language_fourport $weights/lmhead_fourport $resultDir 34662ca90cb45b9a1d34903538b030f28b1f9f70ece3f35e7ccbbaf6eb3bbf97 $acceptance $($layer0.board_acceptance_sha256) $($files[0].r) $($files[0].h)"
$commandError=$null;try{& (Join-Path $PSScriptRoot 'm75c_uart_command.ps1') -Command $cmd -Port $Port -ExpectedFtdiSerial $ExpectedFtdiSerial -LogPath $runLog -TimeoutSeconds $TimeoutSeconds}catch{$commandError=$_}
& $python (Join-Path $PSScriptRoot 'm168_collect_fixed_text_uart.py') --log (Join-Path $workspace $runLog) --result (Join-Path $workspace $formal) --layer0 $layer0Path;$collector=$LASTEXITCODE
if($collector-ne 0){throw "M168 fixed-text FAIL; evidence retained at $formal"};if($null-ne$commandError){throw $commandError};Write-Output 'M168_M120_FIXED_TEXT_UART_PASS'
