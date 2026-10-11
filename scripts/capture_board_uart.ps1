param(
    [string]$Port = 'COM3',
    [string]$ExpectedFtdiSerial = 'XFL1PL5N11BJB',
    [string]$LogPath = 'tmp\board_uart_capture.log',
    [int]$Seconds = 15,
    [switch]$ProbeNewline,
    [switch]$StopAutoboot,
    [switch]$SkipDeviceIdentityCheck
)

$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest

if (-not $SkipDeviceIdentityCheck) {
    $device = Get-CimInstance Win32_PnPEntity | Where-Object {
        $_.Name -match "\($([regex]::Escape($Port))\)$"
    }
    if (-not $device) { throw "Serial port $Port is not present" }
    if ($ExpectedFtdiSerial -and $device.PNPDeviceID -notmatch [regex]::Escape($ExpectedFtdiSerial)) {
        throw "Serial port $Port does not match expected FTDI serial $ExpectedFtdiSerial"
    }
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
$serial.ReadTimeout = 250
$serial.WriteTimeout = 2000

try {
    $serial.Open()
    if ($ProbeNewline) { $serial.Write("`n") }
    $captured = [System.Text.StringBuilder]::new()
    $stopped = $false
    $deadline = [DateTime]::UtcNow.AddSeconds($Seconds)
    while ([DateTime]::UtcNow -lt $deadline) {
        $chunk = $serial.ReadExisting()
        if ($chunk.Length -gt 0) {
            [void]$captured.Append($chunk)
            [System.IO.File]::AppendAllText($resolvedLog, $chunk)
            Write-Host -NoNewline $chunk
            if ($StopAutoboot -and -not $stopped -and
                $captured.ToString() -match 'Hit any key to stop autoboot') {
                $serial.Write(' ')
                $stopped = $true
            }
            if ($StopAutoboot -and $stopped -and
                $captured.ToString() -match 'ZynqMP>\s*$') {
                Write-Output 'BOARD_UART_UBOOT_PROMPT_PASS'
                exit 0
            }
        }
        Start-Sleep -Milliseconds 100
    }
    Write-Output 'BOARD_UART_CAPTURE_COMPLETE'
} finally {
    if ($serial.IsOpen) { $serial.Close() }
    $serial.Dispose()
}
