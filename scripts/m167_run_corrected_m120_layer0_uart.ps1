[CmdletBinding()]
param(
    [string]$Port = 'COM3',
    [string]$ExpectedFtdiSerial = 'XFL1PL5N11BJB',
    [string]$Attempt = '01',
    [string]$StageAttempt = '04',
    [int]$TimeoutSeconds = 900
)

$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest
$workspace = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
$python = 'C:\Users\30429\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe'
$stageRelative = "deployment\mage_vl4b\M166_M120_CORRECTED_LAYER0_BOARD_STAGE_RESULT_${StageAttempt}.json"
$stagePath = Join-Path $workspace $stageRelative
if (-not (Test-Path -LiteralPath $stagePath)) { throw 'M167_LOCKED_UNTIL_M166_CORRECTED_STAGE_PASS' }
$stage = Get-Content -LiteralPath $stagePath -Raw | ConvertFrom-Json
$candidate = '/home/ubuntu/tellme_m120_m89x2_20260901/m165_m120_layer0_board_candidate'
if ($stage.status -ne 'PASS' -or $stage.gate -ne 'M166-M120-corrected-Layer0-board-stage' -or
    $stage.candidate_build_id.ToLowerInvariant() -ne '0x4d395832' -or
    $stage.package_manifest_sha256 -ne '34662ca90cb45b9a1d34903538b030f28b1f9f70ece3f35e7ccbbaf6eb3bbf97' -or
    $stage.output -ne $candidate -or $stage.file_count -ne 18 -or $stage.stable_rollback_preserved -ne $true) {
    throw 'M167_M166_STAGE_IDENTITY_FAIL'
}
$packagePath = Join-Path $workspace 'deployment\mage_vl4b\M165_M120_CORRECTED_LAYER0_PACKAGE_RESULT.json'
$package = Get-Content -LiteralPath $packagePath -Raw | ConvertFrom-Json
if ($package.status -ne 'PASS' -or $package.package_manifest_sha256 -ne $stage.package_manifest_sha256) {
    throw 'M167_M165_PACKAGE_IDENTITY_FAIL'
}

$root = '/home/ubuntu/tellme_m120_m89x2_20260901'
$weights = "$root/m120_fulltext_weights_0x4D395832"
$resultDir = "$root/results/m167_corrected_layer0_${Attempt}"
$checkerRelative = 'scripts\m167_verify_absent_result.py'
$checkerPath = (Resolve-Path -LiteralPath (Join-Path $workspace $checkerRelative)).Path
$checkerHash = (Get-FileHash -Algorithm SHA256 -LiteralPath $checkerPath).Hash.ToLowerInvariant()
$checkerRemote = "$root/bootstrap/m167_verify_absent_result.py"
$checkerUploadLog = "tmp\m167_layer0\checker_${Attempt}_uart.log"
$absenceLog = "tmp\m167_layer0\absence_${Attempt}_uart.log"
$runLog = "tmp\m167_layer0\run_${Attempt}_uart.log"
$formal = "deployment\mage_vl4b\M167_M120_CORRECTED_LAYER0_BOARD_RESULT_${Attempt}.json"
foreach ($relative in @($checkerUploadLog, $absenceLog, $runLog, $formal)) {
    if (Test-Path -LiteralPath (Join-Path $workspace $relative)) { throw "M167 output exists: $relative" }
}
& (Join-Path $PSScriptRoot 'm75c_uart_put_file_base64.ps1') `
    -LocalPath $checkerRelative -RemotePath $checkerRemote -Port $Port `
    -ExpectedFtdiSerial $ExpectedFtdiSerial -LogPath $checkerUploadLog -TimeoutSeconds 120
& (Join-Path $PSScriptRoot 'm75c_uart_command.ps1') `
    -Command "python3 $checkerRemote $resultDir $checkerHash" `
    -Port $Port -ExpectedFtdiSerial $ExpectedFtdiSerial -LogPath $absenceLog -TimeoutSeconds 120
$absenceText = Get-Content -LiteralPath (Join-Path $workspace $absenceLog) -Raw
if ($absenceText -notmatch 'M167_RESULT_DIR_ABSENT') { throw 'M167_REMOTE_RESULT_DIR_NOT_ABSENT' }

$command = "sudo -n bash $candidate/runtime/run_m120_layer0_gate.sh $candidate $weights/language_fourport $weights/lmhead_fourport $resultDir 34662ca90cb45b9a1d34903538b030f28b1f9f70ece3f35e7ccbbaf6eb3bbf97 c514c1b44690855ad45cda8df558807940916d27728491be0d275095d7a1eda2"
$commandError = $null
try {
    & (Join-Path $PSScriptRoot 'm75c_uart_command.ps1') `
        -Command $command -Port $Port -ExpectedFtdiSerial $ExpectedFtdiSerial `
        -LogPath $runLog -TimeoutSeconds $TimeoutSeconds
} catch {
    $commandError = $_
}
& $python (Join-Path $PSScriptRoot 'm167_collect_corrected_layer0_uart.py') `
    --log (Join-Path $workspace $runLog) --result (Join-Path $workspace $formal) --stage-result $stagePath
$collectorExit = $LASTEXITCODE
if ($collectorExit -ne 0) { throw "M167 corrected Layer-0 gate FAIL; formal evidence retained at $formal" }
if ($null -ne $commandError) { throw $commandError }
Write-Output 'M167_M120_CORRECTED_LAYER0_UART_PASS'
