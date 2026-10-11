[CmdletBinding()]
param(
    [Parameter(Mandatory=$true)]
    [ValidateSet('single-descriptor','single-chain')]
    [string]$Level,
    [string]$Port = 'COM3',
    [string]$ExpectedFtdiSerial = 'XFL1PL5N11BJB',
    [ValidatePattern('^[0-9][0-9]$')][string]$Attempt = '01',
    [ValidatePattern('^[0-9][0-9]$')][string]$PrerequisiteAttempt = '01'
)

$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest
$workspace = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
$pwsh = 'C:\Users\30429\.cache\codex-runtimes\codex-primary-runtime\dependencies\native\powershell\pwsh.exe'
$python = 'C:\Users\30429\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe'
$candidate = '/home/ubuntu/tellme_m120_m89x2_20260901/m120_text4b_board_candidate'
$manifest = '7600ba1af87680fe1294ae6dc88f8e0968f23b2e38ca48dbfd316e351ea76e3e'
if ($Level -eq 'single-descriptor') {
    $milestone = 'M139'
    $prerequisite = Join-Path $workspace "deployment\mage_vl4b\M138_M120_BUILD_ID_BOARD_RESULT_${PrerequisiteAttempt}.json"
    $requiredGate = 'M138-M120-COM3-build-id'
} else {
    $milestone = 'M140'
    $prerequisite = Join-Path $workspace "deployment\mage_vl4b\M139_M120_SINGLE_DESCRIPTOR_BOARD_RESULT_${PrerequisiteAttempt}.json"
    $requiredGate = 'M139-M120-COM3-single-descriptor'
}
if (-not (Test-Path -LiteralPath $prerequisite)) { throw "required previous-level result absent: $prerequisite" }
$previous = Get-Content -LiteralPath $prerequisite -Raw | ConvertFrom-Json
if ($previous.status -ne 'PASS' -or $previous.gate -ne $requiredGate -or $previous.candidate_build_id.ToLowerInvariant() -ne '0x4d395832') {
    throw "previous-level result does not authorize $Level"
}
$resultDir = "/home/ubuntu/tellme_m120_m89x2_20260901/results/$($milestone.ToLowerInvariant())_$($Level.Replace('-','_'))_$Attempt"
$stem = "$($milestone.ToLowerInvariant())_$($Level.Replace('-','_'))_$Attempt"
$logRelative = "tmp\m136_uart\${stem}_uart.log"
$log = Join-Path $workspace $logRelative
$formalName = "$($milestone)_M120_$($Level.Replace('-','_').ToUpperInvariant())_BOARD_RESULT_${Attempt}.json"
$formal = Join-Path $workspace "deployment\mage_vl4b\$formalName"
if (Test-Path -LiteralPath $log) { throw "local UART log already exists: $log" }
if (Test-Path -LiteralPath $formal) { throw "local result already exists: $formal" }

$command = "sudo -n bash $candidate/runtime/run_m120_gate.sh $candidate $Level $resultDir $manifest"
& $pwsh -NoProfile -ExecutionPolicy Bypass -File (Join-Path $PSScriptRoot 'm75c_uart_command.ps1') `
    -Port $Port -ExpectedFtdiSerial $ExpectedFtdiSerial -Command $command `
    -LogPath $logRelative -TimeoutSeconds 120 -MarkerPrefix "__$($milestone)_RC_"
$uartCode = $LASTEXITCODE
& $python (Join-Path $PSScriptRoot 'm139_collect_m120_fixture_uart.py') `
    --level $Level --log $log --result $formal --attempt $Attempt
$collectCode = $LASTEXITCODE
if ($uartCode -ne 0) { throw "$milestone UART runner failed with exit code $uartCode; formal evidence was still collected" }
if ($collectCode -ne 0) { throw "$milestone evidence rejected with exit code $collectCode" }
Write-Output "$($milestone)_M120_UART_CLIENT_PASS result=$formal"
