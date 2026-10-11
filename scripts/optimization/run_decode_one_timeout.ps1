$ErrorActionPreference='Stop'
$root='C:\Users\30429\Desktop\TeLLMe_FPGA_2026'
$dest=Join-Path $root 'tmp\op01_decode_one_timeout'
$manifest=Get-Content (Join-Path $dest 'PREPARATION.json') -Raw | ConvertFrom-Json
$tb=Join-Path $dest 'verilog\op01_decode_one_kernel.autotb.v'
if((Get-FileHash $tb -Algorithm SHA256).Hash.ToLowerInvariant() -ne $manifest.modified_tb_sha256){throw 'Timeout testbench identity mismatch'}
Push-Location (Join-Path $dest 'verilog')
try {
    & .\run_timeout.cmd
    $simExit=$LASTEXITCODE
    $log=Get-Content .\xsim.log -Raw
    if($simExit -eq 0){throw 'Expected nonzero simulator exit for bounded timeout'}
    if($log -notmatch 'OP01_WATCHDOG_ARMED start_cnt=1' -or $log -notmatch 'OP01_RTL_TIMEOUT_TRIGGERED finish_cnt=0 total=4' -or $log -notmatch 'Fatal: OP01 bounded timeout expired before ap_done'){throw 'Missing expected timeout evidence'}
    if($log -match 'OP01 negative test invalid' -or $log -match 'RTL Simulation\s*:\s*4\s*/\s*4'){throw 'Invalid timeout negative result'}
    Write-Output "OP01_TIMEOUT_EXPECTED_FAILURE_CONFIRMED simulator_exit=$simExit"
} finally { Pop-Location }
