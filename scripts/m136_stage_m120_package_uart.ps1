[CmdletBinding()]
param(
    [string]$Port = 'COM3',
    [string]$ExpectedFtdiSerial = 'XFL1PL5N11BJB',
    [string]$Output = '/home/ubuntu/tellme_m120_m89x2_20260901/m120_text4b_board_candidate',
    [int]$TimeoutSeconds = 900
)

$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest
$workspace = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
$archiveResult = Get-Content -LiteralPath (Join-Path $workspace 'deployment\mage_vl4b\M136_M120_UART_ARCHIVE_RESULT.json') -Raw | ConvertFrom-Json
if ($archiveResult.status -ne 'PASS') { throw 'M136_UART_ARCHIVE_NOT_PASS' }
$archive = (Resolve-Path -LiteralPath (Join-Path $workspace $archiveResult.archive)).Path
$archiveHash = (Get-FileHash -LiteralPath $archive -Algorithm SHA256).Hash.ToLowerInvariant()
if ($archiveHash -ne $archiveResult.archive_sha256) { throw 'M136_UART_ARCHIVE_HASH_FAIL' }
$manifestHash = '7600ba1af87680fe1294ae6dc88f8e0968f23b2e38ca48dbfd316e351ea76e3e'

$stagerLocal = 'scripts\m136_uart_package_stager.py'
$stagerRemote = '/home/ubuntu/tellme_m120_m89x2_20260901/bootstrap/m136_uart_package_stager.py'
$stager = (Resolve-Path -LiteralPath (Join-Path $workspace $stagerLocal)).Path
$stagerHash = (Get-FileHash -LiteralPath $stager -Algorithm SHA256).Hash.ToLowerInvariant()
& (Join-Path $PSScriptRoot 'm75c_uart_put_file_base64.ps1') `
    -LocalPath $stagerLocal -RemotePath $stagerRemote -Port $Port `
    -ExpectedFtdiSerial $ExpectedFtdiSerial `
    -LogPath 'tmp\m136_uart\bootstrap_uart.log' -TimeoutSeconds 90

$device = Get-CimInstance Win32_PnPEntity | Where-Object { $_.Name -match "\($([regex]::Escape($Port))\)$" }
if (-not $device -or $device.PNPDeviceID -notmatch [regex]::Escape($ExpectedFtdiSerial)) {
    throw 'M136_COM3_IDENTITY_FAIL'
}
$encoded = [Convert]::ToBase64String([IO.File]::ReadAllBytes($archive))
$serial = [IO.Ports.SerialPort]::new($Port,115200,[IO.Ports.Parity]::None,8,[IO.Ports.StopBits]::One)
$serial.Handshake=[IO.Ports.Handshake]::None
$serial.Encoding=[Text.Encoding]::UTF8
$serial.NewLine="`n"
$serial.ReadTimeout=250
$serial.WriteTimeout=5000
$captured=[Text.StringBuilder]::new()
$log=Join-Path $workspace 'tmp\m136_uart\stage_uart.log'
New-Item -ItemType Directory -Force -Path (Split-Path $log) | Out-Null
Set-Content -LiteralPath $log -Value '' -Encoding utf8
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
    throw "M136_UART_TIMEOUT pattern=$Pattern"
}
try {
    $serial.Open()
    $command="python3 $stagerRemote --self-sha256 $stagerHash --output $Output --archive-sha256 $archiveHash --package-manifest-sha256 $manifestHash; rc=`$?; echo __M136_STAGE_RC_`${rc}__"
    $serial.WriteLine($command)
    Read-Until 'M136_M120_UART_STAGER_READY' 30
    $lineCount=[Math]::Ceiling($encoded.Length / 512.0)
    for($offset=0;$offset -lt $encoded.Length;$offset+=512) {
        $length=[Math]::Min(512,$encoded.Length-$offset)
        $serial.WriteLine($encoded.Substring($offset,$length))
        if((($offset/512) % 32) -eq 31) { Start-Sleep -Milliseconds 20 }
        if((($offset/512) % 2048) -eq 2047) {
            $done=[int]($offset/512)+1
            Write-Host "M136_UART_PROGRESS lines=$done/$lineCount"
        }
    }
    $serial.WriteLine('__M136_M120_PACKAGE_EOF__')
    Read-Until '__M136_STAGE_RC_(\d+)__' $TimeoutSeconds
    $match=[regex]::Match($captured.ToString(),'__M136_STAGE_RC_(\d+)__')
    if(-not $match.Success -or [int]$match.Groups[1].Value -ne 0) { throw 'M136_UART_STAGE_FAIL' }
    if($captured.ToString() -notmatch 'M136_M120_UART_STAGE_PASS') { throw 'M136_UART_STAGE_MARKER_MISSING' }
    Write-Output 'M136_M120_UART_STAGE_CLIENT_PASS'
} finally {
    if($serial.IsOpen){$serial.Close()}
    $serial.Dispose()
}

