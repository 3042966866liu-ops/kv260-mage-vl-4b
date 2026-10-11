[CmdletBinding()]
param(
    [string]$Port = 'COM3',
    [string]$ExpectedFtdiSerial = 'XFL1PL5N11BJB',
    [string]$Attempt = '02',
    [int]$TimeoutSeconds = 600
)

$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest
$workspace = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
$python = 'C:\Users\30429\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe'
$build = Get-Content -LiteralPath (Join-Path $workspace 'deployment\mage_vl4b\M166_M120_CORRECTED_LAYER0_DELTA_RESULT.json') -Raw | ConvertFrom-Json
if ($build.status -ne 'PASS') { throw 'M166_DELTA_NOT_PASS' }
$delta = (Resolve-Path -LiteralPath (Join-Path $workspace $build.directory)).Path
$deltaManifestPath = Join-Path $delta 'DELTA_MANIFEST.json'
$deltaManifest = Get-Content -LiteralPath $deltaManifestPath -Raw | ConvertFrom-Json
$deltaManifestHash = (Get-FileHash -Algorithm SHA256 -LiteralPath $deltaManifestPath).Hash.ToLowerInvariant()
if ($deltaManifestHash -ne $build.delta_manifest_sha256 -or $deltaManifest.file_count -ne 5) { throw 'M166_DELTA_MANIFEST_FAIL' }

$streamMemberRelatives = @(
    'auxiliary/M77_TEXT_AUX_MANIFEST.json',
    'auxiliary/m77_text_aux_fp16.npz'
)
$streamMembers = @()
foreach ($memberRelative in $streamMemberRelatives) {
    $memberEntry = @($deltaManifest.files | Where-Object { $_.path -eq $memberRelative })
    if ($memberEntry.Count -ne 1) { throw "M166_STREAM_MEMBER_MANIFEST_FAIL path=$memberRelative" }
    $member = $memberEntry[0]
    $memberPath = (Resolve-Path -LiteralPath (Join-Path $delta $memberRelative)).Path
    if ((Get-Item -LiteralPath $memberPath).Length -ne [int64]$member.bytes -or
        (Get-FileHash -Algorithm SHA256 -LiteralPath $memberPath).Hash.ToLowerInvariant() -ne $member.sha256) {
        throw "M166_STREAM_MEMBER_LOCAL_HASH_FAIL path=$memberRelative"
    }
    $streamMembers += [pscustomobject]@{
        RelativePath = $memberRelative
        Entry = $member
        LocalPath = $memberPath
    }
}

$receiverRelative = 'scripts\m166_uart_file_receiver.py'
$receiverPath = (Resolve-Path -LiteralPath (Join-Path $workspace $receiverRelative)).Path
$receiverHash = (Get-FileHash -Algorithm SHA256 -LiteralPath $receiverPath).Hash.ToLowerInvariant()
$remoteRoot = '/home/ubuntu/tellme_m120_m89x2_20260901/m166_delta_01'
$receiverRemote = '/home/ubuntu/tellme_m120_m89x2_20260901/bootstrap/m166_uart_file_receiver.py'

# Fail before any transfer if the terminal-scoped sudo timestamp has expired.
& (Join-Path $PSScriptRoot 'm75c_uart_command.ps1') `
    -Command 'sudo -n true' -Port $Port -ExpectedFtdiSerial $ExpectedFtdiSerial `
    -LogPath "tmp\m166_layer0\sudo_preflight_${Attempt}_uart.log" -TimeoutSeconds 30

