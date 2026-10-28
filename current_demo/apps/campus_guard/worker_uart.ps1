param(
 [Parameter(Mandatory=$true)][string]$Command,
 [Parameter(Mandatory=$true)][string]$LogPath,
 [string]$Api='http://127.0.0.1:8765',
 [string]$TokenPath='apps/campus_guard/var/worker_token',
 [int]$TimeoutSeconds=1800,
 [switch]$AutoCheckFour
)
$ErrorActionPreference='Stop'
Set-StrictMode -Version Latest
$workspace=(Resolve-Path (Join-Path $PSScriptRoot '../..')).Path
$python='C:/Users/30429/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/python.exe'
$fullLog=Join-Path $workspace $LogPath
if(Test-Path -LiteralPath $fullLog){throw 'Existing attempt: collect only'}
New-Item -ItemType Directory -Force -Path (Split-Path $fullLog) | Out-Null
$headers=@{'X-Worker-Token'=(Get-Content -Raw -LiteralPath (Join-Path $workspace $TokenPath)).Trim()}
function Pulse([bool]$ready){Invoke-RestMethod -Method Post -Uri "$Api/api/worker/heartbeat" -Headers $headers -ContentType 'application/json' -Body (@{ready=$ready;warm=$ready;build='M529 M525-small8 10V18L fixed128'}|ConvertTo-Json -Compress) -TimeoutSec 5 | Out-Null}
function Decode-Packet([string]$line,[string]$kind){
 if($line -notmatch ('^M529_'+$kind+' ([0-9a-f]{64}) ([A-Za-z0-9+/=]+)$')){throw 'Malformed worker packet'}
 $expected=$Matches[1];$bytes=[Convert]::FromBase64String($Matches[2]);$inputStream=[IO.MemoryStream]::new([byte[]]$bytes);$outputStream=[IO.MemoryStream]::new()
 try{$z=[IO.Compression.ZLibStream]::new($inputStream,[IO.Compression.CompressionMode]::Decompress);$z.CopyTo($outputStream);$raw=$outputStream.ToArray();$z.Dispose()}finally{$inputStream.Dispose();$outputStream.Dispose()}
 if($raw.Length -gt 32768){throw 'Oversize raw packet'}
 $digest=[Convert]::ToHexString([Security.Cryptography.SHA256]::HashData($raw)).ToLowerInvariant()
 if($digest -ne $expected){throw 'Worker packet SHA mismatch'}
 return ([Text.Encoding]::UTF8.GetString($raw)|ConvertFrom-Json -AsHashtable)
}
# Preserve original exact FTDI/COM3 and management-shell checks.
$devices=@(Get-CimInstance Win32_PnPEntity | Where-Object {$_.Name -match '\(COM3\)$'})
if($devices.Count -ne 1 -or $devices[0].PNPDeviceID -notmatch 'XFL1PL5N11BJB'){throw 'Exact COM3 FTDI device required'}
if($Command -notmatch '^sudo -n bash /dev/shm/m529_campus_worker_package01/run\.sh [0-9a-f]{64} [0-9a-f]{64}$'){throw 'Frozen runner command only'}
$serial=[IO.Ports.SerialPort]::new('COM3',115200,[IO.Ports.Parity]::None,8,[IO.Ports.StopBits]::One)
$serial.Handshake=[IO.Ports.Handshake]::None;$serial.Encoding=[Text.Encoding]::UTF8;$serial.NewLine="`n";$serial.ReadTimeout=250;$serial.WriteTimeout=2000;$serial.ReadBufferSize=65536
$captured=[Text.StringBuilder]::new();$lineBuffer='';$nonce=$null;$waiting=$false;$autoIndex=0;$lastPulse=[DateTime]::MinValue
$autoCases=@('cal_04_t0','cal_00_t0','cal_04_t1','cal_00_t1')
try{
 Pulse $false;$serial.Open();$serial.Write("`n");$deadline=[DateTime]::UtcNow.AddSeconds(5);$prompt=$false
 while([DateTime]::UtcNow -lt $deadline){$chunk=$serial.ReadExisting();if($chunk.Length){[void]$captured.Append($chunk);[IO.File]::AppendAllText($fullLog,$chunk);if($captured.ToString() -match '(?m)(?:login:|Password:|password:)\s*$'){throw 'Operator login needed; no command sent'};if($captured.ToString() -match '(?m)^>\s*$'){throw 'Continuation prompt; no command sent'};if($captured.ToString() -match '(?m)root@kria:[^\r\n]*#\s*$'){$prompt=$true;break}};Start-Sleep -Milliseconds 100}
 if(-not $prompt){throw 'Root management shell not confirmed; no runner sent'}
 $wrapped=$Command+'; rc=$?; echo __M529_WORKER_RC_${rc}__'
 for($offset=0;$offset -lt $wrapped.Length;$offset+=64){$serial.Write($wrapped.Substring($offset,[Math]::Min(64,$wrapped.Length-$offset)));Start-Sleep -Milliseconds 10};$serial.Write("`n")
 $deadline=[DateTime]::UtcNow.AddSeconds($TimeoutSeconds)
 while([DateTime]::UtcNow -lt $deadline){
  $chunk=$serial.ReadExisting()
  if($chunk.Length){[IO.File]::AppendAllText($fullLog,$chunk);Write-Host -NoNewline $chunk;$lineBuffer+=$chunk
   if($lineBuffer.Contains('M523_M455_P1_RETAIN_PROCESS_LOCK_OVERLAY_ALL_OWNERS')){throw 'Unknown board context retained: close host reader only'}
   while($lineBuffer.Contains("`n")){
    $at=$lineBuffer.IndexOf("`n");$line=$lineBuffer.Substring(0,$at).Trim("`r");$lineBuffer=$lineBuffer.Substring($at+1)
    if($line.StartsWith('M529_READY ')){$ready=Decode-Packet $line 'READY';if($ready.nonce -notmatch '^[0-9a-f]{32}$'){throw 'Fresh readiness nonce invalid'};$nonce=$ready.nonce;$waiting=$true;Pulse $true;$lastPulse=[DateTime]::UtcNow}
    elseif($line.StartsWith('M529_RESULT ')){
     $answer=Decode-Packet $line 'RESULT';$packetPath=Join-Path (Split-Path $fullLog) ('job_'+$answer.ui_job_id+'.packet');if(Test-Path $packetPath){throw 'Duplicate completed job'}
     [IO.File]::WriteAllText($packetPath,$line,[Text.UTF8Encoding]::new($false));$saved=& $python -X utf8 -B (Join-Path $PSScriptRoot 'save_live_result.py') $packetPath
     if($LASTEXITCODE -ne 0){throw 'Save/sync failed; preserve original packet; no replay'}
     $body=($saved -join "`n")|ConvertFrom-Json -AsHashtable
     Invoke-RestMethod -Method Post -Uri "$Api/api/worker/result" -Headers $headers -ContentType 'application/json' -Body ($body|ConvertTo-Json -Compress) -TimeoutSec 10 | Out-Null
    }
    elseif($line.StartsWith('M529_STOP ')){$waiting=$false;Pulse $false}
    elseif($line -match '^__M529_WORKER_RC_([0-9]+)__$'){$rc=[int]$Matches[1];Pulse $false;Write-Output "M529_WORKER_HOST_COMPLETE rc=$rc";exit $rc}
   }
  }
  if(([DateTime]::UtcNow-$lastPulse).TotalSeconds -ge 2){Pulse $waiting;$lastPulse=[DateTime]::UtcNow}
  if($waiting){
   if($AutoCheckFour -and $autoIndex -lt $autoCases.Count){
    Invoke-RestMethod -Method Post -Uri "$Api/api/verify" -ContentType 'application/json' -Body (@{case_id=$autoCases[$autoIndex]}|ConvertTo-Json -Compress) -TimeoutSec 5 | Out-Null;$autoIndex++
   }
   $next=Invoke-RestMethod -Method Get -Uri "$Api/api/worker/next" -Headers $headers -TimeoutSec 5
   if($null -ne $next.job){
    $job=$next.job
    if($job.id -notmatch '^[0-9a-f]{32}$' -or $job.case_id -notin $autoCases){throw 'Only UUID and frozen four cases allowed'}
    $message=@{action='infer';nonce=$nonce;id=$job.id;case_id=$job.case_id}|ConvertTo-Json -Compress
    if([Text.Encoding]::UTF8.GetByteCount($message) -gt 512){throw 'Oversize job data'}
    Pulse $false;$serial.Write($message+"`n");$waiting=$false;$nonce=$null
   }
  }
  Start-Sleep -Milliseconds 100
 }
 throw 'Worker host time bound reached: no signals; preserve board context'
}finally{try{Pulse $false}catch{};if($serial.IsOpen){$serial.Close()};$serial.Dispose()}
