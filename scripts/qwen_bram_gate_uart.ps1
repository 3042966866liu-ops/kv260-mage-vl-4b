param(
    [ValidateSet('smoke', 'linear', 'profile', 'e2e', 'capture', 'lmhead', 'calibrate')]
    [string]$Gate = 'smoke',
    [string]$Port = 'COM3',
    [string]$ExpectedFtdiSerial = 'XFL1PL5N11BJB',
    [string]$Root = '/home/ubuntu/tellme_qwen25_15b_bram',
    [int]$TimeoutSeconds = 900
)

$ErrorActionPreference = 'Stop'
$device = Get-CimInstance Win32_PnPEntity | Where-Object {
    $_.Name -match "\($([regex]::Escape($Port))\)$"
}
if (-not $device) {
    throw "Serial port $Port is not present."
}
if ($ExpectedFtdiSerial -and $device.PNPDeviceID -notmatch [regex]::Escape($ExpectedFtdiSerial)) {
    throw "Serial port $Port does not match expected FTDI serial $ExpectedFtdiSerial."
}

$scriptName = @{
    smoke = 'hardware_smoke.py'
    linear = 'linear_golden.py'
    profile = 'profile_baseline.py'
    e2e = 'llm_e2e.py'
    capture = 'capture_lm_head_hidden.py'
    lmhead = 'lm_head_fpga_smoke.py'
    calibrate = 'calibrate_lm_head_shortlist.py'
}[$Gate]
$python = '/usr/local/share/pynq-venv/bin/python3'
$toolPath = '/usr/local/share/pynq-venv/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin'
$marker = "__CODEX_$($Gate.ToUpperInvariant())_RC_"
$pythonPath = "$Root/runtime:$Root/runtime/vendor"
$command = "cd $Root && sudo -n -E env PATH=$toolPath PYTHONPATH=$pythonPath $python runtime/$scriptName --root $Root; rc=`$?; echo ${marker}`${rc}__"

$serial = [System.IO.Ports.SerialPort]::new(
    $Port,
    115200,
    [System.IO.Ports.Parity]::None,
    8,
    [System.IO.Ports.StopBits]::One
)
$serial.Handshake = [System.IO.Ports.Handshake]::None
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
            $match = [regex]::Match($captured.ToString(), [regex]::Escape($marker) + '(\d+)__')
            if ($match.Success) {
                $code = [int]$match.Groups[1].Value
                if ($code -ne 0) {
                    throw "Board gate '$Gate' failed with exit code $code."
                }
                Write-Output "QWEN_UART_GATE_COMPLETE gate=$Gate rc=$code"
                exit 0
            }
        }
        Start-Sleep -Milliseconds 100
    }
    throw "Timed out waiting for board gate '$Gate' after $TimeoutSeconds seconds."
}
finally {
    if ($serial.IsOpen) {
        $serial.Close()
    }
    $serial.Dispose()
}
