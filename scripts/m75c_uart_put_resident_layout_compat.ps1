param(
    [string]$Port = 'COM3',
    [string]$ExpectedFtdiSerial = 'XFL1PL5N11BJB',
    [string]$LogPath = 'tmp\m75c_full_layout\put_resident_layout_uart.log',
    [int]$TimeoutSeconds = 60
)

$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest

$workspace = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
$source = Join-Path $workspace 'deployment\mage_vl4b\m75c_highddr_payload\runtime\resident_layout.py'
$bytes = [System.IO.File]::ReadAllBytes($source)
$b64 = [Convert]::ToBase64String($bytes)
$remote = '/home/ubuntu/tellme_mage_m75c_full_20260829_01/runtime/resident_layout.py'
$command = "python3 -c `"import base64,pathlib; p=pathlib.Path('$remote'); p.write_bytes(base64.b64decode('$b64')); print('M75C_UART_PUT_RESIDENT_LAYOUT_PASS', p.stat().st_size)`""

& (Join-Path $PSScriptRoot 'm75c_uart_command.ps1') `
    -Command $command `
    -Port $Port `
    -ExpectedFtdiSerial $ExpectedFtdiSerial `
    -LogPath $LogPath `
    -TimeoutSeconds $TimeoutSeconds
