param(
    [string]$Port = 'COM3',
    [string]$ExpectedFtdiSerial = 'XFL1PL5N11BJB',
    [string]$LogPath = 'tmp\m19_authorized_cycle_arm_uart.log',
    [int]$TimeoutSeconds = 120
)

$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest

$candidateRoot = '/home/ubuntu/tellme_qwen25_3b/directddr_chain_highddr_candidate'
$armScript = 'arm_reserved1664_authorized_cycle.sh'
$armSha = 'dcac87a33414255c627d3de2d4a835704442c57fdb032637a0a8b363734c74b3'
$marker = '__QWEN_M19_AUTHORIZED_ARM_RC_'

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

$inner = "cd $candidateRoot && echo '$armSha  $armScript' | sha256sum -c - && sudo -n -E bash $armScript"
$command = "$inner; rc=`$?; echo ${marker}`${rc}__"
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
            $match = [regex]::Match(
                $captured.ToString(), [regex]::Escape($marker) + '(\d+)__'
            )
            if ($match.Success) {
                $code = [int]$match.Groups[1].Value
                if ($code -ne 0) {
                    throw "M19 authorized arm failed with exit code $code"
                }
                Write-Output 'QWEN_M19_AUTHORIZED_ARM_UART_COMPLETE'
                exit 0
            }
        }
        Start-Sleep -Milliseconds 100
    }
    throw "Timed out waiting for M19 authorized arm after $TimeoutSeconds seconds"
} finally {
    if ($serial.IsOpen) { $serial.Close() }
    $serial.Dispose()
}
