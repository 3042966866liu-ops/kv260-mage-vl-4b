$ErrorActionPreference='Stop'
$taskRoot=Resolve-Path (Join-Path $PSScriptRoot '../..')
$taskSim=Join-Path $taskRoot 'tmp/m357_candidate_q_trace/verilog'
if(Test-Path (Join-Path $taskSim 'm357_xelab.log')){throw 'Existing run: inspect only'}
$taskArgs=@'
-testplusarg UVM_VERBOSITY=UVM_NONE
-testplusarg UVM_TESTNAME=m89x_runtime_kernel_test_lib
-testplusarg UVM_TIMEOUT=20000000000000
-sv_seed 356
--noieeewarnings
-tclbatch m357_run.tcl
-log m357_xsim.log
'@
[IO.File]::WriteAllText((Join-Path $taskSim 'm357_xsim.args'),$taskArgs,[Text.UTF8Encoding]::new($false))
Push-Location $taskSim
try {
  & 'D:/AMDDesignTools/2026.1/Vivado/bin/xelab.bat' xil_defaultlib.apatb_m89x_runtime_kernel_top xil_defaultlib.glbl xil_defaultlib.m357_trace_monitor -Oenable_linking_all_libraries -prj m357.prj -L smartconnect_v1_0 -L axi_protocol_checker_v1_1_12 -L axi_protocol_checker_v1_1_13 -L axis_protocol_checker_v1_1_11 -L axis_protocol_checker_v1_1_12 -L xil_defaultlib -L unisims_ver -L xpm -L floating_point_v7_1_22 -L floating_point_v7_0_27 -L uvm -relax -i ./svr -i ./axivip -i ./svtb -i ./file_agent -i ./m89x_runtime_kernel_subsystem -s m357_q -log m357_xelab.log
  $compileRc=$LASTEXITCODE
  if($compileRc -ne 0){throw "xelab failed rc=$compileRc"}
  & 'D:/AMDDesignTools/2026.1/Vivado/bin/xsim.bat' m357_q -f m357_xsim.args
  $simRc=$LASTEXITCODE
  $taskLog=[IO.File]::ReadAllText((Join-Path $taskSim 'm357_xsim.log'))
  $taskEngineError=$taskLog -match 'ERROR:|necessary license|failed to start'
  [IO.File]::WriteAllText((Join-Path $taskSim 'm357_exit.json'),("{`"compile_rc`":$compileRc,`"simulation_rc`":$simRc,`"engine_error`":"+$taskEngineError.ToString().ToLower()+"}"),[Text.UTF8Encoding]::new($false))
  if($simRc -ne 0 -or $taskEngineError){throw "xsim failed rc=$simRc engine_error=$taskEngineError"}
} finally {Pop-Location}
