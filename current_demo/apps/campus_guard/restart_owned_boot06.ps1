$ErrorActionPreference='Stop';Set-StrictMode -Version Latest
$root=(Resolve-Path (Join-Path $PSScriptRoot '../..')).Path
$state=Invoke-RestMethod 'http://127.0.0.1:8766/api/state' -TimeoutSec 4
if($null -ne $state.worker){throw 'Active worker: no local restart'}
$listeners=@(Get-NetTCPConnection -LocalPort 8766 -State Listen)
if($listeners.Count -ne 1 -or $listeners[0].LocalAddress -ne '127.0.0.1'){throw 'Unexpected server listener'}
$ownerId=[int]$listeners[0].OwningProcess
$proc=Get-CimInstance Win32_Process -Filter "ProcessId=$ownerId"
$python='C:/Users/30429/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/python.exe'
if($null -eq $proc -or $proc.ExecutablePath.Replace('\','/') -ne $python -or $proc.CommandLine.Replace('\','/') -notmatch 'apps/campus_guard/live_server\.py.*--port\s+8766'){throw 'Owned campus Python source not confirmed'}
$logs=Join-Path $PSScriptRoot 'var/live/launcher/boot06';if(Test-Path -LiteralPath $logs){throw 'Original restart already attempted'}
[void][IO.Directory]::CreateDirectory($logs)
[IO.File]::WriteAllText((Join-Path $logs 'before.json'),($proc|Select-Object ProcessId,ExecutablePath,CommandLine|ConvertTo-Json),[Text.UTF8Encoding]::new($false))
& $python -X utf8 -B apps/campus_guard/restart_from_record06.py
exit $LASTEXITCODE
