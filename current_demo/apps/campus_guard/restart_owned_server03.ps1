$ErrorActionPreference='Stop';Set-StrictMode -Version Latest
$root=(Resolve-Path (Join-Path $PSScriptRoot '../..')).Path
$state=$null
try{$state=Invoke-RestMethod -Uri 'http://127.0.0.1:8766/api/state' -TimeoutSec 3}catch{}
if($null -ne $state -and $null -ne $state.worker){throw 'Existing worker: do not restart the server during a board scope'}
$python='C:\Users\30429\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe'
$owned=@(Get-CimInstance Win32_Process | Where-Object {$_.ExecutablePath -eq $python -and $_.CommandLine -match 'apps[/\\]campus_guard[/\\]live_server\.py[" ]+--port[" ]+8766(?:[" ]|$)'})
if($owned.Count -gt 1){throw 'Ambiguous owned server; no stop'}
foreach($p in $owned){Stop-Process -Id $p.ProcessId -ErrorAction Stop}
& (Join-Path $PSScriptRoot 'start_demo.ps1') -NoBrowser
if($LASTEXITCODE){exit $LASTEXITCODE}
$now=Invoke-RestMethod -Uri 'http://127.0.0.1:8766/api/state' -TimeoutSec 3
$binding=Get-Content -LiteralPath (Join-Path $PSScriptRoot 'LIVE_BINDING.json') -Raw -Encoding UTF8 | ConvertFrom-Json
if($now.worker_package_sha256 -ne $binding.package_manifest_sha256){throw 'Server binding differs'}
Write-Output 'Owned local server loaded current binding. No board access.'
