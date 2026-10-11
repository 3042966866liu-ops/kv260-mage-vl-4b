param(
    [string]$Port = 'COM3',
    [string]$ExpectedFtdiSerial = 'XFL1PL5N11BJB',
    [string]$CandidateRoot = '/home/ubuntu/tellme_qwen25_3b/decode_tristream_candidate',
    [ValidateSet('Lifecycle', 'PostLifecycle', 'ThreadSweep', 'Full')]
    [string]$Mode = 'Full',
    [string]$LogPath = 'tmp\qwen3b_tristream_full_uart.log',
    [int]$TimeoutSeconds = 2400
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
if ($CandidateRoot -notmatch '^/home/ubuntu/[A-Za-z0-9_./-]+$') {
    throw "CandidateRoot contains unsupported shell characters"
}

$workspace = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
$resolvedLog = Join-Path $workspace $LogPath
New-Item -ItemType Directory -Force -Path (Split-Path $resolvedLog) | Out-Null
Set-Content -LiteralPath $resolvedLog -Value '' -Encoding utf8

$modeKey = $Mode.ToLowerInvariant()
$marker = "__QWEN3B_TRISTREAM_$($modeKey.ToUpperInvariant())_RC_"
$gateScript = if ($Mode -eq 'Lifecycle') {
    'run_lifecycle_gate.sh'
} elseif ($Mode -eq 'ThreadSweep') {
    'run_thread_sweep.sh'
} else {
    'run_full_board_gate.sh'
}
$gateCommand = if ($Mode -eq 'PostLifecycle') {
    "TELLME_SKIP_OVERLAY_LIFECYCLE=1 bash $gateScript"
} else {
    "bash $gateScript"
}
$inner = "cd $CandidateRoot && $gateCommand"
$command = "sudo -n -E sh -c '$inner'; rc=`$?; echo ${marker}`${rc}__"

$serial = [System.IO.Ports.SerialPort]::new(
    $Port,
    115200,
    [System.IO.Ports.Parity]::None,
    8,
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
                $captured.ToString(),
                [regex]::Escape($marker) + '(\d+)__'
            )
            if ($match.Success) {
                $code = [int]$match.Groups[1].Value
                if ($code -ne 0) {
                    throw "Tri-stream $Mode board gate failed with exit code $code"
                }
                Write-Output "QWEN3B_TRISTREAM_UART_COMPLETE mode=$Mode rc=$code"
                exit 0
            }
        }
        Start-Sleep -Milliseconds 100
    }
    throw "Timed out waiting for tri-stream $Mode gate after $TimeoutSeconds seconds"
} finally {
    if ($serial.IsOpen) { $serial.Close() }
    $serial.Dispose()
}
