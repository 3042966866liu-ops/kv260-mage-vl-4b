[CmdletBinding()]
param(
    [string]$Port = 'COM3',
    [string]$ExpectedFtdiSerial = 'XFL1PL5N11BJB',
    [string]$Attempt = '01',
    [string]$PredecessorAttempt = '01',
    [int]$TimeoutSeconds = 900
)

$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest
$workspace = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
$python = 'C:\Users\30429\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe'
$m163Path = Join-Path $workspace "deployment\mage_vl4b\M163_M120_NETWORK_BOARD_IMPORT_RESULT_${PredecessorAttempt}.json"
if (-not (Test-Path -LiteralPath $m163Path)) { throw 'M164_LOCKED_UNTIL_M163_WEIGHT_IMPORT_PASS' }
$m163 = Get-Content -LiteralPath $m163Path -Raw | ConvertFrom-Json
if ($m163.status -ne 'PASS' -or $m163.gate -ne 'M163-M120-direct-Ethernet-PC-push-board-import' -or
    $m163.candidate_build_id.ToLowerInvariant() -ne '0x4d395832' -or $m163.payload_bytes -ne 2035472384) {
    throw 'M164_LOCKED_UNTIL_M163_WEIGHT_IMPORT_PASS'
}
$packagePath = Join-Path $workspace 'deployment\mage_vl4b\M145_M120_LAYER0_BOARD_PACKAGE_RESULT.json'
$package = Get-Content -LiteralPath $packagePath -Raw | ConvertFrom-Json
if ($package.status -ne 'PASS' -or $package.package_manifest_sha256 -ne '732b881d3507eaa12b8488e9224835ac115b686a003c748c9fa05a9793041d13') {
    throw 'M164_M145_PACKAGE_IDENTITY_FAIL'
}

$root = '/home/ubuntu/tellme_m120_m89x2_20260901'
$candidate = "$root/m120_text4b_layer0_board_candidate"
$weights = "$root/m120_fulltext_weights_0x4D395832"
$resultDir = "$root/results/m164_layer0_${Attempt}"
$absenceLog = "tmp\m164_layer0\absence_${Attempt}_uart.log"
$runLog = "tmp\m164_layer0\run_${Attempt}_uart.log"
$formal = "deployment\mage_vl4b\M164_M120_LAYER0_BOARD_RESULT_${Attempt}.json"
foreach ($relative in @($absenceLog, $runLog, $formal)) {
    if (Test-Path -LiteralPath (Join-Path $workspace $relative)) { throw "M164 output exists: $relative" }
}
& (Join-Path $PSScriptRoot 'm75c_uart_command.ps1') `
    -Command "test ! -e $resultDir && echo M164_RESULT_DIR_ABSENT" `
    -Port $Port -ExpectedFtdiSerial $ExpectedFtdiSerial -LogPath $absenceLog -TimeoutSeconds 120
$absenceText = Get-Content -LiteralPath (Join-Path $workspace $absenceLog) -Raw
if ($absenceText -notmatch 'M164_RESULT_DIR_ABSENT') { throw 'M164_REMOTE_RESULT_DIR_NOT_ABSENT' }

$command = "sudo -n bash $candidate/runtime/run_m120_layer0_gate.sh $candidate $weights/language_fourport $weights/lmhead_fourport $resultDir 732b881d3507eaa12b8488e9224835ac115b686a003c748c9fa05a9793041d13 c514c1b44690855ad45cda8df558807940916d27728491be0d275095d7a1eda2"
& (Join-Path $PSScriptRoot 'm75c_uart_command.ps1') `
    -Command $command -Port $Port -ExpectedFtdiSerial $ExpectedFtdiSerial `
    -LogPath $runLog -TimeoutSeconds $TimeoutSeconds

& $python (Join-Path $PSScriptRoot 'm164_collect_m120_layer0_uart.py') `
    --log (Join-Path $workspace $runLog) --result (Join-Path $workspace $formal)
if ($LASTEXITCODE -ne 0) { throw "M164 collector failed exit=$LASTEXITCODE" }
Write-Output 'M164_M120_LAYER0_UART_PASS'
