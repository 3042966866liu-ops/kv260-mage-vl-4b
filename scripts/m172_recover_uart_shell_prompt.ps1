[CmdletBinding()]
param(
    [string]$Port = 'COM3',
    [string]$ExpectedFtdiSerial = 'XFL1PL5N11BJB',
    [string]$LogPath = 'tmp\m172_uart_recovery\run_01_uart.log',
    [int]$TimeoutSeconds = 20
)

$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest
$workspace = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
$fullLog = Join-Path $workspace $LogPath
if (Test-Path -LiteralPath $fullLog) { throw "M172 log already exists: $fullLog" }
New-Item -ItemType Directory -Force -Path (Split-Path -Parent $fullLog) | Out-Null

$device = Get-CimInstance Win32_PnPEntity | Where-Object { $_.Name -match "\($([regex]::Escape($Port))\)$" }
if (-not $device -or $device.PNPDeviceID -notmatch [regex]::Escape($ExpectedFtdiSerial)) {
    throw 'M172_COM3_IDENTITY_FAIL'
}

$serial = [IO.Ports.SerialPort]::new($Port,115200,[IO.Ports.Parity]::None,8,[IO.Ports.StopBits]::One)
$serial.Handshake = [IO.Ports.Handshake]::None
$serial.Encoding = [Text.Encoding]::UTF8
$serial.NewLine = "`n"
$serial.ReadTimeout = 250
$serial.WriteTimeout = 2000
$buffer = [Text.StringBuilder]::new()
try {
    $serial.Open()
    $serial.Write([char]3)
    Start-Sleep -Milliseconds 200
    $serial.Write([char]3)
    $serial.Write("`n")
    Start-Sleep -Milliseconds 300
    $serial.WriteLine('echo __M172_UART_PROMPT_RECOVERED__')
    $deadline = [DateTime]::UtcNow.AddSeconds($TimeoutSeconds)
    while ([DateTime]::UtcNow -lt $deadline) {
        $chunk = $serial.ReadExisting()
        if ($chunk.Length -gt 0) {
            [void]$buffer.Append($chunk)
            [IO.File]::AppendAllText($fullLog,$chunk,[Text.Encoding]::UTF8)
            Write-Host -NoNewline $chunk
            if ($buffer.ToString() -match '__M172_UART_PROMPT_RECOVERED__') {
                Write-Output 'M172_UART_PROMPT_RECOVERY_PASS'
                exit 0
            }
        }
        Start-Sleep -Milliseconds 40
    }
    throw 'M172_UART_PROMPT_RECOVERY_TIMEOUT'
} finally {
    if ($serial.IsOpen) { $serial.Close() }
    $serial.Dispose()
}
