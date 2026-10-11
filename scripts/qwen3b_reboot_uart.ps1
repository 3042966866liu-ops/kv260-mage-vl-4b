param(
    [string]$Port = 'COM3',
    [string]$ExpectedFtdiSerial = 'XFL1PL5N11BJB',
    [string]$LogPath = 'tmp\qwen3b_cma2048_reboot_uart.log',
    [int]$TimeoutSeconds = 20
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

$marker = '__QWEN3B_CMA2048_REBOOT_SCHEDULED__'
$command = 'sudo -n sh -c ''sync; nohup sh -c "sleep 2; systemctl reboot" >/dev/null 2>&1 &'' && echo ' + $marker
$serial = [System.IO.Ports.SerialPort]::new(
    $Port, 115200, [System.IO.Ports.Parity]::None, 8,
    [System.IO.Ports.StopBits]::One
)
$serial.Handshake = [System.IO.Ports.Handshake]::None
$serial.Encoding = [Text.Encoding]::UTF8
$serial.NewLine = "`n"
$serial.ReadTimeout = 250
$serial.WriteTimeout = 2000
$captured = [System.Text.StringBuilder]::new()

try {
    $serial.Open()
    $serial.Write("`n")
    Start-Sleep -Milliseconds 300
    $serial.WriteLine($command)
    $deadline = [DateTime]::UtcNow.AddSeconds($TimeoutSeconds)
    while ([DateTime]::UtcNow -lt $deadline) {
        $chunk = $serial.ReadExisting()
        if ($chunk.Length -gt 0) {
            [void]$captured.Append($chunk)
            [System.IO.File]::AppendAllText($resolvedLog, $chunk)
            Write-Host -NoNewline $chunk
            $markerPattern = '(?:^|[\r\n])' + [regex]::Escape($marker) + '(?:\r?\n|$)'
            if ([regex]::IsMatch($captured.ToString(), $markerPattern)) {
                Write-Output 'QWEN3B_CMA2048_REBOOT_UART_COMPLETE'
                exit 0
            }
        }
        Start-Sleep -Milliseconds 100
    }
    throw "Timed out waiting for reboot scheduling marker after $TimeoutSeconds seconds"
} finally {
    if ($serial.IsOpen) { $serial.Close() }
    $serial.Dispose()
}
