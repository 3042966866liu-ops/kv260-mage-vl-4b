$ErrorActionPreference='Stop'
$taskRoot=Resolve-Path (Join-Path $PSScriptRoot '../..')
$taskSim=Join-Path $taskRoot 'tmp/m356_stable_q_trace/verilog'
if(Test-Path (Join-Path $taskSim 'm356_xsim_02.log')){throw 'Existing simulation: review/collect only'}
if(Test-Path (Join-Path $taskSim 'm356_trace.csv')){throw 'Simulation already started; do not repeat'}
$taskArgs=@'
-testplusarg UVM_VERBOSITY=UVM_NONE
-testplusarg UVM_TESTNAME=m89x_runtime_kernel_test_lib
-testplusarg UVM_TIMEOUT=20000000000000
-sv_seed 356
--noieeewarnings
-tclbatch m356_run.tcl
-log m356_xsim_02.log
'@
[IO.File]::WriteAllText((Join-Path $taskSim 'm356_xsim.args'),$taskArgs,[Text.UTF8Encoding]::new($false))
Push-Location $taskSim
try {
  & 'D:/AMDDesignTools/2026.1/Vivado/bin/xsim.bat' m356_stable_q -f m356_xsim.args
  $taskRc=$LASTEXITCODE
  [IO.File]::WriteAllText((Join-Path $taskSim 'm356_exit_02.json'),("{`"simulation_rc`":$taskRc}"),[Text.UTF8Encoding]::new($false))
  if($taskRc -ne 0){throw "xsim failed rc=$taskRc"}
} finally {Pop-Location}
