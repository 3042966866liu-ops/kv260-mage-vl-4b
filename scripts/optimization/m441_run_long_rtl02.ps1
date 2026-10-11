param([ValidateSet('A','B')][string]$Variant,[ValidateSet('gate_up','mlp_down','q')][string]$Family,[ValidateSet('Compile','Random','Zero')][string]$Mode)
$ErrorActionPreference='Stop'
$taskRoot=(Resolve-Path (Join-Path $PSScriptRoot '../..')).Path
$taskPrepPath=Join-Path $taskRoot ('deployment/mage_vl4b/optimization_v1/runs/M441-long-'+$Variant+'-'+$Family+'-RTL-preparation-02/RESULT.json')
$taskPrep=Get-Content -LiteralPath $taskPrepPath -Raw -Encoding UTF8|ConvertFrom-Json
if(-not $taskPrep.ARLEN_histogram_recorded -or $taskPrep.observer_revision -ne '02'){throw 'ARLEN observer revision not proven'}
if($taskPrep.variant -ne $Variant -or $taskPrep.family -ne $Family){throw 'Wrong frozen preparation'}
foreach($taskFile in $taskPrep.files){
 if((Get-FileHash -LiteralPath (Join-Path $taskRoot $taskFile.path) -Algorithm SHA256).Hash.ToLower() -ne $taskFile.sha256){throw ('Changed RTL input: '+$taskFile.path)}
}
$taskSHA=(Get-FileHash -LiteralPath $taskPrepPath -Algorithm SHA256).Hash.ToLower()
foreach($taskDoc in @('CURRENT_STATE.md','docsMILESTONES.md')){
 if(-not (Get-Content -LiteralPath (Join-Path $taskRoot $taskDoc) -Raw -Encoding UTF8).Contains($taskSHA)){throw 'Preparation not synchronized'}
}
$taskBoard=Get-Content -LiteralPath (Join-Path $taskRoot 'deployment/mage_vl4b/BOARD_GATE_RESULT.json') -Raw -Encoding UTF8|ConvertFrom-Json
$taskKey='latest_m441_long_'+$Variant+'_'+$Family+'_RTL_preparation02'
if($taskBoard.$taskKey.sha256 -ne $taskSHA){throw 'BOARD preparation SHA differs'}
$taskSim=Join-Path $taskRoot ('tmp/m441_long_'+$Variant+'_'+$Family+'_02/verilog')
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
  if($Mode -eq 'Random' -and !(Test-Path 'zero_validated.json')){throw 'Zero full-output gate must pass first'}
  $taskSwitch=if($Mode -eq 'Zero'){'-testplusarg M438_ZERO_EXTRA_LATENCY'}else{''}
  $taskArgs="-testplusarg UVM_VERBOSITY=UVM_NONE`n-testplusarg UVM_TESTNAME=m89x_runtime_kernel_test_lib`n-testplusarg UVM_TIMEOUT=20000000000000`n-sv_seed 356`n--noieeewarnings`n$taskSwitch`n-tclbatch run.tcl`n-log ${taskStem}.log`n"
  [IO.File]::WriteAllText((Join-Path $taskSim ($taskStem+'.args')),$taskArgs,[Text.UTF8Encoding]::new($false))
  & 'D:/AMDDesignTools/2026.1/Vivado/bin/xsim.bat' m441_trace -f ($taskStem+'.args') *> ($taskStem+'_console.log')
  $taskRc=$LASTEXITCODE
  [IO.File]::WriteAllText((Join-Path $taskSim ($taskStem+'_exit.json')),("{`"simulation_rc`":$taskRc}"),[Text.UTF8Encoding]::new($false))
  $taskSaved=Join-Path $taskSim ($taskStem+'_result')
  New-Item -ItemType Directory -Path $taskSaved|Out-Null
  Get-ChildItem (Join-Path $taskSim '../tv/rtldatafile') -File|ForEach-Object {Copy-Item -LiteralPath $_.FullName -Destination $taskSaved}
  if($taskRc -ne 0){throw "Simulation rc=$taskRc"}
  Write-Output ('M441_SIM_RETURN '+$Variant+' '+$Family+' '+$Mode+' rc=0')
 }
} finally {Pop-Location}
