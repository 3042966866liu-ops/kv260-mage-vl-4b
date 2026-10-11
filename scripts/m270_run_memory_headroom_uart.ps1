[CmdletBinding()]
param(
    [string]$Port = 'COM3',
    [string]$ExpectedFtdiSerial = 'XFL1PL5N11BJB',
    [string]$Attempt = '01',
    [int]$ReserveMiB = 256
)

$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest
$workspace = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
$python = 'C:\Users\30429\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe'
$probe = Join-Path $workspace 'scripts\m270_board_memory_headroom_probe.py'
$probeHash = (Get-FileHash -Algorithm SHA256 -LiteralPath $probe).Hash.ToLowerInvariant()
$attemptRelative = "tmp\m270_memory_headroom\attempt_$Attempt"
$attemptRoot = Join-Path $workspace $attemptRelative
$formal = Join-Path $workspace "deployment\mage_vl4b\M270_M269_MEMORY_HEADROOM_BOARD_RESULT_$Attempt.json"
if (Test-Path -LiteralPath $attemptRoot) { throw "M270 attempt already exists: $attemptRoot" }
if (Test-Path -LiteralPath $formal) { throw "M270 result already exists: $formal" }
New-Item -ItemType Directory -Path $attemptRoot | Out-Null

& (Join-Path $PSScriptRoot 'm255_require_uart_shell.ps1') -Port $Port `
    -ExpectedFtdiSerial $ExpectedFtdiSerial -LogPath (Join-Path $attemptRelative 'shell_probe_uart.log')

$relativeProbe = $probe.Substring($workspace.Length + 1)
$remoteProbe = '/dev/shm/tellme_m270_board_memory_headroom_probe.py'
& (Join-Path $PSScriptRoot 'm212_uart_put_file_chunked.ps1') -LocalPath $relativeProbe `
    -RemotePath $remoteProbe -Port $Port -ExpectedFtdiSerial $ExpectedFtdiSerial `
    -LogPrefix (Join-Path $attemptRelative 'upload_probe') -ChunkBytes 1800 -TimeoutSeconds 60

$cacheBytes = 66699264
$runLog = Join-Path $attemptRoot 'run_uart.log'
$commandError = $null
try {
    & (Join-Path $PSScriptRoot 'm75c_uart_command.ps1') `
        -Command "python3 $remoteProbe --expected-self-sha256 $probeHash --cache-bytes $cacheBytes --reserve-mib $ReserveMiB" `
        -Port $Port -ExpectedFtdiSerial $ExpectedFtdiSerial `
        -LogPath (Join-Path $attemptRelative 'run_uart.log') -TimeoutSeconds 30
} catch {
    $commandError = $_
}

$text = Get-Content -Raw -LiteralPath $runLog
$match = [regex]::Match($text, '(?s)__M270_MEMORY_RESULT_BEGIN__\s*(\{.*?\})\s*__M270_MEMORY_RESULT_END__')
if (-not $match.Success) { throw 'M270 result envelope missing from UART log' }
[IO.File]::WriteAllText($formal, ($match.Groups[1].Value + "`n"), [Text.UTF8Encoding]::new($false))
& $python -B -c "import json,sys; p=sys.argv[1]; j=json.load(open(p,encoding='utf-8')); assert j['gate']=='M270-M269-KV260-read-only-memory-headroom'; assert j['status']=='PASS_READ_ONLY_HEADROOM'; print('M270_FORMAL_RESULT_PASS')" $formal
if ($LASTEXITCODE -ne 0) { throw "M270 formal result validation failed rc=$LASTEXITCODE" }
if ($null -ne $commandError) { throw $commandError }
Write-Output "M270_KV260_MEMORY_HEADROOM_UART_GATE_PASS result=$formal"
