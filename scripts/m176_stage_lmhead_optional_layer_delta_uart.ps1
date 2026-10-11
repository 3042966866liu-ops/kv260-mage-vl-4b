[CmdletBinding()]
param(
    [string]$Port = 'COM3',
    [string]$ExpectedFtdiSerial = 'XFL1PL5N11BJB',
    [string]$Attempt = '01',
    [int]$TimeoutSeconds = 600
)

$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest
$workspace = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
$python = 'C:\Users\30429\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe'
$deltaBuild = Get-Content -LiteralPath (Join-Path $workspace 'deployment\mage_vl4b\M176_M120_LMHEAD_OPTIONAL_LAYER_DELTA_RESULT.json') -Raw | ConvertFrom-Json
$fixBuild = Get-Content -LiteralPath (Join-Path $workspace 'deployment\mage_vl4b\M175_M120_LMHEAD_OPTIONAL_LAYER_FIX_RESULT.json') -Raw | ConvertFrom-Json
if ($deltaBuild.status -ne 'PASS' -or $fixBuild.status -ne 'PASS' -or
    $deltaBuild.delta_manifest_sha256 -ne '48400534cc6ffd1026568a299ad09e4a631246c990dc7feb6f4b9b2c78112e04' -or
    $fixBuild.package_manifest_sha256 -ne '406dcca340e4604baeb761445795391c43ec26bd99fa06ffae893d597b17414f') {
    throw 'M176_OFFLINE_IDENTITY_FAIL'
}
$delta = (Resolve-Path -LiteralPath (Join-Path $workspace $deltaBuild.directory)).Path
$manifestPath = Join-Path $delta 'DELTA_MANIFEST.json'
$manifest = Get-Content -LiteralPath $manifestPath -Raw | ConvertFrom-Json
$manifestHash = (Get-FileHash -Algorithm SHA256 -LiteralPath $manifestPath).Hash.ToLowerInvariant()
if ($manifestHash -ne $deltaBuild.delta_manifest_sha256 -or $manifest.file_count -ne 5) { throw 'M176_DELTA_MANIFEST_FAIL' }
foreach ($entry in $manifest.files) {
    $path = (Resolve-Path -LiteralPath (Join-Path $delta $entry.path)).Path
    if ((Get-Item -LiteralPath $path).Length -ne [int64]$entry.bytes -or
        (Get-FileHash -Algorithm SHA256 -LiteralPath $path).Hash.ToLowerInvariant() -ne $entry.sha256) {
        throw "M176_LOCAL_MEMBER_FAIL path=$($entry.path)"
    }
}

$root = '/home/ubuntu/tellme_m120_m89x2_20260901'
$remoteRoot = "$root/m176_delta_01"
$receiverRelative = 'scripts\m176_uart_delta_receiver.py'
$receiverPath = (Resolve-Path -LiteralPath (Join-Path $workspace $receiverRelative)).Path
$receiverHash = (Get-FileHash -Algorithm SHA256 -LiteralPath $receiverPath).Hash.ToLowerInvariant()
$receiverRemote = "$root/bootstrap/m176_uart_delta_receiver.py"

# Terminal-scoped authorization must be verified before any transfer.
& (Join-Path $PSScriptRoot 'm75c_uart_command.ps1') `
    -Command 'sudo -n true' -Port $Port -ExpectedFtdiSerial $ExpectedFtdiSerial `
    -LogPath "tmp\m176_fixed_text\sudo_preflight_${Attempt}_uart.log" -TimeoutSeconds 30
& (Join-Path $PSScriptRoot 'm75c_uart_put_file_base64.ps1') `
    -LocalPath ((Resolve-Path -LiteralPath $manifestPath).Path.Substring($workspace.Length + 1)) `
    -RemotePath "$remoteRoot/DELTA_MANIFEST.json" -Port $Port -ExpectedFtdiSerial $ExpectedFtdiSerial `
    -LogPath "tmp\m176_fixed_text\manifest_${Attempt}_uart.log" -TimeoutSeconds 120
& (Join-Path $PSScriptRoot 'm75c_uart_put_file_base64.ps1') `
    -LocalPath $receiverRelative -RemotePath $receiverRemote -Port $Port `
    -ExpectedFtdiSerial $ExpectedFtdiSerial `
    -LogPath "tmp\m176_fixed_text\receiver_${Attempt}_uart.log" -TimeoutSeconds 120

