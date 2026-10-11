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
    & (Join-Path $workspaceRoot 'scripts\run_vitis_hls_2026_1.cmd') --mode hls --tcl T:\hls\mage_decode_op01_one\run_boundary_csim.tcl
    $toolExit=$LASTEXITCODE
    $report=Join-Path $workspaceRoot 'tmp\op01_decode_one_boundary_csim_02\hls\csim\report\op01_decode_one_kernel_csim.log'
    if(-not(Test-Path -LiteralPath $report)){throw "Missing CSim report; tool exit $toolExit"}
    if((Get-Content -LiteralPath $report -Raw) -notmatch 'OP01_BOUNDARY_NUMERICAL_PASS'){throw "Missing numerical pass marker; tool exit $toolExit"}
    Write-Output "OP01_BOUNDARY_CSIM_REPORT_PASS tool_exit=$toolExit"
} finally {
    if($created){& C:\Windows\System32\subst.exe T: /D | Out-Null}
}
