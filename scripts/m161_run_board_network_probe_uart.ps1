[CmdletBinding()]
param(
    [string]$Port = 'COM3',
    [string]$ExpectedFtdiSerial = 'XFL1PL5N11BJB',
    [string]$Attempt = '01'
)

$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest
$workspace = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
$python = 'C:\Users\30429\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe'
$remote = '/home/ubuntu/tellme_m120_m89x2_20260901/network/m161_board_network_probe.py'
$uploadLog = "tmp\m161_network\upload_${Attempt}_uart.log"
$runLog = "tmp\m161_network\probe_${Attempt}_uart.log"
$result = "deployment\mage_vl4b\M161_KV260_NETWORK_PROBE_RESULT_${Attempt}.json"
foreach ($path in @($uploadLog, $runLog, $result)) {
    if (Test-Path -LiteralPath (Join-Path $workspace $path)) { throw "M161 output already exists: $path" }
}

& (Join-Path $PSScriptRoot 'm75c_uart_put_file_base64.ps1') `
    -LocalPath 'scripts\m161_board_network_probe.py' -RemotePath $remote `
    -Port $Port -ExpectedFtdiSerial $ExpectedFtdiSerial `
    -LogPath $uploadLog -TimeoutSeconds 120

& (Join-Path $PSScriptRoot 'm75c_uart_command.ps1') `
    -Command "python3 $remote" -Port $Port `
    -ExpectedFtdiSerial $ExpectedFtdiSerial -LogPath $runLog -TimeoutSeconds 120

& $python (Join-Path $PSScriptRoot 'm161_collect_board_network_probe.py') `
    --log (Join-Path $workspace $runLog) --result (Join-Path $workspace $result)
if ($LASTEXITCODE -ne 0) { throw "M161 collector failed exit=$LASTEXITCODE" }
Write-Output 'M161_KV260_NETWORK_PROBE_UART_PASS'
