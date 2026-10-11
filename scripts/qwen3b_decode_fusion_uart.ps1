param(
    [ValidateSet('paired', 'full')]
    [string]$Gate = 'paired',
    [string]$Port = 'COM3',
    [string]$ExpectedFtdiSerial = 'XFL1PL5N11BJB',
    [string]$CandidateRoot = '/home/ubuntu/tellme_qwen25_3b/decode_fusion_candidate',
    [string]$WebRoot = '/home/ubuntu/tellme_qwen25_3b_web',
    [string]$LogPath = 'tmp\qwen3b_decode_fusion_uart.log',
    [int]$TimeoutSeconds = 480
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
foreach ($path in @($CandidateRoot, $WebRoot)) {
    if ($path -notmatch '^/home/ubuntu/[A-Za-z0-9_./-]+$') {
        throw "Board path contains unsupported shell characters: $path"
    }
}

$workspace = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
$resolvedLog = Join-Path $workspace $LogPath
New-Item -ItemType Directory -Force -Path (Split-Path $resolvedLog) | Out-Null
Set-Content -LiteralPath $resolvedLog -Value '' -Encoding utf8

$gateScript = if ($Gate -eq 'paired') { 'run_paired_gate.sh' } else { 'run_candidate_gates.sh' }
$marker = "__QWEN3B_DECODE_$($Gate.ToUpperInvariant())_RC_"
$inner = "bash $WebRoot/stop_web.sh && cd $CandidateRoot && bash $gateScript"
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
                if ($code -ne 0) { throw "Decode fusion gate failed with exit code $code" }
                Write-Output "QWEN3B_DECODE_FUSION_UART_COMPLETE gate=$Gate rc=$code"
                exit 0
            }
        }
        Start-Sleep -Milliseconds 100
    }
    throw "Timed out waiting for Decode fusion gate after $TimeoutSeconds seconds"
} finally {
    if ($serial.IsOpen) { $serial.Close() }
    $serial.Dispose()
}