$device = Get-CimInstance Win32_PnPEntity | Where-Object { $_.Name -match "\($([regex]::Escape($Port))\)$" }
if (-not $device -or $device.PNPDeviceID -notmatch [regex]::Escape($ExpectedFtdiSerial)) { throw 'M176_COM3_IDENTITY_FAIL' }
$serial = [IO.Ports.SerialPort]::new($Port,115200,[IO.Ports.Parity]::None,8,[IO.Ports.StopBits]::One)
$serial.Handshake = [IO.Ports.Handshake]::None
$serial.Encoding = [Text.Encoding]::UTF8
$serial.NewLine = "`n"
$serial.ReadTimeout = 250
$serial.WriteTimeout = 5000
$captured = [Text.StringBuilder]::new()
$streamLog = Join-Path $workspace "tmp\m176_fixed_text\stream_${Attempt}_uart.log"
if (Test-Path -LiteralPath $streamLog) { throw "M176 stream log exists: $streamLog" }
[IO.File]::WriteAllText($streamLog,'',[Text.Encoding]::UTF8)
function Read-Until([string]$Pattern,[int]$Seconds) {
    if ($captured.ToString() -match $Pattern) { return }
    $deadline = [DateTime]::UtcNow.AddSeconds($Seconds)
    while ([DateTime]::UtcNow -lt $deadline) {
        $chunk = $serial.ReadExisting()
        if ($chunk.Length -gt 0) {
            [void]$captured.Append($chunk)
            [IO.File]::AppendAllText($streamLog,$chunk)
            Write-Host -NoNewline $chunk
            if ($captured.ToString() -match $Pattern) { return }
        }
        Start-Sleep -Milliseconds 40
    }
    throw "M176_UART_TIMEOUT pattern=$Pattern"
}
try {
    $serial.Open()
    foreach ($entry in $manifest.files) {
        $localPath = (Resolve-Path -LiteralPath (Join-Path $delta $entry.path)).Path
        $encoded = [Convert]::ToBase64String([IO.File]::ReadAllBytes($localPath))
        $remotePath = "$remoteRoot/$($entry.path)"
        $serial.Write([char]3)
        $serial.Write("`n")
        Start-Sleep -Milliseconds 250
        [void]$captured.Clear()
        $command = "python3 $receiverRemote $remotePath $($entry.bytes) $($entry.sha256) $manifestHash $receiverHash; rc=`$?; echo __M176_STREAM_RC_`${rc}__"
        $serial.WriteLine($command)
        Read-Until 'M176_UART_FILE_RECEIVER_READY|M176_UART_FILE_ALREADY_VERIFIED' 45
        if ($captured.ToString() -notmatch 'M176_UART_FILE_ALREADY_VERIFIED') {
            $lineCount = [Math]::Ceiling($encoded.Length / 512.0)
            for ($offset=0; $offset -lt $encoded.Length; $offset+=512) {
                $length = [Math]::Min(512,$encoded.Length-$offset)
                $serial.WriteLine($encoded.Substring($offset,$length))
                if ((($offset/512) % 32) -eq 31) { Start-Sleep -Milliseconds 20 }
                if ((($offset/512) % 256) -eq 255) { Write-Host "M176_UART_PROGRESS path=$($entry.path) lines=$([int]($offset/512)+1)/$lineCount" }
            }
            $serial.WriteLine('__M176_UART_FILE_EOF__')
        }
        Read-Until '__M176_STREAM_RC_(\d+)__' 180
        $match = [regex]::Match($captured.ToString(),'__M176_STREAM_RC_(\d+)__')
        if (-not $match.Success -or [int]$match.Groups[1].Value -ne 0 -or $captured.ToString() -notmatch 'M176_UART_FILE_RECEIVE_PASS') {
            throw "M176_UART_STREAM_FAIL path=$($entry.path)"
        }
    }
} finally {
    if ($serial.IsOpen) { $serial.Close() }
    $serial.Dispose()
}

$runLog = "tmp\m176_fixed_text\stage_${Attempt}_uart.log"
$formal = "deployment\mage_vl4b\M176_M120_LMHEAD_OPTIONAL_LAYER_BOARD_STAGE_RESULT_${Attempt}.json"
foreach ($relative in @($runLog,$formal)) {
    if (Test-Path -LiteralPath (Join-Path $workspace $relative)) { throw "M176 output exists: $relative" }
}
$command = "sudo -n python3 $remoteRoot/m176_apply_lmhead_optional_layer_delta.py --delta-root $remoteRoot --expected-delta-manifest-sha256 $manifestHash --source $root/m165_m120_layer0_board_candidate --output $root/m175_m120_fixed_text_candidate --result $root/results/M176_M120_LMHEAD_OPTIONAL_LAYER_BOARD_STAGE_RESULT_${Attempt}.json"
$commandError = $null
try {
    & (Join-Path $PSScriptRoot 'm75c_uart_command.ps1') `
        -Command $command -Port $Port -ExpectedFtdiSerial $ExpectedFtdiSerial `
        -LogPath $runLog -TimeoutSeconds $TimeoutSeconds
} catch {
    $commandError = $_
}
& $python (Join-Path $PSScriptRoot 'm176_collect_stage_uart.py') `
    --log (Join-Path $workspace $runLog) --result (Join-Path $workspace $formal)
$collector = $LASTEXITCODE
if ($collector -ne 0) { throw "M176 board stage FAIL; formal evidence retained at $formal" }
if ($null -ne $commandError) { throw $commandError }
Write-Output 'M176_LMHEAD_OPTIONAL_LAYER_BOARD_STAGE_UART_PASS'
exit 0
