[CmdletBinding()]
param(
    [string]$Port = 'COM3',
    [string]$ExpectedFtdiSerial = 'XFL1PL5N11BJB',
    [string]$LogPath = 'tmp\m202_video_e2e\recover_prompt.log'
)
$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest
$device = Get-CimInstance Win32_PnPEntity | Where-Object { $_.Name -match "\($([regex]::Escape($Port))\)$" }
if (-not $device) { throw "Serial port $Port is not present" }
if ($device.PNPDeviceID -notmatch [regex]::Escape($ExpectedFtdiSerial)) { throw 'M202 FTDI identity mismatch' }
$workspace = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
$resolvedLog = Join-Path $workspace $LogPath
New-Item -ItemType Directory -Force -Path (Split-Path $resolvedLog) | Out-Null
Set-Content -LiteralPath $resolvedLog -Value '' -Encoding utf8
$serial = [System.IO.Ports.SerialPort]::new($Port,115200,[System.IO.Ports.Parity]::None,8,[System.IO.Ports.StopBits]::One)
$serial.Handshake = [System.IO.Ports.Handshake]::None
$serial.Encoding = [Text.Encoding]::UTF8
try {
    $serial.Open()
    $serial.Write([char]3)
    Start-Sleep -Milliseconds 300
    $serial.Write("`n")
    $deadline = [DateTime]::UtcNow.AddSeconds(5)
    $captured = [System.Text.StringBuilder]::new()
    while ([DateTime]::UtcNow -lt $deadline) {
        $chunk = $serial.ReadExisting()
        if ($chunk.Length -gt 0) {
            [void]$captured.Append($chunk)
            [System.IO.File]::AppendAllText($resolvedLog,$chunk)
            Write-Host -NoNewline $chunk
            if ($captured.ToString() -match 'ubuntu@kria:.*\$') {
                Write-Output 'M202_UART_PROMPT_RECOVERY_PASS'
                exit 0
            }
        }
        Start-Sleep -Milliseconds 100
    }
    throw 'M202 normal shell prompt was not observed after Ctrl+C'
} finally {
    if ($serial.IsOpen) { $serial.Close() }
    $serial.Dispose()
}
