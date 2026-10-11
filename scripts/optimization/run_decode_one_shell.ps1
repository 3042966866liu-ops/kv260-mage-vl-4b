param([switch]$ResumeImplementation)
$ErrorActionPreference='Stop'
$root='C:\Users\30429\Desktop\TeLLMe_FPGA_2026'
$env:XILINXD_LICENSE_FILE='C:\Users\30429\Downloads\Xilinx.lic'
$env:XILINX_VIVADO='D:\AMDDesignTools\2026.1\Vivado'
$env:RDI_PLATFORM='win64'
$env:PATH="$env:XILINX_VIVADO\bin;$env:XILINX_VIVADO\lib\win64.o;$env:PATH"
$ip=Join-Path $root 'tmp\op01_decode_one_experimental_export\op01_decode_one_kernel.zip'
if((Get-FileHash -LiteralPath $ip).Hash -ne '4371F7C48B5B40E87BAB2780FEF6FC0ADC89409628688232425326C6C32B2E1F'){throw 'IP identity mismatch'}
$logs=Join-Path $root 'tmp\op01_d1_shell_logs'
if($ResumeImplementation){
    if(-not(Select-String -LiteralPath "$logs/create.log" -Pattern '^OP01_EXPERIMENTAL_M120_M89X2_PROJECT_CREATE_PASS$' -Quiet)){throw 'No verified candidate project'}
    $implLog="$logs/implementation02"
    if(Test-Path "$implLog.log"){throw 'Refuse repeating implementation02'}
} else {
    if(Test-Path -LiteralPath $logs){throw 'Refuse existing run logs'}
    New-Item -ItemType Directory -Path $logs | Out-Null
    $implLog="$logs/implementation"
}
$created=$false
$existing=@((& C:\Windows\System32\subst.exe) | Where-Object {$_ -match '^\s*T:\\:'})
if($existing.Count){
    if(($existing -join '') -notlike "*$root*"){throw 'T drive ownership mismatch'}
} else {
    & C:\Windows\System32\subst.exe T: $root
    if($LASTEXITCODE -ne 0){throw 'T drive mapping failed'}
    $created=$true
}
try {
    if(-not $ResumeImplementation){
    & "$env:XILINX_VIVADO\bin\vivado.bat" -mode batch -source T:/vivado/op01_decode_one_experimental/create_candidate_project.tcl -log "$logs/create.log" -journal "$logs/create.jou"
    if($LASTEXITCODE -ne 0){throw 'Create process failed'}
    if(-not(Select-String -LiteralPath "$logs/create.log" -Pattern '^OP01_EXPERIMENTAL_M120_M89X2_PROJECT_CREATE_PASS$' -Quiet)){throw 'Create marker missing'}
    }
    & "$env:XILINX_VIVADO\bin\vivado.bat" -mode batch -source T:/vivado/op01_decode_one_experimental/run_implementation.tcl -log "$implLog.log" -journal "$implLog.jou"
    if($LASTEXITCODE -ne 0){throw 'Implementation process failed'}
    if(-not(Select-String -LiteralPath "$implLog.log" -Pattern '^OP01_EXPERIMENTAL_BITSTREAM_CREATED ' -Quiet)){throw 'Bitstream completion marker missing'}
    Write-Output 'EXPERIMENTAL_SHELL_COMPLETE_REQUIRES_ARTIFACT_AUDIT'
} finally {
    if($created){& C:\Windows\System32\subst.exe T: /D | Out-Null}
}
