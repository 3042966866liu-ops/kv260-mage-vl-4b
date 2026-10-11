[CmdletBinding()]
param([ValidateSet('SelfTest','Pause')][string]$Mode)
$ErrorActionPreference='Stop'
Set-StrictMode -Version Latest
$taskRoot=(Resolve-Path (Join-Path $PSScriptRoot '../..')).Path
if ($Mode -eq 'SelfTest') {
    $taskTokens=$null;$taskErrors=$null
    [void][System.Management.Automation.Language.Parser]::ParseFile($PSCommandPath,[ref]$taskTokens,[ref]$taskErrors)
    if ($taskErrors.Count) { throw 'Pause controller parse failed' }
    Write-Output 'M400_PAUSE_ONLY_PARSE_PASS';exit 0
}
if ($Mode -ne 'Pause') { throw 'Explicit Pause required' }
$taskRawPath=Join-Path $taskRoot 'deployment/mage_vl4b/optimization_v1/runs/M400-tail-layer-board-01/BOARD_RESULT.json'
if ((Get-FileHash -LiteralPath $taskRawPath -Algorithm SHA256).Hash.ToLowerInvariant() -ne 'de7f6e0e144fe03529a414f3983e2e6e515bc8a7d7185400daf5e026bcd549e9') { throw 'Original failure SHA differs' }
$taskRaw=Get-Content -LiteralPath $taskRawPath -Raw -Encoding UTF8|ConvertFrom-Json
if ($taskRaw.status -ne 'FAIL_UNSAFE_RETAINED' -or $taskRaw.logical_calls -ne 0 -or $taskRaw.host_calls -ne 0 -or $taskRaw.fpga_transactions -ne 1) { throw 'Not the expected pre-Linear retained wait' }
$taskOriginal=Get-Content -LiteralPath (Join-Path $taskRoot 'deployment/mage_vl4b/optimization_v1/runs/M400-tail-layer-failure-closure-01/UART.log') -Raw -Encoding UTF8
if (-not $taskOriginal.Contains('M400_RECOVERY_REQUIRED_RETAIN_BUFFERS_DO_NOT_INTERRUPT')) { throw 'Retained loop evidence absent' }
$taskLog=Join-Path $taskRoot 'tmp/m400/owner_pause_01.log'
if (Test-Path -LiteralPath $taskLog) { throw 'Pause already attempted; inspect existing evidence' }
$taskDevice=Get-CimInstance Win32_PnPEntity|Where-Object {$_.Name -match '\(COM3\)$'}
if (-not $taskDevice -or $taskDevice.PNPDeviceID -notmatch 'XFL1PL5N11BJB') { throw 'FTDI identity differs' }
$taskSerial=[IO.Ports.SerialPort]::new('COM3',115200,[IO.Ports.Parity]::None,8,[IO.Ports.StopBits]::One)
$taskSerial.Handshake=[IO.Ports.Handshake]::None
$taskSerial.Encoding=[Text.Encoding]::UTF8
$taskSerial.WriteTimeout=2000
$taskCaptured=[Text.StringBuilder]::new()
[IO.File]::WriteAllText($taskLog,'',[Text.UTF8Encoding]::new($false))
try {
    $taskSerial.Open()
    Start-Sleep -Milliseconds 300
    $taskInitial=$taskSerial.ReadExisting()
    if ($taskInitial.Length) {
        [void]$taskCaptured.Append($taskInitial)
        [IO.File]::AppendAllText($taskLog,$taskInitial,[Text.Encoding]::UTF8)
        if ($taskInitial -match '(?:login:|[Pp]assword:|ubuntu@kria:[^\r\n]*\$)\s*$') { throw 'Owner foreground not confirmed; no control byte sent' }
    }
    # One terminal job-control suspend; never SIGINT/SIGTERM/reset/free.
    $taskSerial.Write([char]26)
    $taskDeadline=[DateTime]::UtcNow.AddSeconds(8)
    while ([DateTime]::UtcNow -lt $taskDeadline) {
        $taskChunk=$taskSerial.ReadExisting()
        if ($taskChunk.Length) {
            [void]$taskCaptured.Append($taskChunk)
            [IO.File]::AppendAllText($taskLog,$taskChunk,[Text.Encoding]::UTF8)
            Write-Host -NoNewline $taskChunk
            $taskText=$taskCaptured.ToString()
            if ($taskText -match '(?m)Stopped[^\r\n]*M400_ENABLE_TAIL_LAYER=1[^\r\n]*run_m400_tail_layer\.sh' -and $taskText -match '(?m)ubuntu@kria:[^\r\n]*\$\s*$') {
                Write-Output 'M400_OWNER_JOB_SUSPENDED_SHELL_CONFIRMED_NO_RELEASE';exit 0
            }
        }
        Start-Sleep -Milliseconds 100
    }
    throw 'Suspended job and shell not both confirmed; no further bytes sent'
} finally {
    if ($taskSerial.IsOpen) {$taskSerial.Close()}
    $taskSerial.Dispose()
}
