param(
    [string]$Port = 'COM3',
    [string]$ExpectedFtdiSerial = 'XFL1PL5N11BJB',
    [string]$CandidateRoot = '/home/ubuntu/tellme_qwen25_3b/directddr_candidate',
    [ValidateSet('Smoke', 'LayerBenchmark', 'FusedLayerBenchmark', 'LMHeadBenchmark', 'NonlinearProfile', 'ChainBoardGate', 'ResidentLifecycle', 'ResidentFullE2E', 'CmaInstall', 'CmaRollback', 'HighCmaCheck', 'HighCmaInstall', 'HighCmaRollback', 'HighSmoke', 'HighResidentFullE2E', 'DTCmaCheck', 'DTCmaInstall', 'DTCmaRollback', 'DTHighSmoke', 'DTResidentFullE2E', 'HostBOCheck', 'HostBOInstall', 'HostBORollback', 'HostBOSmoke', 'HostBOResidentFullE2E', 'OfflineHighDDRAudit', 'OfflineHighDDRShiftProbe', 'OfflineHighDDRFullGate', 'Reserved1664Check', 'Reserved1664Install', 'Reserved1664Rollback', 'Reserved1664Prepare', 'Reserved1664FullGate', 'Reboot', 'WebRestore')]
    [string]$Mode = 'Smoke',
    [string]$LogPath = 'tmp\qwen3b_directddr_uart.log',
    [int]$TimeoutSeconds = 300
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
    throw 'CandidateRoot contains unsupported shell characters'
}

$workspace = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
$resolvedLog = Join-Path $workspace $LogPath
New-Item -ItemType Directory -Force -Path (Split-Path $resolvedLog) | Out-Null
Set-Content -LiteralPath $resolvedLog -Value '' -Encoding utf8

$marker = '__QWEN3B_DIRECTDDR_RC_'
$gateScript = if ($Mode -eq 'Reboot') {
    ''
} elseif ($Mode -eq 'WebRestore') {
    'restore_stable_web_after_cma.sh'
} elseif ($Mode -eq 'HostBORollback') {
    'rollback_hostbo800_boot.sh'
} elseif ($Mode -in @('HostBOCheck', 'HostBOInstall')) {
    'install_hostbo1900_boot.sh'
} elseif ($Mode -eq 'HostBOResidentFullE2E') {
    'run_resident_full_e2e_hostbo_gate.sh'
} elseif ($Mode -eq 'HostBOSmoke') {
    'run_hostbo_highddr_smoke_gate.sh'
} elseif ($Mode -eq 'OfflineHighDDRFullGate') {
    'run_offline_highddr_full_gate.sh'
} elseif ($Mode -eq 'OfflineHighDDRShiftProbe') {
    'probe_shifted_highddr_blocks.sh'
} elseif ($Mode -eq 'OfflineHighDDRAudit') {
    'audit_highddr_offline_failure.sh'
} elseif ($Mode -eq 'Reserved1664Rollback') {
    'rollback_reserved1664_boot.sh'
} elseif ($Mode -in @('Reserved1664Check', 'Reserved1664Install')) {
    'install_reserved1664_boot.sh'
} elseif ($Mode -eq 'Reserved1664Prepare') {
    'prepare_reserved1664_full_gate.sh'
} elseif ($Mode -eq 'Reserved1664FullGate') {
    'run_reserved1664_full_gate.sh'
} elseif ($Mode -eq 'DTCmaRollback') {
    'rollback_dtcma800_boot.sh'
} elseif ($Mode -in @('DTCmaCheck', 'DTCmaInstall')) {
    'install_dtcma1900_boot.sh'
} elseif ($Mode -eq 'DTResidentFullE2E') {
    'run_resident_full_e2e_dtcma_gate.sh'
} elseif ($Mode -eq 'DTHighSmoke') {
    'run_dtcma_highddr_smoke_gate.sh'
} elseif ($Mode -eq 'HighCmaRollback') {
    'rollback_cma800_high_boot.sh'
} elseif ($Mode -in @('HighCmaCheck', 'HighCmaInstall')) {
    'install_cma1900_high_boot.sh'
} elseif ($Mode -eq 'HighResidentFullE2E') {
    'run_resident_full_e2e_highddr_gate.sh'
} elseif ($Mode -eq 'HighSmoke') {
    'run_highddr_smoke_gate.sh'
} elseif ($Mode -eq 'CmaRollback') {
    'capture_and_rollback_cma2048.sh'
} elseif ($Mode -eq 'CmaInstall') {
    'install_cma2048_boot.sh'
} elseif ($Mode -eq 'ResidentFullE2E') {
    'run_resident_full_e2e_gate.sh'
} elseif ($Mode -eq 'ResidentLifecycle') {
    'run_resident_store_lifecycle_gate.sh'
} elseif ($Mode -eq 'ChainBoardGate') {
    'run_chain_board_gate.sh'
} elseif ($Mode -eq 'NonlinearProfile') {
    'run_nonlinear_profile_gate.sh'
} elseif ($Mode -eq 'LMHeadBenchmark') {
    'run_lm_head_benchmark_gate.sh'
} elseif ($Mode -in @('LayerBenchmark', 'FusedLayerBenchmark')) {
    'run_layer_benchmark_gate.sh'
} else {
    'run_single_linear_gate.sh'
}
$gateCommand = if ($Mode -eq 'Reboot') {
    'systemd-run --unit=tellme-reboot-once --on-active=2s /usr/bin/systemctl reboot'
} elseif ($Mode -in @('HighCmaCheck', 'DTCmaCheck', 'HostBOCheck', 'Reserved1664Check')) {
    "bash $gateScript --check-only"
} elseif ($Mode -eq 'FusedLayerBenchmark') {
    "TELLME_FUSED_LAYER=1 bash $gateScript"
} else {
    "bash $gateScript"
}
$reservedScriptSha = if ($Mode -in @('Reserved1664Check', 'Reserved1664Install')) {
    '4f63f9e1bd7ded6361433283ed5c6584fb59fc50688de76e908b7bc26347ee7e'
} elseif ($Mode -eq 'Reserved1664Rollback') {
    'e960a327f7ea11ab8b1a15580b4131bd0852e69f0d9b72f4788b057179056fbe'
} elseif ($Mode -eq 'Reserved1664Prepare') {
    '52ec38bfd65044e564457f7e08348c39176f128d5c94a8d13eaa924bff395061'
} elseif ($Mode -eq 'Reserved1664FullGate') {
    '5f18be56ec23d163ba24e0cd23b49a7adff5199b86c14223ea2d25c35f11a817'
} else {
    $null
}
if ($reservedScriptSha) {
    $gateCommand = "test `"`$(sha256sum $gateScript)`" = `"$reservedScriptSha  $gateScript`" && $gateCommand"
}
$inner = "cd $CandidateRoot && $gateCommand"
$command = "sudo -n -E sh -c '$inner'; rc=`$?; echo ${marker}`${rc}__"
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
                    throw "Direct-DDR board gate failed with exit code $code"
                }
                Write-Output "QWEN3B_DIRECTDDR_UART_COMPLETE rc=$code"
                exit 0
            }
        }
        Start-Sleep -Milliseconds 100
    }
    throw "Timed out waiting for Direct-DDR gate after $TimeoutSeconds seconds"
} finally {
    if ($serial.IsOpen) { $serial.Close() }
    $serial.Dispose()
}
