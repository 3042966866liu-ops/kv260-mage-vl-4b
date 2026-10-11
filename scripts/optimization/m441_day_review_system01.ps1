param([Parameter(Mandatory=$true)][string]$OutputPath)
$ErrorActionPreference='Stop'
$taskResult=[ordered]@{status='READ_ONLY_SYSTEM_EVENT_QUERY';captured_utc=[DateTime]::UtcNow.ToString('o');board=$false;errors=@();events=@()}
try {
 $taskOs=Get-CimInstance Win32_OperatingSystem
 $taskResult.os=[ordered]@{last_boot_utc=$taskOs.LastBootUpTime.ToUniversalTime().ToString('o');total_visible_kib=$taskOs.TotalVisibleMemorySize;free_physical_kib=$taskOs.FreePhysicalMemory;total_virtual_kib=$taskOs.TotalVirtualMemorySize;free_virtual_kib=$taskOs.FreeVirtualMemory}
} catch {$taskResult.errors+=('OS: '+$_.Exception.Message)}
$taskSince=[DateTime]::UtcNow.AddHours(-48)
foreach($taskLog in @('System','Application')) {
 try {
  $taskIds=if($taskLog -eq 'System'){@(41,42,107,1074,6005,6006,6008,2004,506,507)}else{@(1000,1001)}
  $taskEvents=Get-WinEvent -FilterHashtable @{LogName=$taskLog;StartTime=$taskSince;Id=$taskIds} -MaxEvents 150 -ErrorAction Stop
  foreach($taskEvent in $taskEvents){
   if($taskLog -eq 'Application' -and $taskEvent.Message -notmatch 'xsim|vivado|python|pwsh|powershell|m441'){continue}
   $taskResult.events+=([ordered]@{log=$taskLog;id=$taskEvent.Id;provider=$taskEvent.ProviderName;time_utc=$taskEvent.TimeCreated.ToUniversalTime().ToString('o');record_id=$taskEvent.RecordId;message=$taskEvent.Message;xml=$taskEvent.ToXml()})
  }
 } catch {$taskResult.errors+=($taskLog+': '+$_.Exception.Message)}
}
try {$taskResult.processes=@(Get-Process | Where-Object {$_.ProcessName -match 'xsim|m441|vivado|python|pwsh'} | Select-Object Id,ProcessName,CPU,WorkingSet64,PrivateMemorySize64)} catch {$taskResult.errors+=('Processes: '+$_.Exception.Message)}
if(Test-Path -LiteralPath $OutputPath){throw 'Read-only query evidence already exists'}
$taskFull=[IO.Path]::GetFullPath($OutputPath)
$taskRoot=[IO.Path]::GetFullPath('C:\Users\30429\Desktop\TeLLMe_FPGA_2026\deployment\mage_vl4b\optimization_v1\runs\M441-day-review-01')
if(-not $taskFull.StartsWith($taskRoot+[IO.Path]::DirectorySeparatorChar,[StringComparison]::OrdinalIgnoreCase)){throw 'Evidence destination outside review directory'}
[IO.Directory]::CreateDirectory([IO.Path]::GetDirectoryName($taskFull))|Out-Null
[IO.File]::WriteAllText($taskFull+'.part',($taskResult|ConvertTo-Json -Depth 10),[Text.UTF8Encoding]::new($false))
[IO.File]::Move($taskFull+'.part',$taskFull)
Write-Output ('SAVED_READ_ONLY_SYSTEM_EVENTS '+$taskFull)
