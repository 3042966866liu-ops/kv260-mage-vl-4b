param(
    [string]$Port = 'COM3',
    [string]$ExpectedFtdiSerial = 'XFL1PL5N11BJB',
    [string]$LogPath = 'tmp\m17_jtag_reset_to_uboot.log',
    [int]$TimeoutSeconds = 90
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
$resetTcl = (Resolve-Path (Join-Path $PSScriptRoot 'm17_jtag_system_reset.tcl')).Path
$xsdb = 'D:\AMDDesignTools\2026.1\Vitis\bin\xsdb.bat'
if (-not (Test-Path -LiteralPath $xsdb)) { throw "xsdb not found: $xsdb" }
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
$captured = [System.Text.StringBuilder]::new()
$stopped = $false
$xsdbProcess = $null

try {
    $serial.Open()
    $serial.DiscardInBuffer()
    $xsdbProcess = Start-Process -FilePath $xsdb -ArgumentList @($resetTcl) `
        -WindowStyle Hidden -PassThru
    $deadline = [DateTime]::UtcNow.AddSeconds($TimeoutSeconds)
    while ([DateTime]::UtcNow -lt $deadline) {
        $chunk = $serial.ReadExisting()
        if ($chunk.Length -gt 0) {
            [void]$captured.Append($chunk)
            [System.IO.File]::AppendAllText($resolvedLog, $chunk)
            Write-Host -NoNewline $chunk
            if (-not $stopped -and $captured.ToString() -match 'Hit any key to stop autoboot') {
                $serial.Write(' ')
                $stopped = $true
            }
            if ($stopped -and $captured.ToString() -match 'ZynqMP>\s*$') {
                Write-Output 'TELLME_JTAG_RESET_UBOOT_PROMPT_PASS'
                exit 0
            }
        }
        Start-Sleep -Milliseconds 100
    }
    throw "Timed out waiting for U-Boot prompt after $TimeoutSeconds seconds"
} finally {
    if ($serial.IsOpen) { $serial.Close() }
    $serial.Dispose()
    if ($null -ne $xsdbProcess -and -not $xsdbProcess.HasExited) {
        Stop-Process -Id $xsdbProcess.Id -Force -ErrorAction SilentlyContinue
    }
}
