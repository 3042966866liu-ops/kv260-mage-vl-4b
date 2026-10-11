param([switch]$ResumeCosim)
$ErrorActionPreference='Stop'
$root='C:\Users\30429\Desktop\TeLLMe_FPGA_2026'
$created=$false
$existing=@((& C:\Windows\System32\subst.exe) | Where-Object {$_ -match '^\s*T:\\:'})
if($existing.Count){if(($existing -join '') -notlike "*$root*"){throw 'T drive belongs to another directory'}}
else { & C:\Windows\System32\subst.exe T: $root; if($LASTEXITCODE -ne 0){throw 'T mapping failed'}; $created=$true }
try {
    $tcl=if($ResumeCosim){'T:\hls\mage_decode_op01_one\resume_shapes_cosim.tcl'}else{'T:\hls\mage_decode_op01_one\run_shapes_rtl.tcl'}
    & (Join-Path $root 'scripts\run_vitis_hls_2026_1.cmd') --mode hls --tcl $tcl
    $toolExit=$LASTEXITCODE
    $report=Join-Path $root 'tmp\op01_decode_one_shapes\hls\sim\report\op01_decode_one_kernel_cosim.rpt'
    $log=Join-Path $root 'tmp\op01_decode_one_shapes\hls\sim\verilog\xsim.log'
    if((Get-Content $report -Raw) -notmatch 'Verilog\s*\|\s*Pass'){throw "Missing RTL Pass tool_exit=$toolExit"}
    if((Get-Content $log -Raw) -notmatch 'RTL Simulation\s*:\s*3\s*/\s*3'){throw 'Missing new three-transaction result'}
    Write-Output "OP01_SHAPES_RTL_REQUIRES_AUDIT tool_exit=$toolExit"
} finally {if($created){& C:\Windows\System32\subst.exe T: /D | Out-Null}}
