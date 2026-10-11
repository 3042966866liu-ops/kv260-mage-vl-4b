param([ValidateSet('candidate_w2','baseline_w4','candidate_w4')][string]$Tag,[ValidateSet('Compile','Random','Zero')][string]$Mode)
$ErrorActionPreference='Stop'
$taskRoot=(Resolve-Path (Join-Path $PSScriptRoot '../..')).Path
$taskSim=Join-Path $taskRoot ('tmp/m439_'+$Tag+'_02/verilog')
Push-Location $taskSim
try {
 if($Mode -eq 'Compile') {
  if(Test-Path 'compile.log'){throw 'Existing compile: collect only'}
  & 'D:/AMDDesignTools/2026.1/Vivado/bin/xelab.bat' xil_defaultlib.apatb_m89x_runtime_kernel_top xil_defaultlib.glbl xil_defaultlib.m439_monitor -Oenable_linking_all_libraries -prj m439.prj -L smartconnect_v1_0 -L axi_protocol_checker_v1_1_12 -L axi_protocol_checker_v1_1_13 -L axis_protocol_checker_v1_1_11 -L axis_protocol_checker_v1_1_12 -L xil_defaultlib -L unisims_ver -L xpm -L floating_point_v7_1_22 -L floating_point_v7_0_27 -L uvm -relax -i ./svr -i ./axivip -i ./svtb -i ./file_agent -i ./m89x_runtime_kernel_subsystem -s m439_trace -log compile.log *> compile_console.log
  $taskRc=$LASTEXITCODE
  [IO.File]::WriteAllText((Join-Path $taskSim 'compile_exit.json'),("{`"compile_rc`":$taskRc}"),[Text.UTF8Encoding]::new($false))
  if($taskRc -ne 0){throw "Compile rc=$taskRc"}
  Write-Output ('M439_COMPILE_RETURN '+$Tag+' rc=0')
 } else {
  if(!(Test-Path 'compile_validated.json')){throw 'Compile not adjudicated'}
  $taskStem=$Mode.ToLower()
  if(Test-Path ($taskStem+'.log')){throw 'Existing run: collect only'}
  if(Test-Path ($taskStem+'_result')){throw 'Existing saved result: collect only'}
  if($Mode -eq 'Random' -and !(Test-Path 'zero_validated.json')){throw 'Zero exact-output gate must pass first'}
  $taskSwitch=if($Mode -eq 'Zero'){'-testplusarg M438_ZERO_EXTRA_LATENCY'}else{''}
  $taskArgs="-testplusarg UVM_VERBOSITY=UVM_NONE`n-testplusarg UVM_TESTNAME=m89x_runtime_kernel_test_lib`n-testplusarg UVM_TIMEOUT=20000000000000`n-sv_seed 356`n--noieeewarnings`n$taskSwitch`n-tclbatch run.tcl`n-log ${taskStem}.log`n"
  [IO.File]::WriteAllText((Join-Path $taskSim ($taskStem+'.args')),$taskArgs,[Text.UTF8Encoding]::new($false))
  & 'D:/AMDDesignTools/2026.1/Vivado/bin/xsim.bat' m439_trace -f ($taskStem+'.args') *> ($taskStem+'_console.log')
  $taskRc=$LASTEXITCODE
  [IO.File]::WriteAllText((Join-Path $taskSim ($taskStem+'_exit.json')),("{`"simulation_rc`":$taskRc}"),[Text.UTF8Encoding]::new($false))
  $taskSaved=Join-Path $taskSim ($taskStem+'_result')
  New-Item -ItemType Directory -Path $taskSaved|Out-Null
  Get-ChildItem (Join-Path $taskSim '../tv/rtldatafile') -File|ForEach-Object {Copy-Item -LiteralPath $_.FullName -Destination $taskSaved}
  if($taskRc -ne 0){throw "Simulation rc=$taskRc"}
  Write-Output ('M439_SIM_RETURN '+$Tag+' '+$Mode+' rc=0')
 }
} finally {Pop-Location}
