$ErrorActionPreference='Stop'
$taskRoot=Resolve-Path (Join-Path $PSScriptRoot '../..')
$taskSim=Join-Path $taskRoot 'tmp/m356_stable_q_trace/verilog'
if(Test-Path (Join-Path $taskSim 'm356_xelab.log')){throw 'Existing run: collect/review only'}
Push-Location $taskSim
try {
  & 'D:/AMDDesignTools/2026.1/Vivado/bin/xelab.bat' xil_defaultlib.apatb_m89x_runtime_kernel_top xil_defaultlib.glbl xil_defaultlib.m356_trace_monitor -Oenable_linking_all_libraries -prj m89x_runtime_kernel.prj -L smartconnect_v1_0 -L axi_protocol_checker_v1_1_12 -L axi_protocol_checker_v1_1_13 -L axis_protocol_checker_v1_1_11 -L axis_protocol_checker_v1_1_12 -L xil_defaultlib -L unisims_ver -L xpm -L floating_point_v7_1_22 -L floating_point_v7_0_27 -L uvm -relax -i ./svr -i ./axivip -i ./svtb -i ./file_agent -i ./m89x_runtime_kernel_subsystem -s m356_stable_q -log m356_xelab.log
  $compileRc=$LASTEXITCODE
  if($compileRc -ne 0){throw "xelab failed rc=$compileRc"}
  & 'D:/AMDDesignTools/2026.1/Vivado/bin/xsim.bat' m356_stable_q -testplusarg 'UVM_VERBOSITY=UVM_NONE' -testplusarg 'UVM_TESTNAME=m89x_runtime_kernel_test_lib' -testplusarg 'UVM_TIMEOUT=20000000000000' -sv_seed 356 --noieeewarnings -tclbatch m356_run.tcl -log m356_xsim.log
  $simRc=$LASTEXITCODE
  [IO.File]::WriteAllText((Join-Path $taskSim 'm356_exit.json'),("{`"compile_rc`":$compileRc,`"simulation_rc`":$simRc}"),[Text.UTF8Encoding]::new($false))
  if($simRc -ne 0){throw "xsim failed rc=$simRc"}
} finally {Pop-Location}
