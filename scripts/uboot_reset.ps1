param(
    [string]$Port = 'COM3',
    [string]$ExpectedFtdiSerial = 'XFL1PL5N11BJB'
)

$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest
$device = Get-CimInstance Win32_PnPEntity | Where-Object {
    $_.Name -match "\($([regex]::Escape($Port))\)$"
}
if (-not $device) { throw "Serial port $Port is not present" }
if ($ExpectedFtdiSerial -and $device.PNPDeviceID -notmatch [regex]::Escape($ExpectedFtdiSerial)) {
    throw "Serial port $Port does not match expected FTDI serial $ExpectedFtdiSerial"
}
$serial = [System.IO.Ports.SerialPort]::new(
    $Port, 115200, [System.IO.Ports.Parity]::None, 8,
    [System.IO.Ports.StopBits]::One
)
$serial.Handshake = [System.IO.Ports.Handshake]::None
$serial.Encoding = [Text.Encoding]::UTF8
$serial.WriteTimeout = 2000
try {
    $serial.Open()
    $serial.WriteLine('reset')
    Start-Sleep -Milliseconds 300
    Write-Output 'UBOOT_RESET_SENT'
} finally {
    if ($serial.IsOpen) { $serial.Close() }
    $serial.Dispose()
}
