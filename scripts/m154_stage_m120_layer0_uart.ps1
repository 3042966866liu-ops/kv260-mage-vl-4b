[CmdletBinding()]
param(
    [string]$Port = 'COM3',
    [string]$ExpectedFtdiSerial = 'XFL1PL5N11BJB',
    [string]$Attempt = '01',
    [int]$TimeoutSeconds = 1200
)

$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest
$workspace = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
$python = 'C:\Users\30429\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe'
$m140Path = Join-Path $workspace "deployment\mage_vl4b\M140_M120_SINGLE_CHAIN_BOARD_RESULT_${Attempt}.json"
if (-not (Test-Path -LiteralPath $m140Path)) { throw 'M154_LOCKED_UNTIL_M140_SINGLE_CHAIN_BOARD_PASS' }
$m140 = Get-Content -LiteralPath $m140Path -Raw | ConvertFrom-Json
if ($m140.status -ne 'PASS' -or $m140.gate -ne 'M140-M120-COM3-single-chain' -or $m140.candidate_build_id.ToLowerInvariant() -ne '0x4d395832') {
    throw 'M154_LOCKED_UNTIL_M140_SINGLE_CHAIN_BOARD_PASS'
}

$archiveResultPath = Join-Path $workspace 'deployment\mage_vl4b\M154_M120_LAYER0_UART_ARCHIVE_RESULT.json'
$archiveResult = Get-Content -LiteralPath $archiveResultPath -Raw | ConvertFrom-Json
if ($archiveResult.status -ne 'PASS') { throw 'M154_LAYER0_ARCHIVE_NOT_PASS' }
$archive = (Resolve-Path -LiteralPath (Join-Path $workspace $archiveResult.archive)).Path
$archiveHash = (Get-FileHash -LiteralPath $archive -Algorithm SHA256).Hash.ToLowerInvariant()
if ($archiveHash -ne $archiveResult.archive_sha256) { throw 'M154_LAYER0_ARCHIVE_HASH_FAIL' }
$manifestHash = '732b881d3507eaa12b8488e9224835ac115b686a003c748c9fa05a9793041d13'

$stagerRelative = 'scripts\m154_uart_layer0_package_stager.py'
$stagerRemote = '/home/ubuntu/tellme_m120_m89x2_20260901/bootstrap/m154_uart_layer0_package_stager.py'
$stager = (Resolve-Path -LiteralPath (Join-Path $workspace $stagerRelative)).Path
$stagerHash = (Get-FileHash -LiteralPath $stager -Algorithm SHA256).Hash.ToLowerInvariant()
& (Join-Path $PSScriptRoot 'm75c_uart_put_file_base64.ps1') `
    -LocalPath $stagerRelative -RemotePath $stagerRemote -Port $Port `
    -ExpectedFtdiSerial $ExpectedFtdiSerial `
    -LogPath "tmp\m154_uart\bootstrap_${Attempt}_uart.log" -TimeoutSeconds 120

$device = Get-CimInstance Win32_PnPEntity | Where-Object { $_.Name -match "\($([regex]::Escape($Port))\)$" }
if (-not $device -or $device.PNPDeviceID -notmatch [regex]::Escape($ExpectedFtdiSerial)) {
    throw 'M154_COM3_IDENTITY_FAIL'
}
$encoded = [Convert]::ToBase64String([IO.File]::ReadAllBytes($archive))
$serial = [IO.Ports.SerialPort]::new($Port,115200,[IO.Ports.Parity]::None,8,[IO.Ports.StopBits]::One)
$serial.Handshake=[IO.Ports.Handshake]::None
$serial.Encoding=[Text.Encoding]::UTF8
$serial.NewLine="`n"
$serial.ReadTimeout=250
$serial.WriteTimeout=5000
$captured=[Text.StringBuilder]::new()
$log=Join-Path $workspace "tmp\m154_uart\stage_${Attempt}_uart.log"
if (Test-Path -LiteralPath $log) { throw "M154 log already exists: $log" }
New-Item -ItemType Directory -Force -Path (Split-Path $log) | Out-Null
[IO.File]::WriteAllText($log,'',[Text.Encoding]::UTF8)
function Read-Until([string]$Pattern,[int]$Seconds) {
    $deadline=[DateTime]::UtcNow.AddSeconds($Seconds)
    while([DateTime]::UtcNow -lt $deadline) {
        $chunk=$serial.ReadExisting()
        if($chunk.Length -gt 0) {
            [void]$captured.Append($chunk)
            [IO.File]::AppendAllText($log,$chunk)
            Write-Host -NoNewline $chunk
            if($captured.ToString() -match $Pattern) { return }
        }
        Start-Sleep -Milliseconds 40
    }
    throw "M154_UART_TIMEOUT pattern=$Pattern"
}
try {
    $serial.Open()
    $output='/home/ubuntu/tellme_m120_m89x2_20260901/m120_text4b_layer0_board_candidate'
    $command="python3 $stagerRemote --self-sha256 $stagerHash --output $output --archive-sha256 $archiveHash --package-manifest-sha256 $manifestHash; rc=`$?; echo __M154_STAGE_RC_`${rc}__"
    $serial.WriteLine($command)
    Read-Until 'M154_M120_LAYER0_UART_STAGER_READY' 45
    $lineCount=[Math]::Ceiling($encoded.Length / 512.0)
    for($offset=0;$offset -lt $encoded.Length;$offset+=512) {
        $length=[Math]::Min(512,$encoded.Length-$offset)
        $serial.WriteLine($encoded.Substring($offset,$length))
        if((($offset/512) % 32) -eq 31) { Start-Sleep -Milliseconds 20 }
        if((($offset/512) % 2048) -eq 2047) { Write-Host "M154_UART_PROGRESS lines=$([int]($offset/512)+1)/$lineCount" }
    }
    $serial.WriteLine('__M154_M120_LAYER0_PACKAGE_EOF__')
    Read-Until '__M154_STAGE_RC_(\d+)__' $TimeoutSeconds
    $match=[regex]::Match($captured.ToString(),'__M154_STAGE_RC_(\d+)__')
    if(-not $match.Success -or [int]$match.Groups[1].Value -ne 0) { throw 'M154_UART_STAGE_FAIL' }
    if($captured.ToString() -notmatch 'M154_M120_LAYER0_UART_STAGE_PASS') { throw 'M154_UART_STAGE_MARKER_MISSING' }
    Write-Output 'M154_M120_LAYER0_UART_STAGE_CLIENT_PASS'
} finally {
    if($serial.IsOpen){$serial.Close()}
    $serial.Dispose()
}
