param([ValidateSet('Compile','MaxFIFO','Timeout')][string]$Mode='Compile')
$ErrorActionPreference='Stop'
$taskRoot=Resolve-Path (Join-Path $PSScriptRoot '../..')
$taskSim=Join-Path $taskRoot 'tmp/m357_guarded_max_02/verilog'
$taskPrep=Join-Path $taskRoot 'deployment/mage_vl4b/optimization_v1/runs/M357-guarded-rtl-preparation-02/RESULT.json'
if((Get-FileHash -LiteralPath $taskPrep -Algorithm SHA256).Hash.ToLower() -ne '5f84b4ac57b137044d44acc79f5fab0dcde0badcd853b4f0869e38dcfb6ef6ce'){throw 'Preparation SHA mismatch'}
$taskSpec=Get-Content -LiteralPath $taskPrep -Encoding UTF8 -Raw | ConvertFrom-Json
foreach($row in $taskSpec.files){
  if((Get-FileHash -LiteralPath (Join-Path $taskRoot $row.path) -Algorithm SHA256).Hash.ToLower() -ne $row.sha256){throw "Input source SHA mismatch: $($row.path)"}
}
if($Mode -ne 'Compile'){
  $taskPrior=Join-Path $taskRoot 'deployment/mage_vl4b/optimization_v1/runs/M357-candidate-q-rtl-02/RESULT.json'
  if(-not (Test-Path $taskPrior)){throw 'Candidate full Q RTL evidence not completed'}
  $taskPriorSpec=Get-Content -LiteralPath $taskPrior -Encoding UTF8 -Raw | ConvertFrom-Json
  if($taskPriorSpec.status -ne 'PASS_FULL_FROZEN_Q_RTL'){throw 'Candidate full Q RTL rejected'}
  $taskPriorSha=(Get-FileHash -LiteralPath $taskPrior -Algorithm SHA256).Hash.ToLower()
  foreach($n in @('CURRENT_STATE.md','docsMILESTONES.md','deployment/mage_vl4b/BOARD_GATE_RESULT.json')){
    if(-not ([IO.File]::ReadAllText((Join-Path $taskRoot $n)).Contains($taskPriorSha))){throw "Prior evidence not synchronized: $n"}
  }
}
Push-Location $taskSim
try {
  if($Mode -eq 'Compile'){
    if(Test-Path m357_guarded_xelab.log){throw 'Existing compiled attempt; inspect only'}
    & 'D:/AMDDesignTools/2026.1/Vivado/bin/xelab.bat' xil_defaultlib.apatb_m89x_runtime_kernel_top xil_defaultlib.glbl xil_defaultlib.m357_trace_monitor xil_defaultlib.m357_rtl_watchdog -Oenable_linking_all_libraries -prj m357_guarded.prj -L smartconnect_v1_0 -L axi_protocol_checker_v1_1_12 -L axi_protocol_checker_v1_1_13 -L axis_protocol_checker_v1_1_11 -L axis_protocol_checker_v1_1_12 -L xil_defaultlib -L unisims_ver -L xpm -L floating_point_v7_1_22 -L floating_point_v7_0_27 -L uvm -relax -i ./svr -i ./axivip -i ./svtb -i ./file_agent -i ./m89x_runtime_kernel_subsystem -s m357_guarded -log m357_guarded_xelab.log *> m357_guarded_compile_console.log
    $taskRc=$LASTEXITCODE
    Get-Content m357_guarded_compile_console.log -Tail 8
    if($taskRc -ne 0){throw "Guarded compile failed rc=$taskRc"}
    [IO.File]::WriteAllText((Join-Path $taskSim 'm357_guarded_compile_exit.json'),("{`"compile_rc`":$taskRc}"),[Text.UTF8Encoding]::new($false))
    exit 0
  }
  if($Mode -eq 'Timeout'){
    $taskMax=Join-Path $taskRoot 'deployment/mage_vl4b/optimization_v1/runs/M357-max-fifo-rtl-01/RESULT.json'
    if(-not (Test-Path $taskMax)){throw 'Maximum FIFO gate not completed'}
    if((Get-Content $taskMax -Encoding UTF8 -Raw | ConvertFrom-Json).status -ne 'PASS_MAX_DESCRIPTOR_FIFO_RTL'){throw 'Maximum FIFO gate rejected'}
    throw 'Timeout must use independent fixture/result cwd; do not overwrite MaxFIFO outputs'
  }
  if(Test-Path m357_max_xsim.log){throw 'Existing maximum FIFO attempt; collect only'}
  $taskHoldPlan=Join-Path $taskRoot 'deployment/mage_vl4b/optimization_v1/runs/M357-max-axi-control-preparation-01/RESULT.json'
  if((Get-FileHash -LiteralPath $taskHoldPlan -Algorithm SHA256).Hash.ToLowerInvariant() -ne '429fc6f12b1684e064d322ab1aa587ec9a8d47abd1e1d7d117fd6bef3b7a056e'){throw 'AXI hold plan changed'}
  $taskHoldSpec=Get-Content $taskHoldPlan -Raw -Encoding UTF8 | ConvertFrom-Json
  $taskHoldTcl=Join-Path $taskRoot $taskHoldSpec.tcl_path
  if((Get-FileHash -LiteralPath $taskHoldTcl -Algorithm SHA256).Hash.ToLowerInvariant() -ne $taskHoldSpec.tcl_sha256){throw 'AXI hold Tcl changed'}
  $taskArgs=@'
-testplusarg UVM_VERBOSITY=UVM_NONE
-testplusarg UVM_TESTNAME=m89x_runtime_kernel_test_lib
-testplusarg UVM_TIMEOUT=20000000000000
-testplusarg M357_ZERO_EXTRA_LATENCY
-sv_seed 357
--noieeewarnings
-tclbatch m357_max_run.tcl
-log m357_max_xsim.log
'@
  $taskArgs=$taskArgs.Replace('m357_max_run.tcl',$taskHoldTcl.Replace('\','/'))
  [IO.File]::WriteAllText((Join-Path $taskSim 'm357_max.args'),$taskArgs,[Text.UTF8Encoding]::new($false))
  & 'D:/AMDDesignTools/2026.1/Vivado/bin/xsim.bat' m357_guarded -f m357_max.args *> m357_max_console.log
  $taskRc=$LASTEXITCODE
  Get-Content m357_max_console.log -Tail 18
  [IO.File]::WriteAllText((Join-Path $taskSim 'm357_max_exit.json'),("{`"simulation_rc`":$taskRc}"),[Text.UTF8Encoding]::new($false))
  if($taskRc -ne 0){throw "Maximum FIFO simulation failed rc=$taskRc"}
} finally {Pop-Location}
