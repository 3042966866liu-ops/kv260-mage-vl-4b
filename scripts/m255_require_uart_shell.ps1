[CmdletBinding()]
param(
    [string]$Port = 'COM3',
    [string]$ExpectedFtdiSerial = 'XFL1PL5N11BJB',
    [string]$LogPath = 'tmp\m255_session_attach\shell_probe_uart.log'
)

$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest
$workspace = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
$resolvedLog = Join-Path $workspace $LogPath
New-Item -ItemType Directory -Force -Path (Split-Path $resolvedLog) | Out-Null
Set-Content -LiteralPath $resolvedLog -Value '' -Encoding utf8
$device = Get-CimInstance Win32_PnPEntity | Where-Object { $_.Name -match "\($([regex]::Escape($Port))\)$" }
if (-not $device) { throw "Serial port $Port is not present" }
if ($ExpectedFtdiSerial -and $device.PNPDeviceID -notmatch [regex]::Escape($ExpectedFtdiSerial)) {
    throw "Serial port $Port does not match expected FTDI serial $ExpectedFtdiSerial"
}
$serial = [System.IO.Ports.SerialPort]::new($Port,115200,[System.IO.Ports.Parity]::None,8,[System.IO.Ports.StopBits]::One)
$serial.Encoding = [Text.Encoding]::UTF8
$serial.ReadTimeout = 250
$serial.WriteTimeout = 2000
try {
    $serial.Open()
    $serial.Write("`n")
    $deadline = [DateTime]::UtcNow.AddSeconds(8)
    $captured = [Text.StringBuilder]::new()
    while ([DateTime]::UtcNow -lt $deadline) {
        $chunk = $serial.ReadExisting()
        if ($chunk.Length -gt 0) {
            [void]$captured.Append($chunk)
            [IO.File]::AppendAllText($resolvedLog,$chunk)
            if ($captured.ToString() -match 'ubuntu@kria:.*[$#]') {
                Write-Output 'M255_UART_EXISTING_SHELL_PASS'
                exit 0
            }
            if ($captured.ToString() -match 'login:') {
                throw 'KV260 is at login prompt; no upload or command was attempted.'
            }
        }
        Start-Sleep -Milliseconds 100
    }
    throw 'M255 could not prove an existing authenticated UART shell; no upload or command was attempted.'
} finally {
    if ($serial.IsOpen) { $serial.Close() }
    $serial.Dispose()
}
