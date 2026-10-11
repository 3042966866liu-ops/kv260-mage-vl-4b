[CmdletBinding()]
param(
    [string]$Port = 'COM3',
    [string]$ExpectedFtdiSerial = 'XFL1PL5N11BJB',
    [ValidatePattern('^[0-9][0-9]$')][string]$Attempt = '01'
)

$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest
$workspace = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
$pwsh = 'C:\Users\30429\.cache\codex-runtimes\codex-primary-runtime\dependencies\native\powershell\pwsh.exe'
$python = 'C:\Users\30429\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe'
$candidate = '/home/ubuntu/tellme_m120_m89x2_20260901/m120_text4b_board_candidate'
$manifest = '7600ba1af87680fe1294ae6dc88f8e0968f23b2e38ca48dbfd316e351ea76e3e'
$resultDir = "/home/ubuntu/tellme_m120_m89x2_20260901/results/m138_build_id_$Attempt"
$logRelative = "tmp\m136_uart\m138_build_id_${Attempt}_uart.log"
$log = Join-Path $workspace $logRelative
$formal = Join-Path $workspace "deployment\mage_vl4b\M138_M120_BUILD_ID_BOARD_RESULT_${Attempt}.json"
if (Test-Path -LiteralPath $log) { throw "local UART log already exists: $log" }
if (Test-Path -LiteralPath $formal) { throw "local result already exists: $formal" }

$command = "sudo -n bash $candidate/runtime/run_m120_gate.sh $candidate build-id $resultDir $manifest"
& $pwsh -NoProfile -ExecutionPolicy Bypass -File (Join-Path $PSScriptRoot 'm75c_uart_command.ps1') `
    -Port $Port -ExpectedFtdiSerial $ExpectedFtdiSerial -Command $command `
    -LogPath $logRelative -TimeoutSeconds 120 -MarkerPrefix '__M138_BUILD_ID_RC_'
$uartCode = $LASTEXITCODE

& $python (Join-Path $PSScriptRoot 'm138_collect_m120_build_id_uart.py') `
    --log $log --result $formal --attempt $Attempt
$collectCode = $LASTEXITCODE
if ($uartCode -ne 0) { throw "M138 UART runner failed with exit code $uartCode; formal evidence was still collected" }
if ($collectCode -ne 0) { throw "M138 Build-ID evidence rejected with exit code $collectCode" }
Write-Output "M138_M120_BUILD_ID_UART_CLIENT_PASS result=$formal"
