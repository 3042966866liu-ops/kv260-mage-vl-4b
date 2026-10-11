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
$local = 'scripts\m188_board_ml_runtime_inventory.py'
$remote = '/home/ubuntu/tellme_m120_m89x2_20260901/m188_inventory/m188_board_ml_runtime_inventory.py'
$hash = (Get-FileHash -Algorithm SHA256 -LiteralPath (Join-Path $workspace $local)).Hash.ToLowerInvariant()
$upload = "tmp\m188_inventory\upload_${Attempt}_uart.log"
$run = "tmp\m188_inventory\run_${Attempt}_uart.log"
$formal = "deployment\mage_vl4b\M188_BOARD_ML_RUNTIME_INVENTORY_RESULT_${Attempt}.json"
foreach ($path in @($upload, $run, $formal)) { if (Test-Path -LiteralPath (Join-Path $workspace $path)) { throw "M188 output exists: $path" } }
& (Join-Path $PSScriptRoot 'm75c_uart_put_file_base64.ps1') -LocalPath $local -RemotePath $remote -Port $Port -ExpectedFtdiSerial $ExpectedFtdiSerial -LogPath $upload -TimeoutSeconds 180
& (Join-Path $PSScriptRoot 'm75c_uart_command.ps1') `
    -Command "python3 $remote --expected-self-sha256 $hash --result /home/ubuntu/tellme_m120_m89x2_20260901/results/M188_BOARD_ML_RUNTIME_INVENTORY_RESULT.json" `
    -Port $Port -ExpectedFtdiSerial $ExpectedFtdiSerial -LogPath $run -TimeoutSeconds 300
& $python (Join-Path $PSScriptRoot 'm188_collect_board_ml_inventory_uart.py') --log (Join-Path $workspace $run) --result (Join-Path $workspace $formal)
if ($LASTEXITCODE -ne 0) { throw "M188 collector failed exit=$LASTEXITCODE" }
Write-Output 'M188_BOARD_ML_RUNTIME_INVENTORY_UART_PASS'
