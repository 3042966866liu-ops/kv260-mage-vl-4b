param(
    [ValidateSet('program', 'prefill-smoke', 'prefill-profile', 'linear-golden', 'lmhead-smoke', 'e2e', 'profile', 'all', 'paired', 'shared-probe', 'shared-suite', 'cma-bench', 'stage1-7b', 'stage2-7b', 'stage3-7b')]
    [string]$Gate = 'program',
    [string]$Port = 'COM3',
    [string]$ExpectedFtdiSerial = 'XFL1PL5N11BJB',
    [string]$Root = '/home/ubuntu/tellme_qwen25_15b/prefill_v1_candidate',
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

$gateName = @{
    program = 'program'
    'prefill-smoke' = 'prefill-hardware-smoke'
    'prefill-profile' = 'prefill-profile'
    'linear-golden' = 'linear-golden'
    e2e = 'llm-e2e'
    profile = 'profile-baseline'
    all = 'all'
    paired = 'paired'
    'shared-probe' = 'shared-probe'
    'shared-suite' = 'shared-suite'
    'cma-bench' = 'cma-bench'
    'lmhead-smoke' = 'lmhead-smoke'
}[$Gate]
$python = '/usr/local/share/pynq-venv/bin/python3'
$toolPath = '/usr/local/share/pynq-venv/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin'
$pythonPath = "$Root/runtime:$Root/runtime/vendor"
$marker = "__CODEX_PREFILL_$($Gate.ToUpperInvariant().Replace('-', '_'))_RC_"
$gateCommand = switch ($Gate) {
    'all' { "runtime/run_candidate_gates.sh" }
    'paired' { "runtime/run_paired_gate.sh" }
    'shared-probe' { "$python runtime/decode_via_prefill_probe.py --root $Root" }
    'shared-suite' { "$python runtime/decode_via_prefill_suite.py --root $Root" }
    'cma-bench' { "$python runtime/cma_copy_benchmark.py --root $Root" }
    'lmhead-smoke' { "$python runtime/lm_head_fpga_smoke.py --root $Root" }
    'stage1-7b' { "runtime/run_stage1_gate.sh" }
    'stage2-7b' { "runtime/run_stage2_gate.sh" }
    'stage3-7b' { "runtime/run_stage3_e2e.sh" }
    default { "$python runtime/gate_with_rollback.py $gateName --root $Root" }
}
$command = "cd $Root && sudo -n -E env PATH=$toolPath PYTHONPATH=$pythonPath $gateCommand; rc=`$?; echo ${marker}`${rc}__"

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
            $match = [regex]::Match(
                $captured.ToString(),
                [regex]::Escape($marker) + '(\d+)__'
            )
            if ($match.Success) {
                $code = [int]$match.Groups[1].Value
                if ($code -ne 0) {
                    throw "Board gate '$Gate' failed with exit code $code."
                }
                Write-Output "QWEN_PREFILL_UART_GATE_COMPLETE gate=$Gate rc=$code"
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
