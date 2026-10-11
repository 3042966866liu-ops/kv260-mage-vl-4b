[CmdletBinding()]
param(
    [string]$Port = 'COM3',
    [string]$ExpectedFtdiSerial = 'XFL1PL5N11BJB',
    [string]$DeltaPath = 'tmp\m89x1_hs64\m89x1_hs64_c464_delta.tar.gz',
    [string]$Baseline = '/home/ubuntu/tellme_m89x1_waitfix_20260831/m89x_board_candidate',
    [string]$Output = '/home/ubuntu/tellme_m89x1_hs64_20260831/m89x_board_candidate',
    [string]$BaselineManifestSha256 = 'c4645fdf2ff1b299d3a7fb302fed72a8d50a95b658ad76e464c67a72a1a6cf50',
    [string]$CandidateManifestSha256 = '8b45d93ac104006eff98acf9ce4479922c49dc0be7e225b201cfa0671a472679',
    [string]$DeltaSha256 = '',
    [int]$TimeoutSeconds = 120
)

$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest
$workspace = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
$delta = (Resolve-Path -LiteralPath (Join-Path $workspace $DeltaPath)).Path
if (-not $DeltaSha256) { $DeltaSha256 = (Get-FileHash -LiteralPath $delta -Algorithm SHA256).Hash.ToLowerInvariant() }
if ((Get-FileHash -LiteralPath $delta -Algorithm SHA256).Hash.ToLowerInvariant() -ne $DeltaSha256) {
    throw 'M89X1_HS64_LOCAL_DELTA_HASH_FAIL'
}

$stagerLocal = 'scripts\m89x1_hostscale_uart_stager.py'
$stagerRemote = '/home/ubuntu/tellme_m89x1_hs64_20260831/bootstrap/m89x1_hostscale_uart_stager.py'
$stagerResolved = (Resolve-Path -LiteralPath (Join-Path $workspace $stagerLocal)).Path
$stagerSha256 = (Get-FileHash -LiteralPath $stagerResolved -Algorithm SHA256).Hash.ToLowerInvariant()
& (Join-Path $PSScriptRoot 'm75c_uart_put_file_base64.ps1') `
    -LocalPath $stagerLocal -RemotePath $stagerRemote -Port $Port `
    -ExpectedFtdiSerial $ExpectedFtdiSerial `
    -LogPath 'tmp\m89x1_hs64\bootstrap_uart.log' -TimeoutSeconds 60

$bytes = [IO.File]::ReadAllBytes($delta)
$encoded = [Convert]::ToBase64String($bytes)
$device = Get-CimInstance Win32_PnPEntity | Where-Object { $_.Name -match "\($([regex]::Escape($Port))\)$" }
if (-not $device -or $device.PNPDeviceID -notmatch [regex]::Escape($ExpectedFtdiSerial)) {
    throw 'M89X1_HS64_COM3_IDENTITY_FAIL'
}
$serial = [IO.Ports.SerialPort]::new($Port,115200,[IO.Ports.Parity]::None,8,[IO.Ports.StopBits]::One)
$serial.Handshake=[IO.Ports.Handshake]::None
$serial.Encoding=[Text.Encoding]::UTF8
$serial.NewLine="`n"
$serial.ReadTimeout=250
$serial.WriteTimeout=5000
$captured=[Text.StringBuilder]::new()
$log=Join-Path $workspace 'tmp\m89x1_hs64\stage_uart.log'
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
        Start-Sleep -Milliseconds 50
    }
    throw "M89X1_HS64_UART_TIMEOUT pattern=$Pattern"
}
try {
    $serial.Open()
    $command="python3 $stagerRemote --self-sha256 $stagerSha256 --baseline $Baseline --output $Output --baseline-manifest-sha256 $BaselineManifestSha256 --candidate-manifest-sha256 $CandidateManifestSha256 --delta-sha256 $DeltaSha256; rc=`$?; echo __M89X1_HS64_STAGE_RC_`${rc}__"
    $serial.WriteLine($command)
    Read-Until 'M89X1_HS64_UART_STAGER_READY' 30
    for($offset=0;$offset -lt $encoded.Length;$offset+=512) {
        $length=[Math]::Min(512,$encoded.Length-$offset)
        $serial.WriteLine($encoded.Substring($offset,$length))
        if((($offset/512) % 32) -eq 31) { Start-Sleep -Milliseconds 20 }
    }
    $serial.WriteLine('__M89X1_HS64_DELTA_EOF__')
    Read-Until '__M89X1_HS64_STAGE_RC_(\d+)__' $TimeoutSeconds
    $match=[regex]::Match($captured.ToString(),'__M89X1_HS64_STAGE_RC_(\d+)__')
    if(-not $match.Success -or [int]$match.Groups[1].Value -ne 0) { throw 'M89X1_HS64_UART_STAGE_FAIL' }
    if($captured.ToString() -notmatch 'M89X1_HS64_UART_STAGE_PASS') { throw 'M89X1_HS64_STAGE_MARKER_MISSING' }
    Write-Output 'M89X1_HS64_UART_STAGE_CLIENT_PASS'
} finally {
    if($serial.IsOpen){$serial.Close()}
    $serial.Dispose()
}
