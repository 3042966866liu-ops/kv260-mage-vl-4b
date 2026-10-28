param(
 [Parameter(Mandatory=$true)][string]$Command,
 [Parameter(Mandatory=$true)][string]$LogPath,
 [Parameter(Mandatory=$true)][string]$Session,
 [Parameter(Mandatory=$true)][string]$Manifest,
 [string]$Api='http://127.0.0.1:8766',
 [string]$TokenPath='apps/campus_guard/var/live/worker_token',
 [int]$TimeoutSeconds=3000
)
$ErrorActionPreference='Stop';Set-StrictMode -Version Latest
$workspace=(Resolve-Path (Join-Path $PSScriptRoot '../..')).Path
$python='C:/Users/30429/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/python.exe'
$fullLog=Join-Path $workspace $LogPath
if(Test-Path -LiteralPath $fullLog){throw 'Existing attempt: collect only'}
New-Item -ItemType Directory -Force -Path (Split-Path $fullLog)|Out-Null
if($Session -notmatch '^[0-9a-f]{32}$' -or $Manifest -notmatch '^[0-9a-f]{64}$' -or $Api -notmatch '^http://127\.0\.0\.1:[0-9]+$'){throw 'Frozen local session required'}
if($Command -notmatch ('^sudo -n bash /dev/shm/m544_live_worker_package01/run\.sh [0-9a-f]{64} '+$Manifest+' '+$Session+'$')){throw 'Frozen versioned runner only'}
$tokenFile=Join-Path $workspace $TokenPath;$headers=@{'X-Worker-Token'=(Get-Content -Raw -LiteralPath $tokenFile).Trim()}
$uploadsRoot=[IO.Path]::GetFullPath((Join-Path (Split-Path $tokenFile) 'uploads'))+[IO.Path]::DirectorySeparatorChar
function Call-Api([string]$path,$data=$null){
 if($null -eq $data){return Invoke-RestMethod -Method Get -Uri ($Api+$path) -Headers $headers -TimeoutSec 6}
 return Invoke-RestMethod -Method Post -Uri ($Api+$path) -Headers $headers -ContentType 'application/json' -Body ($data|ConvertTo-Json -Depth 8 -Compress) -TimeoutSec 6
}
$warm=$false
function Pulse([bool]$ready,[bool]$closed=$false){Call-Api '/api/worker/heartbeat' @{session=$Session;package_manifest_sha256=$Manifest;ready=$ready;warm=$script:warm;closed=$closed}|Out-Null}
function Hash([byte[]]$b){return [Convert]::ToHexString([Security.Cryptography.SHA256]::HashData($b)).ToLowerInvariant()}
function Decode([string]$line,[string]$kind){
 if($line -notmatch ('^M544_'+$kind+' ([0-9a-f]{64}) ([A-Za-z0-9+/=]{1,65536})$')){throw 'Malformed bounded worker packet'}
 $expected=$Matches[1];$bytes=[Convert]::FromBase64String($Matches[2]);$inputStream=[IO.MemoryStream]::new([byte[]]$bytes);$output=[IO.MemoryStream]::new()
 try{$z=[IO.Compression.ZLibStream]::new($inputStream,[IO.Compression.CompressionMode]::Decompress);$buffer=[byte[]]::new(4096);while(($n=$z.Read($buffer,0,$buffer.Length)) -gt 0){if($output.Length+$n -gt 32768){throw 'Oversize decoded packet'};$output.Write($buffer,0,$n)};$z.Dispose();$raw=$output.ToArray()}finally{$inputStream.Dispose();$output.Dispose()}
 if((Hash $raw) -ne $expected){throw 'Worker packet SHA differs'}
 $v=[Text.Encoding]::UTF8.GetString($raw)|ConvertFrom-Json -AsHashtable
 if($v.session -ne $Session -or $v.package_manifest_sha256 -ne $Manifest){throw 'Worker session/manifest differs'}
 return $v
}
$devices=@(Get-CimInstance Win32_PnPEntity|Where-Object {$_.Name -match '\(COM3\)$'})
if($devices.Count -ne 1 -or $devices[0].PNPDeviceID -notmatch 'XFL1PL5N11BJB'){throw 'Exact FTDI COM3 required'}
$serial=[IO.Ports.SerialPort]::new('COM3',115200,[IO.Ports.Parity]::None,8,[IO.Ports.StopBits]::One)
$serial.Handshake=[IO.Ports.Handshake]::None;$serial.Encoding=[Text.Encoding]::UTF8;$serial.NewLine="`n";$serial.ReadTimeout=250;$serial.WriteTimeout=3000;$serial.ReadBufferSize=65536
function Read-Available(){
 $chunk=$serial.ReadExisting()
 if($chunk.Length){[IO.File]::AppendAllText($fullLog,$chunk,[Text.UTF8Encoding]::new($false));Write-Host -NoNewline $chunk}
 return $chunk
}
function Send-Data($value){$line=$value|ConvertTo-Json -Depth 6 -Compress;if([Text.Encoding]::UTF8.GetByteCount($line)+1 -gt 1024){throw 'Data line exceeds frozen1024bytes'};$serial.Write($line+"`n")}
function Frame-Transfer($f,[string]$nonce){
 $path=[IO.Path]::GetFullPath([string]$f.frame_file)
 if(-not $path.StartsWith($uploadsRoot,[StringComparison]::OrdinalIgnoreCase)){throw 'Frame outside owned upload root'}
 $item=Get-Item -LiteralPath $path;if($item.LinkType -or $item.Length -ne 602240){throw 'Plain exact RGB NPY required'}
 $raw=[IO.File]::ReadAllBytes($path);if((Hash $raw) -ne $f.frame_sha256){throw 'Prepared input file SHA differs'}
 $stream=[IO.MemoryStream]::new();$z=[IO.Compression.ZLibStream]::new($stream,[IO.Compression.CompressionLevel]::Fastest,$true);$z.Write($raw,0,$raw.Length);$z.Dispose();$bytes=$stream.ToArray();$stream.Dispose()
 if($bytes.Length -gt 1048576){throw 'Compressed RGB frame too large'}
 $id=[Guid]::NewGuid().ToString('N');$head=@{action='frame';nonce=$nonce;id=$id;case_id=$f.case_id;frame_sha256=$f.frame_sha256;pixel_sha256=$f.pixel_sha256;video_sha256=$f.video_sha256;upload_id=$f.upload_id;timestamp_ms=$f.timestamp_ms;compressed_bytes=$bytes.Length;compressed_sha256=(Hash $bytes);file_bytes=$raw.Length}
 Send-Data $head
 return @{id=$id;bytes=$bytes;next_seq=0;frame=$f}
}
$lineBuffer='';$waiting=$false;$nonce=$null;$transfer=$null;$currentJob=$null;$lastPulse=[DateTime]::MinValue;$originalRc=$null
try{
 Pulse $false;$serial.Open();$serial.Write("`n");$capture='';$until=[DateTime]::UtcNow.AddSeconds(6)
 while([DateTime]::UtcNow -lt $until){$capture+=Read-Available;if($capture -match '(?m)(?:login:|Password:|password:)\s*$'){throw 'Root operator shell required; no command sent'};if($capture -match '(?m)^>\s*$'){throw 'Continuation prompt; no command sent'};if($capture -match '(?m)root@kria:[^\r\n]*#\s*$'){break};Start-Sleep -Milliseconds 80}
 if($capture -notmatch '(?m)root@kria:[^\r\n]*#\s*$'){throw 'Root shell unconfirmed; no command sent'}
 $serial.Write('sudo -n true; rc=$?; echo __M544_AUTH_RC_${rc}__'+"`n");$capture='';$until=[DateTime]::UtcNow.AddSeconds(12)
 while([DateTime]::UtcNow -lt $until){$capture+=Read-Available;if($capture -match '__M544_AUTH_RC_([0-9]+)__'){if([int]$Matches[1] -ne 0){throw 'Current terminal authorization failed'};break};Start-Sleep -Milliseconds 80}
 if($capture -notmatch '__M544_AUTH_RC_0__'){throw 'Authorization not confirmed; no runner sent'}
 $wrapped=$Command+'; rc=$?; echo __M544_WORKER_RC_${rc}__'
 for($i=0;$i -lt $wrapped.Length;$i+=64){$serial.Write($wrapped.Substring($i,[Math]::Min(64,$wrapped.Length-$i)));Start-Sleep -Milliseconds 10};$serial.Write("`n")
 $until=[DateTime]::UtcNow.AddSeconds($TimeoutSeconds)
 while([DateTime]::UtcNow -lt $until){
  $chunk=Read-Available
  if($chunk.Length){$lineBuffer+=$chunk;if($lineBuffer.Contains('M523_M455_P1_RETAIN_PROCESS_LOCK_OVERLAY_ALL_OWNERS')){throw 'Unknown board state retained; no signals or retry'}
   while($lineBuffer.Contains("`n")){
    $at=$lineBuffer.IndexOf("`n");$line=$lineBuffer.Substring(0,$at).Trim("`r");$lineBuffer=$lineBuffer.Substring($at+1)
    if($line.StartsWith('M544_READY ')){
     $p=Decode $line 'READY';if($p.nonce -notmatch '^[0-9a-f]{32}$'){throw 'Invalid nonce'}
     if(-not $script:warm){
      $fixedPacket=Join-Path (Split-Path $fullLog) 'fixed_warmup_READY.packet';if(Test-Path -LiteralPath $fixedPacket){throw 'Existing fixed gate receipt; inspect only'}
      [IO.File]::WriteAllText($fixedPacket,$line,[Text.UTF8Encoding]::new($false))
      & $python -X utf8 -B (Join-Path $PSScriptRoot 'save_fixed_warmup03.py') $fixedPacket | Out-Null
      if($LASTEXITCODE -ne 0){throw 'Current boot fixed warmup gate is not synchronized; no Web task sent'}
     }
     $nonce=$p.nonce;$waiting=$true;$script:warm=$true;Pulse $true;$lastPulse=[DateTime]::UtcNow
    }
    elseif($line.StartsWith('M544_ACK ')){
     $p=Decode $line 'ACK';if($null -eq $transfer -or $p.id -ne $transfer.id -or [int]$p.next_seq -ne $transfer.next_seq){throw 'Upload ACK mismatch'}
     $offset=$transfer.next_seq*512;$count=[Math]::Min(512,$transfer.bytes.Length-$offset);if($count -le 0){throw 'Unexpected extra ACK'}
     $part=[byte[]]::new($count);[Array]::Copy($transfer.bytes,$offset,$part,0,$count);Send-Data @{action='chunk';id=$transfer.id;seq=$transfer.next_seq;data=[Convert]::ToBase64String($part)};$transfer.next_seq++
    }
    elseif($line.StartsWith('M544_PREPARED ')){
     $p=Decode $line 'PREPARED';if($null -eq $transfer -or $p.id -ne $transfer.id -or $p.case_id -ne $transfer.frame.case_id){throw 'Prepared input identity differs'}
     Call-Api '/api/worker/prepared' $p|Out-Null;$transfer=$null
    }
    elseif($line.StartsWith('M544_RESULT ')){
     $p=Decode $line 'RESULT';if($null -eq $currentJob -or $p.ui_job_id -ne $currentJob.id -or $p.frame_sha256 -ne $currentJob.frame_sha256){throw 'Current job/result identity differs'}
     $packet=Join-Path (Split-Path $fullLog) ('job_'+$p.ui_job_id+'.packet');if(Test-Path -LiteralPath $packet){throw 'Duplicate result packet'}
     [IO.File]::WriteAllText($packet,$line,[Text.UTF8Encoding]::new($false));$saved=& $python -X utf8 -B (Join-Path $PSScriptRoot 'save_live_result02.py') $packet
     if($LASTEXITCODE -ne 0){throw 'Saving live proof failed; preserve packet, no replay'}
     $body=($saved -join "`n")|ConvertFrom-Json -AsHashtable;Call-Api '/api/worker/result' $body|Out-Null;$currentJob=$null
    }
    elseif($line.StartsWith('M544_ERROR ')){$p=Decode $line 'ERROR';if($null -ne $currentJob){Call-Api '/api/worker/failed' @{id=$currentJob.id}|Out-Null};$transfer=$null;$currentJob=$null;$waiting=$false}
    elseif($line.StartsWith('M544_STOP ')){$null=Decode $line 'STOP';$waiting=$false;Pulse $false}
    elseif($line -match '^__M544_WORKER_RC_([0-9]+)__$'){$originalRc=[int]$Matches[1];Pulse $false $true;Write-Output "M544_WORKER_HOST_COMPLETE rc=$originalRc";exit $originalRc}
   }
  }
  if(([DateTime]::UtcNow-$lastPulse).TotalSeconds -gt 2){Pulse $waiting;$lastPulse=[DateTime]::UtcNow}
  if($waiting){
   $pre=Call-Api '/api/worker/prepare'
   if(($pre.PSObject.Properties.Name -contains 'stop') -and $pre.stop){Send-Data @{action='stop';nonce=$nonce};$waiting=$false;Pulse $false}
   else{
    $next=Call-Api '/api/worker/next'
    if($null -ne $next.job){$j=$next.job;if($j.session -ne $Session -or $j.id -notmatch '^[0-9a-f]{32}$'){throw 'New exact job required'};$currentJob=$j;Send-Data @{action='infer';nonce=$nonce;id=$j.id;case_id=$j.case_id;frame_sha256=$j.frame_sha256};$waiting=$false;Pulse $false}
    elseif($null -ne $pre.frame){$transfer=Frame-Transfer $pre.frame $nonce;$waiting=$false;Pulse $false}
   }
  }
  Start-Sleep -Milliseconds 35
 }
 throw 'Bounded worker host timeout; no signals or board retry'
}catch{if($null -ne $currentJob){try{Call-Api '/api/worker/failed' @{id=$currentJob.id}|Out-Null}catch{}};throw}
finally{try{Pulse $false $true}catch{};if($serial.IsOpen){$serial.Close()};$serial.Dispose()}
