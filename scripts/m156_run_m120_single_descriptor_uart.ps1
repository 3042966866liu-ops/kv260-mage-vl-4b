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
$remoteRoot = '/home/ubuntu/tellme_m120_m89x2_20260901/diagnostics/m156'
$remoteDiagnostic = "$remoteRoot/m156_m120_single_descriptor_diagnostic.py"
$remoteRunner = "$remoteRoot/m156_run_m120_single_descriptor_diagnostic.sh"
$resultDir = "/home/ubuntu/tellme_m120_m89x2_20260901/results/m156_single_descriptor_$Attempt"
$manifest = '7600ba1af87680fe1294ae6dc88f8e0968f23b2e38ca48dbfd316e351ea76e3e'

$m138Path = Join-Path $workspace "deployment\mage_vl4b\M138_M120_BUILD_ID_BOARD_RESULT_${Attempt}.json"
$m139Path = Join-Path $workspace "deployment\mage_vl4b\M139_M120_SINGLE_DESCRIPTOR_BOARD_RESULT_${Attempt}.json"
if (-not (Test-Path -LiteralPath $m138Path) -or -not (Test-Path -LiteralPath $m139Path)) {
    throw 'M156 requires retained M138 PASS and M139 numerical FAIL'
}
$m138 = Get-Content -Raw -LiteralPath $m138Path | ConvertFrom-Json
$m139 = Get-Content -Raw -LiteralPath $m139Path | ConvertFrom-Json
if ($m138.status -ne 'PASS' -or $m138.gate -ne 'M138-M120-COM3-build-id' -or $m138.candidate_build_id.ToLowerInvariant() -ne '0x4d395832') {
    throw 'M156 M138 prerequisite mismatch'
}
if ($m139.status -ne 'FAIL' -or $m139.gate -ne 'M139-M120-COM3-single-descriptor' -or $m139.error -notmatch 'first_byte=2308') {
    throw 'M156 M139 failure identity mismatch'
}

$localDiagnostic = Join-Path $workspace 'scripts\m156_m120_single_descriptor_diagnostic.py'
$localRunner = Join-Path $workspace 'scripts\m156_run_m120_single_descriptor_diagnostic.sh'
$diagnosticHash = (Get-FileHash -Algorithm SHA256 -LiteralPath $localDiagnostic).Hash.ToLowerInvariant()
$runnerHash = (Get-FileHash -Algorithm SHA256 -LiteralPath $localRunner).Hash.ToLowerInvariant()
$logRoot = Join-Path $workspace 'tmp\m156_uart'
$uploadDiagnosticLog = Join-Path $logRoot "upload_diagnostic_${Attempt}.log"
$uploadRunnerLog = Join-Path $logRoot "upload_runner_${Attempt}.log"
$hashLog = Join-Path $logRoot "remote_hash_${Attempt}.log"
$runLog = Join-Path $logRoot "diagnostic_${Attempt}.log"
$formal = Join-Path $workspace "deployment\mage_vl4b\M156_M120_SINGLE_DESCRIPTOR_DIAGNOSTIC_RESULT_${Attempt}.json"
foreach ($path in @($uploadDiagnosticLog,$uploadRunnerLog,$hashLog,$runLog,$formal)) {
    if (Test-Path -LiteralPath $path) { throw "M156 refuses existing evidence path: $path" }
}

& $pwsh -NoProfile -ExecutionPolicy Bypass -File (Join-Path $PSScriptRoot 'm75c_uart_put_file_base64.ps1') `
    -LocalPath 'scripts\m156_m120_single_descriptor_diagnostic.py' -RemotePath $remoteDiagnostic `
    -Port $Port -ExpectedFtdiSerial $ExpectedFtdiSerial `
    -LogPath "tmp\m156_uart\upload_diagnostic_${Attempt}.log" -TimeoutSeconds 120
if ($LASTEXITCODE -ne 0) { throw 'M156 diagnostic upload failed' }
& $pwsh -NoProfile -ExecutionPolicy Bypass -File (Join-Path $PSScriptRoot 'm75c_uart_put_file_base64.ps1') `
    -LocalPath 'scripts\m156_run_m120_single_descriptor_diagnostic.sh' -RemotePath $remoteRunner `
    -Port $Port -ExpectedFtdiSerial $ExpectedFtdiSerial `
    -LogPath "tmp\m156_uart\upload_runner_${Attempt}.log" -TimeoutSeconds 120
if ($LASTEXITCODE -ne 0) { throw 'M156 runner upload failed' }

$hashCommand = "sha256sum $remoteDiagnostic $remoteRunner"
& $pwsh -NoProfile -ExecutionPolicy Bypass -File (Join-Path $PSScriptRoot 'm75c_uart_command.ps1') `
    -Command $hashCommand -Port $Port -ExpectedFtdiSerial $ExpectedFtdiSerial `
    -LogPath "tmp\m156_uart\remote_hash_${Attempt}.log" -TimeoutSeconds 30 -MarkerPrefix '__M156_HASH_RC_'
if ($LASTEXITCODE -ne 0) { throw 'M156 remote hash command failed' }
$hashText = Get-Content -Raw -LiteralPath $hashLog
if ($hashText -notmatch [regex]::Escape($diagnosticHash) -or $hashText -notmatch [regex]::Escape($runnerHash)) {
    throw 'M156 remote upload SHA-256 mismatch'
}

$command = "sudo -n bash $remoteRunner $candidate $remoteDiagnostic $resultDir $manifest $diagnosticHash"
& $pwsh -NoProfile -ExecutionPolicy Bypass -File (Join-Path $PSScriptRoot 'm75c_uart_command.ps1') `
    -Command $command -Port $Port -ExpectedFtdiSerial $ExpectedFtdiSerial `
    -LogPath "tmp\m156_uart\diagnostic_${Attempt}.log" -TimeoutSeconds 120 -MarkerPrefix '__M156_RUN_RC_'
$uartCode = $LASTEXITCODE
& $python -B (Join-Path $PSScriptRoot 'm156_collect_m120_single_descriptor_uart.py') `
    --log $runLog --result $formal --attempt $Attempt
$collectCode = $LASTEXITCODE
if ($uartCode -ne 0) { throw "M156 UART diagnostic failed with exit code $uartCode" }
if ($collectCode -ne 0) { throw "M156 evidence collector rejected output with exit code $collectCode" }
Write-Output "M156_M120_SINGLE_DESCRIPTOR_UART_CLIENT_PASS result=$formal"
