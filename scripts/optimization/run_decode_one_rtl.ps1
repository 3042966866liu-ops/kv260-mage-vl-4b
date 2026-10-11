$ErrorActionPreference='Stop'
$workspaceRoot='C:\Users\30429\Desktop\TeLLMe_FPGA_2026'
$created=$false
$existing=@((& C:\Windows\System32\subst.exe) | Where-Object {$_ -match '^\s*T:\\:'})
if($existing.Count){
    if(($existing -join '') -notlike "*$workspaceRoot*"){throw 'T drive belongs to another directory'}
} else {
    & C:\Windows\System32\subst.exe T: $workspaceRoot
    if($LASTEXITCODE -ne 0){throw 'T mapping failed'}
    $created=$true
}
try {
    & (Join-Path $workspaceRoot 'scripts\run_vitis_hls_2026_1.cmd') --mode hls --tcl T:\hls\mage_decode_op01_one\run_rtl.tcl
    $toolExit=$LASTEXITCODE
    $report=Join-Path $workspaceRoot 'tmp\op01_decode_one_rtl\hls\sim\report\op01_decode_one_kernel_cosim.rpt'
    if(-not(Test-Path -LiteralPath $report)){throw "Missing RTL report; tool exit $toolExit"}
    if((Get-Content -LiteralPath $report -Raw) -notmatch 'Verilog\s*\|\s*Pass'){throw "RTL report not Pass; tool exit $toolExit"}
    Write-Output "OP01_RTL_REPORT_REQUIRES_AUDIT tool_exit=$toolExit"
} finally {
    if($created){& C:\Windows\System32\subst.exe T: /D | Out-Null}
}
