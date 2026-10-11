[CmdletBinding()]
param(
    [Parameter(Mandatory=$true)][ValidateSet('single-descriptor','single-chain')][string]$Level,
    [string]$Port = 'COM3',
    [string]$ExpectedFtdiSerial = 'XFL1PL5N11BJB',
    [ValidatePattern('^[0-9][0-9]$')][string]$Attempt = '01',
    [ValidatePattern('^[0-9][0-9]$')][string]$DescriptorAttempt = '02'
)

$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest
$workspace = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
$pwsh = 'C:\Users\30429\.cache\codex-runtimes\codex-primary-runtime\dependencies\native\powershell\pwsh.exe'
$python = 'C:\Users\30429\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe'
$candidate = '/home/ubuntu/tellme_m120_m89x2_20260901/m120_text4b_board_candidate'
$manifest = '7600ba1af87680fe1294ae6dc88f8e0968f23b2e38ca48dbfd316e351ea76e3e'
$normalized = $Level.Replace('-','_')
$remoteRoot = "/home/ubuntu/tellme_m120_m89x2_20260901/diagnostics/m157_${normalized}_${Attempt}"
$remoteGate = "$remoteRoot/m157_m120_fixture_ftz_gate.py"
$remoteRunner = "$remoteRoot/m157_run_m120_fixture_ftz_gate.sh"
$remotePolicy = "$remoteRoot/M157_M120_FP16_FTZ_POLICY_RESULT.json"
$resultDir = "/home/ubuntu/tellme_m120_m89x2_20260901/results/m157_${normalized}_${Attempt}"

$policyPath = Join-Path $workspace 'deployment\mage_vl4b\M157_M120_FP16_FTZ_POLICY_RESULT.json'
$policy = Get-Content -Raw -LiteralPath $policyPath | ConvertFrom-Json
if ($policy.status -ne 'PASS_POLICY_FROZEN_BEFORE_ACCEPTANCE_RERUN' -or $policy.candidate_build_id.ToLowerInvariant() -ne '0x4d395832') {
    throw 'M157 policy prerequisite mismatch'
}
if ($Level -eq 'single-descriptor') {
    $previousPath = Join-Path $workspace 'deployment\mage_vl4b\M138_M120_BUILD_ID_BOARD_RESULT_01.json'
    $previousGate = 'M138-M120-COM3-build-id'
    $formal = Join-Path $workspace "deployment\mage_vl4b\M139_M120_SINGLE_DESCRIPTOR_BOARD_RESULT_${Attempt}.json"
    $syncLevel = 'single-descriptor'
} else {
    $previousPath = Join-Path $workspace "deployment\mage_vl4b\M139_M120_SINGLE_DESCRIPTOR_BOARD_RESULT_${DescriptorAttempt}.json"
    $previousGate = 'M139-M120-COM3-single-descriptor'
    $formal = Join-Path $workspace "deployment\mage_vl4b\M140_M120_SINGLE_CHAIN_BOARD_RESULT_${Attempt}.json"
    $syncLevel = 'single-chain'
}
if (-not (Test-Path -LiteralPath $previousPath)) { throw "M157 previous result absent: $previousPath" }
$previous = Get-Content -Raw -LiteralPath $previousPath | ConvertFrom-Json
if ($previous.status -ne 'PASS' -or $previous.gate -ne $previousGate -or $previous.candidate_build_id.ToLowerInvariant() -ne '0x4d395832') {
    throw "M157 previous result does not authorize $Level"
}

