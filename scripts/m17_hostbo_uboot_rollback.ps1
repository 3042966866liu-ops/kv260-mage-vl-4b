param(
    [string]$Port = 'COM3',
    [string]$ExpectedFtdiSerial = 'XFL1PL5N11BJB',
    [string]$LogPath = 'tmp\m17_hostbo_uboot_rollback.log',
    [int]$CommandTimeoutSeconds = 20
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
$serial.ReadTimeout = 250
$serial.WriteTimeout = 2000

function Receive-Prompt([string]$Label) {
    $captured = [System.Text.StringBuilder]::new()
    $deadline = [DateTime]::UtcNow.AddSeconds($CommandTimeoutSeconds)
    while ([DateTime]::UtcNow -lt $deadline) {
        $chunk = $serial.ReadExisting()
        if ($chunk.Length -gt 0) {
            [void]$captured.Append($chunk)
            [System.IO.File]::AppendAllText($resolvedLog, $chunk)
            Write-Host -NoNewline $chunk
            if ($captured.ToString() -match 'ZynqMP>\s*$') {
                return $captured.ToString()
            }
        }
        Start-Sleep -Milliseconds 100
    }
    throw "Timed out waiting for U-Boot prompt after $Label"
}

function Invoke-Uboot([string]$Command) {
    [System.IO.File]::AppendAllText($resolvedLog, "`n# $Command`n")
    $serial.WriteLine($Command)
    return Receive-Prompt $Command
}

try {
    $serial.Open()
    $serial.DiscardInBuffer()
    $serial.Write("`n")
    [void](Receive-Prompt 'initial synchronization')

    $mmc = Invoke-Uboot 'mmc dev 1'
    if ($mmc -notmatch 'mmc1 is current device|switch to partitions #0, OK') {
        throw 'MMC device 1 selection was not confirmed'
    }

    $backup = Invoke-Uboot 'fatload mmc 1:1 0x08000000 boot.scr.uimg.tellme-pre-hostbo1900'
    if ($backup -notmatch '8378 bytes read') {
        throw 'Stable Host-BO backup size was not exactly 8378 bytes'
    }
    $backupCrc = Invoke-Uboot 'crc32 0x08000000 0x20ba'
    if ($backupCrc -notmatch '(?i)da11b149') {
        throw 'Stable Host-BO backup CRC32 mismatch'
    }

    $write = Invoke-Uboot 'fatwrite mmc 1:1 0x08000000 boot.scr.uimg 0x20ba'
    if ($write -notmatch '8378 bytes written') {
        throw 'Stable active boot write size was not exactly 8378 bytes'
    }

    $active = Invoke-Uboot 'fatload mmc 1:1 0x08000000 boot.scr.uimg'
    if ($active -notmatch '8378 bytes read') {
        throw 'Restored active boot size was not exactly 8378 bytes'
    }
    $activeCrc = Invoke-Uboot 'crc32 0x08000000 0x20ba'
    if ($activeCrc -notmatch '(?i)da11b149') {
        throw 'Restored active boot CRC32 mismatch'
    }

    [void](Invoke-Uboot 'fatrm mmc 1:1 user-override.dtb')
    $absence = Invoke-Uboot 'fatload mmc 1:1 0x08000000 user-override.dtb'
    if ($absence -notmatch "(?i)(Unable to read file|File not found|Failed to load)") {
        throw 'Candidate user-override.dtb still appears readable after removal'
    }

    Write-Output 'QWEN_HOSTBO_UBOOT_ROLLBACK_PASS_NO_REBOOT'
} finally {
    if ($serial.IsOpen) { $serial.Close() }
    $serial.Dispose()
}
