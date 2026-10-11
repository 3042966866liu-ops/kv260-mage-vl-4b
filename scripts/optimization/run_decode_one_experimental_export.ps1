$ErrorActionPreference='Stop'
$workspaceRoot='C:\Users\30429\Desktop\TeLLMe_FPGA_2026'
$licensePath='C:\Users\30429\Downloads\Xilinx.lic'
if(-not(Test-Path -LiteralPath $licensePath)){throw 'Recorded license file missing'}
$env:XILINXD_LICENSE_FILE=$licensePath
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
    & (Join-Path $workspaceRoot 'scripts\run_vitis_hls_2026_1.cmd') --mode hls --tcl T:\hls\mage_decode_op01_one\export_experimental_ip.tcl
    $rc=$LASTEXITCODE
    if($rc -ne 0){throw "Experimental IP export failed: $rc"}
    $zip=Join-Path $workspaceRoot 'tmp\op01_decode_one_experimental_export\op01_decode_one_kernel.zip'
    if(-not(Test-Path -LiteralPath $zip)){throw 'Missing exported IP archive'}
    Get-FileHash -LiteralPath $zip -Algorithm SHA256
    Write-Output 'EXPERIMENTAL_IP_EXPORT_FINISHED_REQUIRES_AUDIT'
} finally {
    if($created){& C:\Windows\System32\subst.exe T: /D | Out-Null}
}