$localGate = Join-Path $workspace 'scripts\m157_m120_fixture_ftz_gate.py'
$localRunner = Join-Path $workspace 'scripts\m157_run_m120_fixture_ftz_gate.sh'
$gateHash = (Get-FileHash -Algorithm SHA256 -LiteralPath $localGate).Hash.ToLowerInvariant()
$runnerHash = (Get-FileHash -Algorithm SHA256 -LiteralPath $localRunner).Hash.ToLowerInvariant()
$policyHash = (Get-FileHash -Algorithm SHA256 -LiteralPath $policyPath).Hash.ToLowerInvariant()
$stem = "m157_${normalized}_${Attempt}"
$logPaths = @(
    "tmp\m157_uart\upload_gate_${stem}.log",
    "tmp\m157_uart\upload_runner_${stem}.log",
    "tmp\m157_uart\upload_policy_${stem}.log",
    "tmp\m157_uart\remote_hash_${stem}.log",
    "tmp\m157_uart\run_${stem}.log"
)
foreach ($relative in $logPaths) {
    if (Test-Path -LiteralPath (Join-Path $workspace $relative)) { throw "M157 refuses existing evidence: $relative" }
}
if (Test-Path -LiteralPath $formal) { throw "M157 refuses existing formal result: $formal" }

$uploads = @(
    @('scripts\m157_m120_fixture_ftz_gate.py',$remoteGate,$logPaths[0]),
    @('scripts\m157_run_m120_fixture_ftz_gate.sh',$remoteRunner,$logPaths[1]),
    @('deployment\mage_vl4b\M157_M120_FP16_FTZ_POLICY_RESULT.json',$remotePolicy,$logPaths[2])
)
foreach ($upload in $uploads) {
    & $pwsh -NoProfile -ExecutionPolicy Bypass -File (Join-Path $PSScriptRoot 'm75c_uart_put_file_base64.ps1') `
        -LocalPath $upload[0] -RemotePath $upload[1] -Port $Port -ExpectedFtdiSerial $ExpectedFtdiSerial `
        -LogPath $upload[2] -TimeoutSeconds 120
    if ($LASTEXITCODE -ne 0) { throw "M157 upload failed: $($upload[0])" }
}
$hashCommand = "sha256sum $remoteGate $remoteRunner $remotePolicy"
& $pwsh -NoProfile -ExecutionPolicy Bypass -File (Join-Path $PSScriptRoot 'm75c_uart_command.ps1') `
    -Command $hashCommand -Port $Port -ExpectedFtdiSerial $ExpectedFtdiSerial `
    -LogPath $logPaths[3] -TimeoutSeconds 30 -MarkerPrefix '__M157_HASH_RC_'
if ($LASTEXITCODE -ne 0) { throw 'M157 remote hash command failed' }
$hashText = Get-Content -Raw -LiteralPath (Join-Path $workspace $logPaths[3])
foreach ($hash in @($gateHash,$runnerHash,$policyHash)) {
    if ($hashText -notmatch [regex]::Escape($hash)) { throw "M157 remote SHA-256 missing: $hash" }
}

$command = "sudo -n bash $remoteRunner $candidate $remoteGate $Level $remotePolicy $resultDir $manifest $gateHash $policyHash"
& $pwsh -NoProfile -ExecutionPolicy Bypass -File (Join-Path $PSScriptRoot 'm75c_uart_command.ps1') `
    -Command $command -Port $Port -ExpectedFtdiSerial $ExpectedFtdiSerial `
    -LogPath $logPaths[4] -TimeoutSeconds 120 -MarkerPrefix '__M157_RUN_RC_'
$uartCode = $LASTEXITCODE
$runLog = Join-Path $workspace $logPaths[4]
& $python -B (Join-Path $PSScriptRoot 'm157_collect_m120_fixture_ftz_uart.py') `
    --level $Level --log $runLog --result $formal --attempt $Attempt
$collectCode = $LASTEXITCODE
if ($uartCode -ne 0) { throw "M157 $Level UART gate failed with exit code $uartCode" }
if ($collectCode -ne 0) { throw "M157 $Level collector failed with exit code $collectCode" }
& $python -B (Join-Path $PSScriptRoot 'm149_sync_m120_small_gate_state.py') --level $syncLevel --result $formal
if ($LASTEXITCODE -ne 0) { throw "M157 $Level state sync failed" }
Write-Output "M157_M120_FTZ_UART_PASS level=$Level result=$formal"
