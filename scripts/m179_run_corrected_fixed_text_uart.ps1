[CmdletBinding()]
param([string]$Port='COM3',[string]$ExpectedFtdiSerial='XFL1PL5N11BJB',[string]$Attempt='01',[string]$Layer0Attempt='01',[string]$StageAttempt='01',[int]$TimeoutSeconds=3600)
$ErrorActionPreference='Stop';Set-StrictMode -Version Latest
$workspace=(Resolve-Path (Join-Path $PSScriptRoot '..')).Path
$python='C:\Users\30429\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe'
$layer0Path=Join-Path $workspace "deployment\mage_vl4b\M167_M120_CORRECTED_LAYER0_BOARD_RESULT_${Layer0Attempt}.json"
$stagePath=Join-Path $workspace "deployment\mage_vl4b\M176_M120_LMHEAD_OPTIONAL_LAYER_BOARD_STAGE_RESULT_${StageAttempt}.json"
if(-not(Test-Path -LiteralPath $layer0Path)-or-not(Test-Path -LiteralPath $stagePath)){throw 'M179_LOCKED_UNTIL_M167_AND_M176_PASS'}
$layer0=Get-Content -LiteralPath $layer0Path -Raw|ConvertFrom-Json
$stage=Get-Content -LiteralPath $stagePath -Raw|ConvertFrom-Json
if($layer0.status-ne'PASS'-or $layer0.gate-ne'M144-M120-complete-layer0-boundary-acceptance'-or $layer0.candidate_build_id.ToLowerInvariant()-ne'0x4d395832'-or $layer0.board_acceptance_sha256-ne'8906034715c94b00d8a437b134e4e69c27020fa62dd4cb89e615c2dc05580e1d'){throw 'M179_M167_IDENTITY_FAIL'}
if($stage.status-ne'PASS'-or $stage.gate-ne'M176-M120-LMHead-optional-layer-board-stage'-or $stage.package_manifest_sha256-ne'406dcca340e4604baeb761445795391c43ec26bd99fa06ffae893d597b17414f'-or $stage.file_count-ne 18){throw 'M179_M176_IDENTITY_FAIL'}
$root='/home/ubuntu/tellme_m120_m89x2_20260901';$candidate="$root/m175_m120_fixed_text_candidate";$weights="$root/m120_fulltext_weights_0x4D395832";$resultDir="$root/results/m179_fixed_text_${Attempt}";$acceptance="$root/results/m167_corrected_layer0_${Layer0Attempt}/layer0_acceptance.json"
& (Join-Path $PSScriptRoot 'm75c_uart_command.ps1') -Command 'sudo -n true' -Port $Port -ExpectedFtdiSerial $ExpectedFtdiSerial -LogPath "tmp\m179_fixed_text\sudo_preflight_${Attempt}_uart.log" -TimeoutSeconds 30
$files=@(@{l='scripts\m168_verify_m167_predecessor.py';r="$root/bootstrap/m179_verify_m167_predecessor.py";n='predecessor'},@{l='scripts\m179_verify_absent_result.py';r="$root/bootstrap/m179_verify_absent_result.py";n='absence'},@{l='scripts\m179_run_corrected_fixed_text_e2e.sh';r="$root/bootstrap/m179_run_corrected_fixed_text_e2e.sh";n='runner'})
foreach($f in $files){$f.h=(Get-FileHash -Algorithm SHA256 -LiteralPath (Join-Path $workspace $f.l)).Hash.ToLowerInvariant();$log="tmp\m179_fixed_text\upload_$($f.n)_${Attempt}_uart.log";if(Test-Path -LiteralPath (Join-Path $workspace $log)){throw "M179 upload log exists: $log"};& (Join-Path $PSScriptRoot 'm75c_uart_put_file_base64.ps1') -LocalPath $f.l -RemotePath $f.r -Port $Port -ExpectedFtdiSerial $ExpectedFtdiSerial -LogPath $log -TimeoutSeconds 120}
$absenceLog="tmp\m179_fixed_text\absence_${Attempt}_uart.log";$runLog="tmp\m179_fixed_text\run_${Attempt}_uart.log";$formal="deployment\mage_vl4b\M179_M120_FIXED_TEXT_BOARD_RESULT_${Attempt}.json"
foreach($r in @($absenceLog,$runLog,$formal)){if(Test-Path -LiteralPath (Join-Path $workspace $r)){throw "M179 output exists: $r"}}
& (Join-Path $PSScriptRoot 'm75c_uart_command.ps1') -Command "python3 $($files[1].r) $resultDir $($files[1].h)" -Port $Port -ExpectedFtdiSerial $ExpectedFtdiSerial -LogPath $absenceLog -TimeoutSeconds 120
if((Get-Content -LiteralPath (Join-Path $workspace $absenceLog)-Raw)-notmatch'M179_RESULT_DIR_ABSENT'){throw 'M179_RESULT_ABSENCE_FAIL'}
$cmd="sudo -n bash $($files[2].r) $candidate $weights/language_fourport $weights/lmhead_fourport $resultDir 406dcca340e4604baeb761445795391c43ec26bd99fa06ffae893d597b17414f $acceptance $($layer0.board_acceptance_sha256) $($files[0].r) $($files[0].h)"
$commandError=$null;try{& (Join-Path $PSScriptRoot 'm75c_uart_command.ps1') -Command $cmd -Port $Port -ExpectedFtdiSerial $ExpectedFtdiSerial -LogPath $runLog -TimeoutSeconds $TimeoutSeconds}catch{$commandError=$_}
& $python (Join-Path $PSScriptRoot 'm179_collect_fixed_text_uart.py') --log (Join-Path $workspace $runLog) --result (Join-Path $workspace $formal) --layer0 $layer0Path --stage $stagePath;$collector=$LASTEXITCODE
if($collector-ne 0){throw "M179 fixed-text FAIL; evidence retained at $formal"};if($null-ne$commandError){throw $commandError};Write-Output 'M179_M120_FIXED_TEXT_UART_PASS'
exit 0
