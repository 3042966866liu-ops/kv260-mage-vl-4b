param(
    [Parameter(Mandatory=$true)][string]$Command,
    [string]$Port = 'COM3',
    [string]$ExpectedFtdiSerial = 'XFL1PL5N11BJB',
    [string]$LogPath = 'tmp\m75c_uart_command.log',
    [int]$TimeoutSeconds = 30,
    [string]$MarkerPrefix = '__M75C_UART_RC_',
    [ValidateRange(16,256)][int]$WriteSliceChars = 64,
    [ValidateRange(1,100)][int]$WritePauseMs = 10,
    [switch]$DeviceIdentitySelfTest
)

$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest

$device = @()
$cimError = $null
try {
    $device = @(Get-CimInstance Win32_PnPEntity | Where-Object {
        $_.Name -match "\($([regex]::Escape($Port))\)$"
    })
} catch { $cimError = $_ }
if (-not $device.Count -and $cimError) {
    # Some managed Windows sessions deny CIM/WMI queries. Fall back to the
    # built-in PnP inventory, while retaining the exact port and FTDI serial
    # checks before opening COM3.
    $inventory = @(& pnputil.exe /enum-devices /class Ports 2>&1)
    if ($LASTEXITCODE -ne 0) { throw "CIM unavailable and pnputil inventory failed: $cimError" }
    $records = (($inventory | ForEach-Object { [string]$_ }) -join "`n") -split "(?:\r?\n){2,}"
    $matchedDevices = @()
    foreach ($record in $records) {
        $description = [regex]::Match($record, '(?m)^\s*Device Description:\s*(.+?)\s*$')
        $instance = [regex]::Match($record, '(?m)^\s*Instance ID:\s*(.+?)\s*$')
        if ($description.Success -and $instance.Success -and
            $description.Groups[1].Value -match "\($([regex]::Escape($Port))\)$") {
            $matchedDevices += [pscustomobject]@{ PNPDeviceID = $instance.Groups[1].Value; Name = $description.Groups[1].Value }
        }
    }
    $device = $matchedDevices
}
if ($device.Count -ne 1) { throw "Serial port $Port identity is missing or ambiguous" }
if ($ExpectedFtdiSerial -and $device[0].PNPDeviceID -notmatch [regex]::Escape($ExpectedFtdiSerial)) {
    throw "Serial port $Port does not match expected FTDI serial $ExpectedFtdiSerial"
}
if ($DeviceIdentitySelfTest) {
    Write-Output "M75C_DEVICE_IDENTITY_PASS $Port $($device[0].PNPDeviceID)"
    exit 0
}

$workspace = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
$resolvedLog = Join-Path $workspace $LogPath
New-Item -ItemType Directory -Force -Path (Split-Path $resolvedLog) | Out-Null
Set-Content -LiteralPath $resolvedLog -Value '' -Encoding utf8

$marker = $MarkerPrefix
$wrapped = "$Command; rc=`$?; echo ${marker}`${rc}__"
$serial = [System.IO.Ports.SerialPort]::new(
    $Port, 115200, [System.IO.Ports.Parity]::None, 8,
    [System.IO.Ports.StopBits]::One
)
$serial.Handshake = [System.IO.Ports.Handshake]::None
$serial.Encoding = [Text.Encoding]::UTF8
$serial.NewLine = "`n"
$serial.ReadTimeout = 250
$serial.WriteTimeout = 2000
$serial.ReadBufferSize = 65536
$captured = [System.Text.StringBuilder]::new()
$taskMarkerTail = ''
$taskMarkerPattern = [regex]::Escape($marker) + '(\d+)__'

try {
    $serial.Open()
    $serial.Write("`n")
    # Never send a command into login/password or continuation prompts.
    $promptDeadline = [DateTime]::UtcNow.AddSeconds(5)
    $promptConfirmed = $false
    while ([DateTime]::UtcNow -lt $promptDeadline) {
        $promptChunk = $serial.ReadExisting()
        if ($promptChunk.Length -gt 0) {
            [void]$captured.Append($promptChunk)
            [System.IO.File]::AppendAllText($resolvedLog, $promptChunk)
            Write-Host -NoNewline $promptChunk
            $promptText = $captured.ToString()
            if ($promptText -match '(?m)(?:login:|Password:|password:)\s*$') {
                throw 'COM3 requires operator login; no command was sent'
            }
            if ($promptText -match '(?m)^>\s*$') {
                throw 'COM3 continuation prompt; use the fixed recovery procedure'
            }
            if ($promptText -match '(?m)(?:ubuntu|root)@kria:[^\r\n]*[\$#]\s*$') {
                $promptConfirmed = $true
                break
            }
        }
        Start-Sleep -Milliseconds 100
    }
    if (-not $promptConfirmed) { throw 'COM3 shell prompt not confirmed; no command was sent' }
    # Bound each host write instead of bursting an entire echoed command.
    # Keep prompt authorization, original rc and whole-file SHA checks intact.
    for ($offset = 0; $offset -lt $wrapped.Length; $offset += $WriteSliceChars) {
        $count = [Math]::Min($WriteSliceChars, $wrapped.Length - $offset)
        $serial.Write($wrapped.Substring($offset, $count))
        Start-Sleep -Milliseconds $WritePauseMs
    }
    $serial.Write("`n")
    $deadline = [DateTime]::UtcNow.AddSeconds($TimeoutSeconds)
    while ([DateTime]::UtcNow -lt $deadline) {
        $chunk = $serial.ReadExisting()
        if ($chunk.Length -gt 0) {
            [void]$captured.Append($chunk)
            [System.IO.File]::AppendAllText($resolvedLog, $chunk)
            Write-Host -NoNewline $chunk
            # Preserve complete evidence, but inspect only new bytes and a bounded
            # overlap for the exit marker. Avoid copying/scanning the full log
            # on every read as saved-result output grows to several MiB.
            $taskMarkerWindow = $taskMarkerTail + $chunk
            $match = [regex]::Match($taskMarkerWindow, $taskMarkerPattern)
            $taskMarkerTail = $taskMarkerWindow.Substring([Math]::Max(0,$taskMarkerWindow.Length-512))
            if ($match.Success) {
                $code = [int]$match.Groups[1].Value
                if ($code -ne 0) {
                    throw "UART command failed with exit code $code"
                }
                Write-Output "M75C_UART_COMMAND_COMPLETE rc=$code"
                exit 0
            }
        }
        Start-Sleep -Milliseconds 100
    }
    throw "Timed out waiting for UART command marker"
} finally {
    if ($serial.IsOpen) { $serial.Close() }
    $serial.Dispose()
}
