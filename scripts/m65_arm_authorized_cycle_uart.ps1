param(
    [string]$Port = 'COM3',
    [string]$ExpectedFtdiSerial = 'XFL1PL5N11BJB',
    [string]$LogPath = 'tmp\m65_authorized_cycle_arm_uart.log',
    [int]$TimeoutSeconds = 120
)

$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest

$candidateRoot = '/home/ubuntu/tellme_mage_m65_smoke/cycle'
$armScript = 'arm_m65_reserved1664_cycle.sh'
$armSha = 'b322aca86c1f6581d869d209586652fd3c1cbcbdc37601edadebfbb7e9bd0e45'
$marker = '__MAGE_M65_AUTHORIZED_ARM_RC_'

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

# The check-only command and the real arm run in the same UART shell and are
# chained with &&.  A failed hash or preflight therefore makes the arm
# unreachable.  The board package itself owns rollback and reboot scheduling.
$inner = "cd $candidateRoot && echo '$armSha  $armScript' | sha256sum -c - && sudo -n bash $armScript --check-only && sudo -n bash $armScript"
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
                    throw "M65 authorized arm failed with exit code $code"
                }
                Write-Output 'MAGE_M65_AUTHORIZED_ARM_UART_COMPLETE'
                exit 0
            }
        }
        Start-Sleep -Milliseconds 100
    }
    throw "Timed out waiting for M65 authorized arm after $TimeoutSeconds seconds"
} finally {
    if ($serial.IsOpen) { $serial.Close() }
    $serial.Dispose()
}
