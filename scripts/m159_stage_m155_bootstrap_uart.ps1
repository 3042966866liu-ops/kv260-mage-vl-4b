[CmdletBinding()]
param(
    [string]$Port = 'COM3',
    [string]$ExpectedFtdiSerial = 'XFL1PL5N11BJB',
    [string]$Attempt = '01',
    [int]$TimeoutSeconds = 300
)

$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest
$workspace = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
$m140Path = Join-Path $workspace 'deployment\mage_vl4b\M140_M120_SINGLE_CHAIN_BOARD_RESULT_01.json'
$m140Hash = (Get-FileHash -LiteralPath $m140Path -Algorithm SHA256).Hash.ToLowerInvariant()
if ($m140Hash -ne '60bc5dad7f3609c32b4698ebbb372eba9a3ab9e74b273969dd322299b4431cbb') {
    throw 'M159_M140_IDENTITY_FAIL'
}
$m140 = Get-Content -LiteralPath $m140Path -Raw | ConvertFrom-Json
if ($m140.gate -ne 'M140-M120-COM3-single-chain' -or $m140.status -ne 'PASS' -or $m140.candidate_build_id.ToLowerInvariant() -ne '0x4d395832') {
    throw 'M159_LOCKED_UNTIL_EXACT_M140_PASS'
}

$archiveResultPath = Join-Path $workspace 'deployment\mage_vl4b\M159_M155_BOOTSTRAP_UART_ARCHIVE_RESULT.json'
$archiveResult = Get-Content -LiteralPath $archiveResultPath -Raw | ConvertFrom-Json
if ($archiveResult.status -ne 'PASS') { throw 'M159_ARCHIVE_NOT_PASS' }
$archive = (Resolve-Path -LiteralPath (Join-Path $workspace $archiveResult.archive)).Path
$archiveHash = (Get-FileHash -LiteralPath $archive -Algorithm SHA256).Hash.ToLowerInvariant()
if ($archiveHash -ne $archiveResult.archive_sha256) { throw 'M159_ARCHIVE_HASH_FAIL' }
$manifestHash = [string]$archiveResult.package_manifest_sha256

$stagerRelative = 'scripts\m159_uart_m155_bootstrap_stager.py'
$stager = (Resolve-Path -LiteralPath (Join-Path $workspace $stagerRelative)).Path
$stagerHash = (Get-FileHash -LiteralPath $stager -Algorithm SHA256).Hash.ToLowerInvariant()
$stagerRemote = '/home/ubuntu/tellme_m120_m89x2_20260901/bootstrap/m159_uart_m155_bootstrap_stager.py'
$bootstrapLog = "tmp\m159_uart\bootstrap_${Attempt}_uart.log"
$stageLog = Join-Path $workspace "tmp\m159_uart\stage_${Attempt}_uart.log"
if (Test-Path -LiteralPath (Join-Path $workspace $bootstrapLog)) { throw "M159 bootstrap log exists: $bootstrapLog" }
if (Test-Path -LiteralPath $stageLog) { throw "M159 stage log exists: $stageLog" }

& (Join-Path $PSScriptRoot 'm75c_uart_put_file_base64.ps1') `
    -LocalPath $stagerRelative -RemotePath $stagerRemote -Port $Port `
    -ExpectedFtdiSerial $ExpectedFtdiSerial -LogPath $bootstrapLog -TimeoutSeconds 120

$device = Get-CimInstance Win32_PnPEntity | Where-Object { $_.Name -match "\($([regex]::Escape($Port))\)$" }
if (-not $device -or $device.PNPDeviceID -notmatch [regex]::Escape($ExpectedFtdiSerial)) {
    throw 'M159_COM3_IDENTITY_FAIL'
}
$encoded = [Convert]::ToBase64String([IO.File]::ReadAllBytes($archive))
$serial = [IO.Ports.SerialPort]::new($Port,115200,[IO.Ports.Parity]::None,8,[IO.Ports.StopBits]::One)
$serial.Handshake = [IO.Ports.Handshake]::None
$serial.Encoding = [Text.Encoding]::UTF8
$serial.NewLine = "`n"
$serial.ReadTimeout = 250
$serial.WriteTimeout = 5000
$captured = [Text.StringBuilder]::new()
New-Item -ItemType Directory -Force -Path (Split-Path $stageLog) | Out-Null
[IO.File]::WriteAllText($stageLog, '', [Text.Encoding]::UTF8)

function Read-Until([string]$Pattern, [int]$Seconds) {
    $deadline = [DateTime]::UtcNow.AddSeconds($Seconds)
    while ([DateTime]::UtcNow -lt $deadline) {
        $chunk = $serial.ReadExisting()
        if ($chunk.Length -gt 0) {
            [void]$captured.Append($chunk)
            [IO.File]::AppendAllText($stageLog, $chunk)
            Write-Host -NoNewline $chunk
            if ($captured.ToString() -match $Pattern) { return }
        }
        Start-Sleep -Milliseconds 40
    }
    throw "M159_UART_TIMEOUT pattern=$Pattern"
}

try {
    $serial.Open()
    $output = '/home/ubuntu/tellme_m120_m89x2_20260901/m155_bootstrap'
    $command = "python3 $stagerRemote --self-sha256 $stagerHash --output $output --archive-sha256 $archiveHash --package-manifest-sha256 $manifestHash; rc=`$?; echo __M159_STAGE_RC_`${rc}__"
    $serial.WriteLine($command)
    Read-Until 'M159_M155_BOOTSTRAP_UART_STAGER_READY' 45
    for ($offset = 0; $offset -lt $encoded.Length; $offset += 512) {
        $length = [Math]::Min(512, $encoded.Length - $offset)
        $serial.WriteLine($encoded.Substring($offset, $length))
        if ((($offset / 512) % 32) -eq 31) { Start-Sleep -Milliseconds 20 }
    }
    $serial.WriteLine('__M159_M155_BOOTSTRAP_EOF__')
    Read-Until '__M159_STAGE_RC_(\d+)__' $TimeoutSeconds
    $match = [regex]::Match($captured.ToString(), '__M159_STAGE_RC_(\d+)__')
    if (-not $match.Success -or [int]$match.Groups[1].Value -ne 0) { throw 'M159_UART_STAGE_FAIL' }
    if ($captured.ToString() -notmatch 'M159_M155_BOOTSTRAP_UART_STAGE_PASS') { throw 'M159_UART_STAGE_MARKER_MISSING' }
    Write-Output 'M159_M155_BOOTSTRAP_UART_STAGE_CLIENT_PASS'
} finally {
    if ($serial.IsOpen) { $serial.Close() }
    $serial.Dispose()
}
