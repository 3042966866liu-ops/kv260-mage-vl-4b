param(
    [string]$Port = "COM3",
    [string]$ExpectedFtdiSerial = "XFL1PL5N11BJB",
    [string]$WebRoot = "/home/ubuntu/tellme_qwen25_3b_web",
    [switch]$Restart,
    [int]$TimeoutSeconds = 30
)

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

$device = Get-CimInstance Win32_PnPEntity | Where-Object {
    $_.Name -match "\($([regex]::Escape($Port))\)$"
}
if (-not $device) { throw "Serial port $Port is not present" }
if ($ExpectedFtdiSerial -and $device.PNPDeviceID -notmatch [regex]::Escape($ExpectedFtdiSerial)) {
    throw "Serial port $Port does not match expected FTDI serial $ExpectedFtdiSerial"
}
if ($WebRoot -notmatch '^/home/ubuntu/[A-Za-z0-9_./-]+$') {
    throw "WebRoot contains unsupported shell characters"
}

$marker = "__WEB3B_START_RC_"
$launch = "cd $WebRoot; nohup bash start_web.sh > $WebRoot/web3b_server.log 2>&1 < /dev/null & echo `$! > $WebRoot/web3b_server.pid"
if ($Restart) {
    $inner = "cd $WebRoot && bash stop_web.sh; $launch"
    $command = "sudo -n -E sh -c '$inner'; rc=`$?; echo ${marker}`${rc}__"
} else {
    $command = "if test -f $WebRoot/web3b_server.pid && kill -0 `$(cat $WebRoot/web3b_server.pid) 2>/dev/null; then echo WEB3B_ALREADY_RUNNING; else sudo -n -E sh -c '$launch'; fi; rc=`$?; echo ${marker}`${rc}__"
}

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
            Write-Host -NoNewline $chunk
            $match = [regex]::Match(
                $captured.ToString(),
                [regex]::Escape($marker) + '(\d+)__'
            )
            if ($match.Success) {
                $code = [int]$match.Groups[1].Value
                if ($code -ne 0) { throw "Web server launch failed with exit code $code" }
                Write-Output "WEB3B_UART_START_COMPLETE"
                exit 0
            }
        }
        Start-Sleep -Milliseconds 100
    }
    throw "Timed out waiting for Web server launch marker"
} finally {
    if ($serial.IsOpen) { $serial.Close() }
    $serial.Dispose()
}
