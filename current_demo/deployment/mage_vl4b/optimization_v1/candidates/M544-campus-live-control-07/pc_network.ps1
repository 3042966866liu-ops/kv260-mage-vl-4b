[CmdletBinding()]
param([Parameter(Mandatory=$true)][ValidateSet('Before','After')][string]$Mode,
      [Parameter(Mandatory=$true)][ValidateSet('Baseline')][string]$Level)
$ErrorActionPreference='Stop'
Set-StrictMode -Version Latest
$taskRoot='C:/Users/30429/Desktop/TeLLMe_FPGA_2026'
$taskDirectory=Join-Path $taskRoot "tmp/m544_live_worker07/$($Level)_fetch"
[void][IO.Directory]::CreateDirectory($taskDirectory)
$taskOutput=Join-Path $taskDirectory "pc_network_$($Mode.ToLowerInvariant())01.json"
if(Test-Path -LiteralPath $taskOutput){throw 'Original snapshot exists; inspect only'}
$taskAddresses=@(Get-NetIPAddress -AddressFamily IPv4|Select-Object InterfaceIndex,IPAddress,PrefixLength|Sort-Object InterfaceIndex,IPAddress,PrefixLength)
$taskRoutes=@(Get-NetRoute -AddressFamily IPv4 -DestinationPrefix '0.0.0.0/0'|Select-Object InterfaceIndex,DestinationPrefix,NextHop,RouteMetric|Sort-Object InterfaceIndex,NextHop,RouteMetric)
$taskPeer=@($taskAddresses|Where-Object {$_.IPAddress -eq '192.168.0.10' -and $_.PrefixLength -eq 24})
if($taskPeer.Count -ne 1){throw 'Exact existing PC source 192.168.0.10/24 required; no network mutation'}
$taskValue=[ordered]@{status='SAVED_PC_M523_B0_NETWORK_BEFORE01';addresses=$taskAddresses;default_routes=$taskRoutes;network_mutations=0;specific_source='192.168.0.10'}
if($Mode -eq 'After'){
 $taskBefore=Get-Content -LiteralPath (Join-Path $taskDirectory 'pc_network_before01.json') -Raw -Encoding UTF8|ConvertFrom-Json
 if((ConvertTo-Json -Depth 8 -Compress $taskAddresses) -ne (ConvertTo-Json -Depth 8 -Compress $taskBefore.addresses)){throw 'PC addresses changed'}
 if((ConvertTo-Json -Depth 8 -Compress $taskRoutes) -ne (ConvertTo-Json -Depth 8 -Compress $taskBefore.default_routes)){throw 'PC default routes changed'}
 $taskValue.status='PASS_PC_M523_B0_NETWORK_UNCHANGED01'
}
$taskRaw=[Text.UTF8Encoding]::new($false).GetBytes((ConvertTo-Json -Depth 8 $taskValue)+[Environment]::NewLine)
$taskPart=$taskOutput+'.partial'
$taskStream=[IO.File]::Open($taskPart,[IO.FileMode]::CreateNew,[IO.FileAccess]::Write,[IO.FileShare]::None)
try{$taskStream.Write($taskRaw,0,$taskRaw.Length);$taskStream.Flush($true)}finally{$taskStream.Dispose()}
[IO.File]::Move($taskPart,$taskOutput)
"M523_B0_PC_NETWORK_$($Mode.ToUpperInvariant())_SAVED_NO_MUTATION"
