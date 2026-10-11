param([ValidateSet('A','B')][string]$Variant,[ValidateSet('gate_up','mlp_down','q')][string]$Family,[ValidateSet('Compile','Random','Zero')][string]$Mode,[switch]$Enable)
$ErrorActionPreference='Stop'
if(-not $Enable){throw 'Revision03 tool disabled; require -Enable'}
$taskRoot=(Resolve-Path (Join-Path $PSScriptRoot '../..')).Path
$taskPrepPath=Join-Path $taskRoot ('deployment/mage_vl4b/optimization_v1/runs/M441-long-'+$Variant+'-'+$Family+'-RTL-preparation-04/RESULT.json')
$taskPrep=Get-Content -LiteralPath $taskPrepPath -Raw -Encoding UTF8|ConvertFrom-Json
$taskGuardPath=Join-Path $taskRoot 'deployment/mage_vl4b/optimization_v1/runs/M441-guard03-component-02/RESULT.json'
$taskGuard=Get-Content -LiteralPath $taskGuardPath -Raw -Encoding UTF8|ConvertFrom-Json
if($taskGuard.status -ne 'PASS_M441_ACTUAL_SV_GUARD_COMPONENT_ONLY'){throw 'Actual guard component not proven'}
if((Get-FileHash -LiteralPath (Join-Path $taskRoot 'scripts/optimization/m441_observer03.py') -Algorithm SHA256).Hash.ToLower() -ne $taskPrep.observer_helper_sha256 -or $taskGuard.guard_logic_sha256 -ne $taskPrep.observer_helper_sha256){throw 'Observer helper changed'}
if(-not $taskPrep.ARLEN_histogram_recorded -or $taskPrep.observer_revision -ne '04'){throw 'ARLEN observer revision not proven'}
if($taskPrep.variant -ne $Variant -or $taskPrep.family -ne $Family){throw 'Wrong frozen preparation'}
foreach($taskFile in $taskPrep.files){
 if((Get-FileHash -LiteralPath (Join-Path $taskRoot $taskFile.path) -Algorithm SHA256).Hash.ToLower() -ne $taskFile.sha256){throw ('Changed RTL input: '+$taskFile.path)}
}
$taskSHA=(Get-FileHash -LiteralPath $taskPrepPath -Algorithm SHA256).Hash.ToLower()
foreach($taskDoc in @('CURRENT_STATE.md','docsMILESTONES.md')){
 if(-not (Get-Content -LiteralPath (Join-Path $taskRoot $taskDoc) -Raw -Encoding UTF8).Contains($taskSHA)){throw 'Preparation not synchronized'}
}
$taskBoard=Get-Content -LiteralPath (Join-Path $taskRoot 'deployment/mage_vl4b/BOARD_GATE_RESULT.json') -Raw -Encoding UTF8|ConvertFrom-Json
$taskKey='latest_m441_long_'+$Variant+'_'+$Family+'_RTL_preparation04'
if($taskBoard.$taskKey.sha256 -ne $taskSHA){throw 'BOARD preparation SHA differs'}
$taskSim=Join-Path $taskRoot ('tmp/m441_long_'+$Variant+'_'+$Family+'_04/verilog')
Push-Location $taskSim
try {
 if($Mode -eq 'Compile') {
  if(Test-Path 'compile.log'){throw 'Existing compile: collect only'}
  & 'D:/AMDDesignTools/2026.1/Vivado/bin/xelab.bat' xil_defaultlib.apatb_m89x_runtime_kernel_top xil_defaultlib.glbl xil_defaultlib.m441_monitor -Oenable_linking_all_libraries -prj m441.prj -L smartconnect_v1_0 -L axi_protocol_checker_v1_1_12 -L axi_protocol_checker_v1_1_13 -L axis_protocol_checker_v1_1_11 -L axis_protocol_checker_v1_1_12 -L xil_defaultlib -L unisims_ver -L xpm -L floating_point_v7_1_22 -L floating_point_v7_0_27 -L uvm -relax -i ./svr -i ./axivip -i ./svtb -i ./file_agent -i ./m89x_runtime_kernel_subsystem -s m441_trace -log compile.log *> compile_console.log
  $taskRc=$LASTEXITCODE
  [IO.File]::WriteAllText((Join-Path $taskSim 'compile_exit.json'),("{`"compile_rc`":$taskRc}"),[Text.UTF8Encoding]::new($false))
  if($taskRc -ne 0){throw "Compile rc=$taskRc"}
  Write-Output ('M441_COMPILE_RETURN '+$Variant+' '+$Family+' rc=0')
 } else {
  if(!(Test-Path 'compile_validated.json')){throw 'Compile not adjudicated'}
  $taskStem=$Mode.ToLower()
  if(Test-Path ($taskStem+'.log')){throw 'Existing run: collect only'}
  if(Test-Path ($taskStem+'_result')){throw 'Existing saved result: collect only'}
  if($Mode -eq 'Random' -and !(Test-Path 'zero_validated.json')){
   if($Family -ne 'gate_up'){throw 'Zero full-output gate must pass first'}
   $taskPriorPath=Join-Path $taskRoot ('deployment/mage_vl4b/optimization_v1/runs/M441-long-'+$Variant+'-gate_up-zero-02/RESULT.json')
   $taskPrior=Get-Content -LiteralPath $taskPriorPath -Raw -Encoding UTF8|ConvertFrom-Json
   $taskPriorSha=(Get-FileHash -LiteralPath $taskPriorPath -Algorithm SHA256).Hash.ToLower()
   $taskPriorKey='latest_m441_long_'+$Variant+'_gate_up_zero02'
   if($taskPrior.status -ne 'PASS_M441_COMPLETE_CHAIN_RTL_NUMERIC_AND_PROTOCOL' -or $taskBoard.$taskPriorKey.sha256 -ne $taskPriorSha){throw 'Original Zero evidence missing'}
   foreach($taskDoc in @('CURRENT_STATE.md','docsMILESTONES.md')){if(-not (Get-Content -LiteralPath (Join-Path $taskRoot $taskDoc) -Raw -Encoding UTF8).Contains($taskPriorSha)){throw 'Original Zero not synced'}}
   $taskOldPrepPath=Join-Path $taskRoot ('deployment/mage_vl4b/optimization_v1/runs/M441-long-'+$Variant+'-gate_up-RTL-preparation-02/RESULT.json')
   $taskOldPrep=Get-Content -LiteralPath $taskOldPrepPath -Raw -Encoding UTF8|ConvertFrom-Json
   if($taskPrep.fixture_sha256 -ne $taskOldPrep.fixture_sha256 -or $taskPrep.build_id -ne $taskOldPrep.build_id){throw 'Changed DUT/fixture'}
   foreach($taskOldFile in $taskOldPrep.files){
    if($taskOldFile.path.EndsWith('/m441_monitor.sv') -or $taskOldFile.path.EndsWith('/m89x_runtime_kernel_env.sv')){continue}
    $taskNewPath=$taskOldFile.path.Replace('_gate_up_02/','_gate_up_03/')
    if((Get-FileHash -LiteralPath (Join-Path $taskRoot $taskNewPath) -Algorithm SHA256).Hash.ToLower() -ne $taskOldFile.sha256){throw ('Changed nonobserver input: '+$taskNewPath)}
   }
  }
  $taskSwitch=if($Mode -eq 'Zero'){'-testplusarg M438_ZERO_EXTRA_LATENCY'}else{''}
  $taskArgs="-testplusarg UVM_VERBOSITY=UVM_NONE`n-testplusarg UVM_TESTNAME=m89x_runtime_kernel_test_lib`n-testplusarg UVM_TIMEOUT=20000000000000`n-sv_seed 356`n--noieeewarnings`n$taskSwitch`n-tclbatch run.tcl`n-log ${taskStem}.log`n"
  [IO.File]::WriteAllText((Join-Path $taskSim ($taskStem+'.args')),$taskArgs,[Text.UTF8Encoding]::new($false))
  & 'D:/AMDDesignTools/2026.1/Vivado/bin/xsim.bat' m441_trace -f ($taskStem+'.args') *> ($taskStem+'_console.log')
  $taskToolRc=$LASTEXITCODE
  $taskLog=Get-Content -LiteralPath ($taskStem+'.log') -Raw
  $taskDoneCount=[regex]::Matches($taskLog,'(?m)^M441_DONE cycles=').Count
  $taskRc=$taskToolRc
  if($taskRc -eq 0 -and ($taskDoneCount -ne 1 -or $taskLog -match '(?m)^(Fatal:|ERROR:)')){$taskRc=1}
  [IO.File]::WriteAllText((Join-Path $taskSim ($taskStem+'_exit.json')),("{`"simulation_rc`":$taskToolRc,`"gate_rc`":$taskRc}"),[Text.UTF8Encoding]::new($false))
  $taskSaved=Join-Path $taskSim ($taskStem+'_result')
  New-Item -ItemType Directory -Path $taskSaved|Out-Null
  Get-ChildItem (Join-Path $taskSim '../tv/rtldatafile') -File|ForEach-Object {Copy-Item -LiteralPath $_.FullName -Destination $taskSaved}
  if($taskRc -ne 0){throw "Simulation rc=$taskRc"}
  Write-Output ('M441_SIM_RETURN '+$Variant+' '+$Family+' '+$Mode+' rc=0')
 }
} finally {Pop-Location}
