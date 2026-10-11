param([ValidateSet('Compile','Random','Zero')][string]$Mode)
$ErrorActionPreference='Stop'
$taskRoot=(Resolve-Path (Join-Path $PSScriptRoot '../..')).Path
$taskSim=Join-Path $taskRoot 'tmp/m438_weight_wait_03/verilog'
$taskPython='C:/Users/30429/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/python.exe'
Push-Location $taskSim
try {
 if($Mode -eq 'Compile') {
  if(Test-Path 'm438_xelab.log'){throw 'Existing compilation; collect only'}
  & 'D:/AMDDesignTools/2026.1/Vivado/bin/xelab.bat' xil_defaultlib.apatb_m89x_runtime_kernel_top xil_defaultlib.glbl xil_defaultlib.m438_monitor -Oenable_linking_all_libraries -prj m438.prj -L smartconnect_v1_0 -L axi_protocol_checker_v1_1_12 -L axi_protocol_checker_v1_1_13 -L axis_protocol_checker_v1_1_11 -L axis_protocol_checker_v1_1_12 -L xil_defaultlib -L unisims_ver -L xpm -L floating_point_v7_1_22 -L floating_point_v7_0_27 -L uvm -relax -i ./svr -i ./axivip -i ./svtb -i ./file_agent -i ./m89x_runtime_kernel_subsystem -s m438_wait -log m438_xelab.log *> m438_compile_console.log
  $taskRc=$LASTEXITCODE
  [IO.File]::WriteAllText((Join-Path $taskSim 'm438_compile_exit.json'),("{`"compile_rc`":$taskRc}"),[Text.UTF8Encoding]::new($false))
  if($taskRc -ne 0){throw "Compile rc=$taskRc"}
  Write-Output 'M438_COMPILE_PASS'
 } else {
  if(!(Test-Path 'm438_compile_exit.json')){throw 'Compile evidence missing'}
  $taskCompile=Get-Content 'm438_compile_exit.json' -Raw|ConvertFrom-Json
  if($taskCompile.compile_rc -ne 0){throw 'Compile not passed'}
  $taskStem='m438_'+$Mode.ToLower()
  if(Test-Path ($taskStem+'_xsim.log')){throw 'Existing simulation; collect only'}
  if(Test-Path ($taskStem+'_result')){throw 'Saved result exists; collect only'}
  if($Mode -eq 'Zero' -and !(Test-Path 'm438_random_validated.json')){throw 'Random full-output adjudication must pass first'}
  $taskSwitch=if($Mode -eq 'Zero'){'-testplusarg M438_ZERO_EXTRA_LATENCY'}else{''}
  $taskArgs="-testplusarg UVM_VERBOSITY=UVM_NONE`n-testplusarg UVM_TESTNAME=m89x_runtime_kernel_test_lib`n-testplusarg UVM_TIMEOUT=20000000000000`n-sv_seed 356`n--noieeewarnings`n$taskSwitch`n-tclbatch m438_run.tcl`n-log ${taskStem}_xsim.log`n"
  [IO.File]::WriteAllText((Join-Path $taskSim ($taskStem+'.args')),$taskArgs,[Text.UTF8Encoding]::new($false))
  & 'D:/AMDDesignTools/2026.1/Vivado/bin/xsim.bat' m438_wait -f ($taskStem+'.args') *> ($taskStem+'_console.log')
  $taskRc=$LASTEXITCODE
  [IO.File]::WriteAllText((Join-Path $taskSim ($taskStem+'_exit.json')),("{`"simulation_rc`":$taskRc}"),[Text.UTF8Encoding]::new($false))
  # Each run owns a separate immutable snapshot of simulator-produced outputs.
  $taskSaved=Join-Path $taskSim ($taskStem+'_result')
  New-Item -ItemType Directory -Path $taskSaved|Out-Null
  Get-ChildItem (Join-Path $taskSim '../tv/rtldatafile') -File|ForEach-Object {Copy-Item -LiteralPath $_.FullName -Destination $taskSaved}
  if($taskRc -ne 0){throw "Simulation rc=$taskRc"}
  Write-Output ('M438_SIM_RETURN '+$Mode+' rc='+$taskRc)
 }
} finally {Pop-Location}
