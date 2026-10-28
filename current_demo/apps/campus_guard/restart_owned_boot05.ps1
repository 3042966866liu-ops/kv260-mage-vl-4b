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
$logs=Join-Path $PSScriptRoot 'var/live/launcher/boot05';if(Test-Path -LiteralPath $logs){throw 'Original restart already attempted'}
[void][IO.Directory]::CreateDirectory($logs)
[IO.File]::WriteAllText((Join-Path $logs 'before.json'),($proc|Select-Object ProcessId,ExecutablePath,CommandLine|ConvertTo-Json),[Text.UTF8Encoding]::new($false))
Stop-Process -Id $ownerId
$child=Start-Process -FilePath $python -ArgumentList @('-X','utf8','-B','apps/campus_guard/live_server.py','--port','8766') -WorkingDirectory $root -WindowStyle Hidden -RedirectStandardOutput (Join-Path $logs 'server.out') -RedirectStandardError (Join-Path $logs 'server.err') -PassThru
$expected=(Get-FileHash -LiteralPath (Join-Path $PSScriptRoot 'live_server.py') -Algorithm SHA256).Hash.ToLowerInvariant()
$binding=Get-Content -LiteralPath (Join-Path $PSScriptRoot 'LIVE_BINDING.json') -Raw -Encoding UTF8|ConvertFrom-Json
for($i=0;$i -lt 40;$i++){
 try{$s=Invoke-RestMethod 'http://127.0.0.1:8766/api/state' -TimeoutSec 2;if($s.web_source_sha256 -eq $expected -and $s.worker_package_sha256 -eq $binding.package_manifest_sha256){[IO.File]::WriteAllText((Join-Path $logs 'RESULT.json'),(@{status='RESTARTED_EXACT_OWNED_LOCAL_SERVER05';pid=$child.Id;old_pid=$ownerId;web_sha256=$expected;manifest=$binding.package_manifest_sha256;board_commands=0}|ConvertTo-Json),[Text.UTF8Encoding]::new($false));Write-Output 'OWNED_SERVER05_READY';exit 0}}catch{}
 Start-Sleep -Milliseconds 200
}
throw 'New local service did not match expected source/binding'
