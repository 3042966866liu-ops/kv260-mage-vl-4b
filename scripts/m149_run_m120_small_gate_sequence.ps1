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
$sync = Join-Path $PSScriptRoot 'm149_sync_m120_small_gate_state.py'

function Invoke-GateAndSync {
    param(
        [Parameter(Mandatory=$true)][string]$Level,
        [Parameter(Mandatory=$true)][string]$Runner,
        [Parameter(Mandatory=$true)][string]$Formal,
        [string[]]$RunnerArguments = @()
    )

    if (Test-Path -LiteralPath $Formal) {
        throw "Refusing to overwrite existing formal result: $Formal"
    }
    & $pwsh -NoProfile -ExecutionPolicy Bypass -File $Runner @RunnerArguments
    $runnerCode = $LASTEXITCODE

    if (-not (Test-Path -LiteralPath $Formal)) {
        throw "$Level runner produced no formal result; authoritative state was not changed"
    }

    & $python $sync --level $Level --result $Formal
    $syncCode = $LASTEXITCODE
    if ($syncCode -ne 0) {
        throw "$Level state synchronization rejected the formal result with exit code $syncCode"
    }
    if ($runnerCode -ne 0) {
        throw "$Level gate failed with exit code $runnerCode; result was synchronized and no broader gate ran"
    }
}

$buildResult = Join-Path $workspace "deployment\mage_vl4b\M138_M120_BUILD_ID_BOARD_RESULT_${Attempt}.json"
$descriptorResult = Join-Path $workspace "deployment\mage_vl4b\M139_M120_SINGLE_DESCRIPTOR_BOARD_RESULT_${Attempt}.json"
$chainResult = Join-Path $workspace "deployment\mage_vl4b\M140_M120_SINGLE_CHAIN_BOARD_RESULT_${Attempt}.json"

Invoke-GateAndSync -Level 'build-id' `
    -Runner (Join-Path $PSScriptRoot 'm138_run_m120_build_id_uart.ps1') `
    -Formal $buildResult `
    -RunnerArguments @('-Port', $Port, '-ExpectedFtdiSerial', $ExpectedFtdiSerial, '-Attempt', $Attempt)

Invoke-GateAndSync -Level 'single-descriptor' `
    -Runner (Join-Path $PSScriptRoot 'm139_run_m120_fixture_uart.ps1') `
    -Formal $descriptorResult `
    -RunnerArguments @('-Level', 'single-descriptor', '-Port', $Port,
        '-ExpectedFtdiSerial', $ExpectedFtdiSerial, '-Attempt', $Attempt,
        '-PrerequisiteAttempt', $Attempt)

Invoke-GateAndSync -Level 'single-chain' `
    -Runner (Join-Path $PSScriptRoot 'm139_run_m120_fixture_uart.ps1') `
    -Formal $chainResult `
    -RunnerArguments @('-Level', 'single-chain', '-Port', $Port,
        '-ExpectedFtdiSerial', $ExpectedFtdiSerial, '-Attempt', $Attempt,
        '-PrerequisiteAttempt', $Attempt)

Write-Output "M149_M120_SMALL_GATE_SEQUENCE_PASS attempt=$Attempt"
