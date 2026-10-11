$ErrorActionPreference='Stop'
$workspaceRoot='C:\Users\30429\Desktop\TeLLMe_FPGA_2026'
$fixture=Join-Path $workspaceRoot 'deployment\mage_vl4b\optimization_v1\runs\OP01-decode-one-real-fixture\real_gate_up.bin'
if((Get-FileHash -LiteralPath $fixture -Algorithm SHA256).Hash.ToLowerInvariant() -ne 'e4ec996a6c6cda9c0e890948258157bd9c77a98f95249a8435d8eae265fdef69'){throw 'Real fixture identity mismatch'}
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
    & (Join-Path $workspaceRoot 'scripts\run_vitis_hls_2026_1.cmd') --mode hls --tcl T:\hls\mage_decode_op01_one\run_real_csim.tcl
    $toolExit=$LASTEXITCODE
    $report=Join-Path $workspaceRoot 'tmp\op01_decode_one_real_csim\hls\csim\report\op01_decode_one_kernel_csim.log'
    if(-not(Test-Path -LiteralPath $report)){throw "Missing CSim report; tool exit $toolExit"}
    if((Get-Content -LiteralPath $report -Raw) -notmatch 'OP01_REAL_GATE_UP_CSIM_PASS words=311296 active_values=19456'){throw "Missing numerical pass marker; tool exit $toolExit"}
    Write-Output "OP01_REAL_GATE_UP_CSIM_REPORT_PASS tool_exit=$toolExit"
} finally {
    if($created){& C:\Windows\System32\subst.exe T: /D | Out-Null}
}
