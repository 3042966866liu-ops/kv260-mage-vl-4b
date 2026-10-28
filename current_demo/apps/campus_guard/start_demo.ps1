param([switch]$ConnectBoard,[switch]$NoBrowser)
$ErrorActionPreference='Stop'
Set-StrictMode -Version Latest
$root=(Resolve-Path (Join-Path $PSScriptRoot '../..')).Path
$python='C:/Users/30429/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/python.exe'
$url='http://127.0.0.1:8766'
$logs=Join-Path $PSScriptRoot 'var/live/launcher'
New-Item -ItemType Directory -Force -Path $logs | Out-Null
$expected=(Get-FileHash -Algorithm SHA256 -LiteralPath (Join-Path $PSScriptRoot 'live_server.py')).Hash.ToLowerInvariant()
$state=$null
try{$state=Invoke-RestMethod -Uri ($url+'/api/state') -TimeoutSec 2}catch{}
if($null -eq $state){
 $stamp=[DateTime]::UtcNow.ToString('yyyyMMdd_HHmmss_ffff')
 $launchArgs=@('-X','utf8','-B','apps/campus_guard/live_server.py','--port','8766')
 $null=Start-Process -FilePath $python -ArgumentList $launchArgs -WorkingDirectory $root -WindowStyle Hidden -RedirectStandardOutput (Join-Path $logs ($stamp+'.out')) -RedirectStandardError (Join-Path $logs ($stamp+'.err')) -PassThru
 for($i=0;$i -lt 30;$i++){
  try{$state=Invoke-RestMethod -Uri ($url+'/api/state') -TimeoutSec 2;break}catch{Start-Sleep -Milliseconds 200}
 }
}
if($null -eq $state -or $state.web_source_sha256 -ne $expected){throw 'Local server is unavailable or has an older source. Do not kill an unknown process; restart only the confirmed campus live server.'}
if(-not $NoBrowser){Start-Process $url | Out-Null}
Write-Host ('Campus demonstration: '+$url)
if($ConnectBoard){
 $binding=Get-Content -LiteralPath (Join-Path $PSScriptRoot 'LIVE_BINDING.json') -Raw -Encoding UTF8 | ConvertFrom-Json
 $imported=Join-Path $root $binding.worker_import_result
 if(-not (Test-Path -LiteralPath $imported)){Write-Host 'Preview ready. Actual A53 Import is still pending; no board command sent.';exit 0}
 if($null -ne $state.worker){Write-Host 'Existing board worker detected. No duplicate launch.';exit 0}
 Push-Location $root
 try{& $python -X utf8 -B apps/campus_guard/run_live_worker07.py --purpose operator-demo;exit $LASTEXITCODE}finally{Pop-Location}
}