& (Join-Path $PSScriptRoot 'm75c_uart_put_file_base64.ps1') `
    -LocalPath $receiverRelative -RemotePath $receiverRemote -Port $Port `
    -ExpectedFtdiSerial $ExpectedFtdiSerial `
    -LogPath "tmp\m166_layer0\receiver_${Attempt}_uart.log" -TimeoutSeconds 120

$device = Get-CimInstance Win32_PnPEntity | Where-Object { $_.Name -match "\($([regex]::Escape($Port))\)$" }
if (-not $device -or $device.PNPDeviceID -notmatch [regex]::Escape($ExpectedFtdiSerial)) { throw 'M166_COM3_IDENTITY_FAIL' }
$serial = [IO.Ports.SerialPort]::new($Port,115200,[IO.Ports.Parity]::None,8,[IO.Ports.StopBits]::One)
$serial.Handshake=[IO.Ports.Handshake]::None
$serial.Encoding=[Text.Encoding]::UTF8
$serial.NewLine="`n"
$serial.ReadTimeout=250
$serial.WriteTimeout=5000
$captured=[Text.StringBuilder]::new()
$streamLog=Join-Path $workspace "tmp\m166_layer0\stream_${Attempt}_uart.log"
if (Test-Path -LiteralPath $streamLog) { throw "M166 stream log exists: $streamLog" }
[IO.File]::WriteAllText($streamLog,'',[Text.Encoding]::UTF8)
function Read-Until([string]$Pattern,[int]$Seconds) {
    if($captured.ToString() -match $Pattern) { return }
    $deadline=[DateTime]::UtcNow.AddSeconds($Seconds)
    while([DateTime]::UtcNow -lt $deadline) {
        $chunk=$serial.ReadExisting()
        if($chunk.Length -gt 0) {
            [void]$captured.Append($chunk)
            [IO.File]::AppendAllText($streamLog,$chunk)
            Write-Host -NoNewline $chunk
            if($captured.ToString() -match $Pattern) { return }
        }
        Start-Sleep -Milliseconds 40
    }
    throw "M166_UART_TIMEOUT pattern=$Pattern"
}
try {
    $serial.Open()
    foreach ($streamMember in $streamMembers) {
        $member = $streamMember.Entry
        $memberRelative = $streamMember.RelativePath
        $remoteMember = "$remoteRoot/$memberRelative"
        $encoded = [Convert]::ToBase64String([IO.File]::ReadAllBytes($streamMember.LocalPath))
        # Clear any abandoned canonical input from a rejected one-line attempt.
        $serial.Write([char]3)
        $serial.Write("`n")
        Start-Sleep -Milliseconds 300
        [void]$captured.Clear()
        $command="python3 $receiverRemote $remoteMember $($member.bytes) $($member.sha256) $receiverHash; rc=`$?; echo __M166_STREAM_RC_`${rc}__"
        $serial.WriteLine($command)
        Read-Until 'M166_UART_FILE_RECEIVER_READY|M166_UART_FILE_ALREADY_VERIFIED' 45
        if($captured.ToString() -notmatch 'M166_UART_FILE_ALREADY_VERIFIED') {
            $lineCount=[Math]::Ceiling($encoded.Length / 512.0)
            for($offset=0;$offset -lt $encoded.Length;$offset+=512) {
                $length=[Math]::Min(512,$encoded.Length-$offset)
                $serial.WriteLine($encoded.Substring($offset,$length))
                if((($offset/512) % 32) -eq 31) { Start-Sleep -Milliseconds 20 }
                if((($offset/512) % 256) -eq 255) { Write-Host "M166_UART_PROGRESS path=$memberRelative lines=$([int]($offset/512)+1)/$lineCount" }
            }
            $serial.WriteLine('__M166_UART_FILE_EOF__')
        }
        Read-Until '__M166_STREAM_RC_(\d+)__' 300
        $match=[regex]::Match($captured.ToString(),'__M166_STREAM_RC_(\d+)__')
        if(-not $match.Success -or [int]$match.Groups[1].Value -ne 0 -or $captured.ToString() -notmatch 'M166_UART_FILE_RECEIVE_PASS') {
            throw "M166_UART_STREAM_FAIL path=$memberRelative"
        }
    }
} finally {
    if($serial.IsOpen){$serial.Close()}
    $serial.Dispose()
}

& (Join-Path $PSScriptRoot 'm75c_uart_put_file_base64.ps1') `
    -LocalPath ((Resolve-Path -LiteralPath $deltaManifestPath).Path.Substring($workspace.Length + 1)) `
    -RemotePath "$remoteRoot/DELTA_MANIFEST.json" -Port $Port -ExpectedFtdiSerial $ExpectedFtdiSerial `
    -LogPath "tmp\m166_layer0\manifest_${Attempt}_uart.log" -TimeoutSeconds 120

$runLog = "tmp\m166_layer0\stage_${Attempt}_uart.log"
$formal = "deployment\mage_vl4b\M166_M120_CORRECTED_LAYER0_BOARD_STAGE_RESULT_${Attempt}.json"
if (Test-Path -LiteralPath (Join-Path $workspace $runLog)) { throw "M166 run log exists: $runLog" }
if (Test-Path -LiteralPath (Join-Path $workspace $formal)) { throw "M166 result exists: $formal" }
$command = "sudo -n python3 $remoteRoot/m166_apply_corrected_layer0_delta.py --delta-root $remoteRoot --expected-delta-manifest-sha256 $deltaManifestHash --source /home/ubuntu/tellme_m120_m89x2_20260901/m120_text4b_layer0_board_candidate --output /home/ubuntu/tellme_m120_m89x2_20260901/m165_m120_layer0_board_candidate --result /home/ubuntu/tellme_m120_m89x2_20260901/results/M166_M120_CORRECTED_LAYER0_BOARD_STAGE_RESULT_${Attempt}.json"
$commandError = $null
try {
    & (Join-Path $PSScriptRoot 'm75c_uart_command.ps1') `
        -Command $command -Port $Port -ExpectedFtdiSerial $ExpectedFtdiSerial -LogPath $runLog -TimeoutSeconds $TimeoutSeconds
} catch {
    $commandError = $_
}
& $python (Join-Path $PSScriptRoot 'm166_collect_corrected_stage_uart.py') `
    --log (Join-Path $workspace $runLog) --result (Join-Path $workspace $formal)
$collectorExit = $LASTEXITCODE
if ($collectorExit -ne 0) { throw "M166 corrected stage FAIL; formal evidence retained at $formal" }
if ($null -ne $commandError) { throw $commandError }
Write-Output 'M166_CORRECTED_LAYER0_BOARD_STAGE_STREAM_UART_PASS'
