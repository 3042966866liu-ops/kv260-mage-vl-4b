param(
    [string]$Port = 'COM3',
    [string]$ExpectedFtdiSerial = 'XFL1PL5N11BJB',
    [string]$LogPath = 'tmp\m19_uboot_reset_capture_uart.log',
    [int]$Seconds = 180
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

$workspace = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
$resolvedLog = Join-Path $workspace $LogPath
New-Item -ItemType Directory -Force -Path (Split-Path $resolvedLog) | Out-Null
Set-Content -LiteralPath $resolvedLog -Value '' -Encoding utf8

$serial = [System.IO.Ports.SerialPort]::new(
    $Port, 115200, [System.IO.Ports.Parity]::None, 8,
    [System.IO.Ports.StopBits]::One
)
$serial.Handshake = [System.IO.Ports.Handshake]::None
$serial.Encoding = [Text.Encoding]::UTF8
$serial.NewLine = "`n"
$serial.ReadTimeout = 250
$serial.WriteTimeout = 2000

try {
    $serial.Open()
    $serial.WriteLine('reset')
    Write-Output 'QWEN_M19_UBOOT_RESET_SENT'
    $deadline = [DateTime]::UtcNow.AddSeconds($Seconds)
    while ([DateTime]::UtcNow -lt $deadline) {
        $chunk = $serial.ReadExisting()
        if ($chunk.Length -gt 0) {
            [System.IO.File]::AppendAllText($resolvedLog, $chunk)
            Write-Host -NoNewline $chunk
        }
        Start-Sleep -Milliseconds 100
    }
    Write-Output 'QWEN_M19_UBOOT_RESET_CAPTURE_COMPLETE'
} finally {
    if ($serial.IsOpen) { $serial.Close() }
    $serial.Dispose()
}
