[CmdletBinding()]
param()

$ErrorActionPreference = 'Stop'
$workspaceRoot = 'C:\Users\30429\Desktop\TeLLMe_FPGA_2026'
$launcher = Join-Path $workspaceRoot 'scripts\run_vitis_hls_2026_1.cmd'
$tclScript = 'T:\hls\mage_prefill_m89x_runtime\run_norm_qkv_pure_csim_tdrive.tcl'
$substExe = 'C:\Windows\System32\subst.exe'
$createdMapping = $false

if (-not (Test-Path -LiteralPath $launcher -PathType Leaf)) { throw "M89X1_PURE_CSIM_LAUNCHER_MISSING path=$launcher" }
$existing = @((& $substExe 2>$null) | Where-Object { $_ -match '^\s*T:\\:' })
if ($existing.Count -gt 0) {
    if (($existing -join "`n") -notlike "*$workspaceRoot*") { throw "M89X1_PURE_CSIM_T_DRIVE_IN_USE observed=$($existing -join ' ')" }
} else {
    & $substExe T: $workspaceRoot
    if ($LASTEXITCODE -ne 0) { throw "M89X1_PURE_CSIM_SUBST_CREATE_FAILED exit=$LASTEXITCODE" }
    $createdMapping = $true
}
try {
    cmd.exe /d /c "call scripts\run_vitis_hls_2026_1.cmd --mode hls --tcl $tclScript"
    if ($LASTEXITCODE -ne 0) { throw "M89X1_PURE_CSIM_FAILED exit=$LASTEXITCODE" }
    $output = 'T:\deployment\mage_vl4b\artifacts\m89x1_layer0_norm_qkv_hls_output.bin'
    if (-not (Test-Path -LiteralPath $output -PathType Leaf)) { throw "M89X1_PURE_CSIM_OUTPUT_MISSING path=$output" }
    $hash = (Get-FileHash -Algorithm SHA256 -LiteralPath $output).Hash.ToLowerInvariant()
    Write-Output "M89X1_PURE_CSIM_TDRIVE_PASS output_sha256=$hash"
} finally {
    if ($createdMapping) { & $substExe T: /D | Out-Null }
}
