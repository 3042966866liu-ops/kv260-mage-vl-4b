param([switch]$Run)
$ErrorActionPreference='Stop'
$taskRoot=(Resolve-Path (Join-Path $PSScriptRoot '../..')).Path
if(-not $Run){throw 'Explicit Run required'}
$taskMax=Join-Path $taskRoot 'deployment/mage_vl4b/optimization_v1/runs/M357-max-fifo-rtl-03/RESULT.json'
if(-not(Test-Path $taskMax)){throw 'Maximum FIFO evidence incomplete'}
$taskMaxData=Get-Content -LiteralPath $taskMax -Raw -Encoding UTF8 | ConvertFrom-Json
if($taskMaxData.status -ne 'PASS_MAX_DESCRIPTOR_FIFO_RTL'){throw 'Maximum FIFO rejected'}
$taskMaxSha=(Get-FileHash -LiteralPath $taskMax -Algorithm SHA256).Hash.ToLowerInvariant()
foreach($n in @('CURRENT_STATE.md','docsMILESTONES.md','deployment/mage_vl4b/BOARD_GATE_RESULT.json')){
  if(-not([IO.File]::ReadAllText((Join-Path $taskRoot $n)).Contains($taskMaxSha))){throw "Prior not synchronized: $n"}
}
$taskPrep=Join-Path $taskRoot 'deployment/mage_vl4b/optimization_v1/runs/M357-timeout-preparation-01/RESULT.json'
if((Get-FileHash $taskPrep -Algorithm SHA256).Hash.ToLowerInvariant() -ne '03b143dcfc00f219622435618f825ea22df23aafc8747fdbf2e4c1982a973fb5'){throw 'Timeout preparation SHA changed'}
$taskSpec=Get-Content -LiteralPath $taskPrep -Raw -Encoding UTF8 | ConvertFrom-Json
foreach($row in $taskSpec.files){
  if((Get-FileHash -LiteralPath (Join-Path $taskRoot $row.path) -Algorithm SHA256).Hash.ToLowerInvariant() -ne $row.sha256){throw "Timeout input changed: $($row.path)"}
}
$taskSim=Join-Path $taskRoot 'tmp/m357_timeout_negative_01/verilog'
Push-Location $taskSim
try{
  if(Test-Path m357_timeout_xsim.log){throw 'Existing timeout attempt; collect only'}
  $taskArgs=@'
-testplusarg UVM_VERBOSITY=UVM_NONE
-testplusarg UVM_TESTNAME=m89x_runtime_kernel_test_lib
-testplusarg UVM_TIMEOUT=20000000000000
-testplusarg M357_ZERO_EXTRA_LATENCY
-testplusarg M357_EXPECT_TIMEOUT
-sv_seed 357
--noieeewarnings
-onerror quit
-tclbatch run_timeout.tcl
-log m357_timeout_xsim.log
'@
  [IO.File]::WriteAllText((Join-Path $taskSim 'm357_timeout.args'),$taskArgs,[Text.UTF8Encoding]::new($false))
  & 'D:/AMDDesignTools/2026.1/Vivado/bin/xsim.bat' m357_guarded -f m357_timeout.args *> m357_timeout_console.log
  $taskRc=$LASTEXITCODE
  $taskLog=[IO.File]::ReadAllText((Join-Path $taskSim 'm357_timeout_xsim.log'))
  $taskTimeout=$taskLog.Contains('M357_RTL_TIMEOUT_TRIGGERED ap_done=0 budget_cycles=200') -and $taskLog.Contains('M357 bounded timeout expired before ap_done')
  $taskGateRc=if($taskTimeout){1}else{2}
  $taskReceipt=@{simulation_rc=$taskRc;gate_rc=$taskGateRc;timeout_observed=$taskTimeout;expected_negative=$true;prior_max_sha256=$taskMaxSha} | ConvertTo-Json -Compress
  [IO.File]::WriteAllText((Join-Path $taskSim 'm357_timeout_exit.json'),$taskReceipt,[Text.UTF8Encoding]::new($false))
  Get-Content -LiteralPath m357_timeout_console.log -Tail 15
  if(-not $taskTimeout){throw 'Expected timeout not observed; no PASS'}
  Write-Output "M357_EXPECTED_TIMEOUT_OBSERVED original_simulator_rc=$taskRc fail_closed_gate_rc=$taskGateRc"
}finally{Pop-Location}
