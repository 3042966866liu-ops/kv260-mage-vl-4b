[CmdletBinding()]
param()

$ErrorActionPreference = 'Stop'
$workspaceRoot = 'C:\Users\30429\Desktop\TeLLMe_FPGA_2026'
$vitisRun = 'D:\AMDDesignTools\2026.1\Vitis\bin\vitis-run.bat'
$tclScript = 'T:\hls\mage_prefill_m89x_runtime\run_export.tcl'
$substExe = 'C:\Windows\System32\subst.exe'
$createdMapping = $false

if (-not (Test-Path -LiteralPath $workspaceRoot -PathType Container)) {
    throw "M89X_EXPORT_WORKSPACE_NOT_FOUND path=$workspaceRoot"
}
if (-not (Test-Path -LiteralPath $vitisRun -PathType Leaf)) {
    throw "M89X_EXPORT_VITIS_NOT_FOUND path=$vitisRun"
}

$substLines = @(& $substExe 2>$null)
$existing = @($substLines | Where-Object { $_ -match '^\s*T:\\:' })
if ($existing.Count -gt 0) {
    $expected = "T:\: => $workspaceRoot"
    if (($existing -join "`n") -notlike "*$workspaceRoot*") {
        throw "M89X_EXPORT_T_DRIVE_IN_USE observed=$($existing -join ' ') expected=$expected"
    }
} else {
    & $substExe T: $workspaceRoot
    if ($LASTEXITCODE -ne 0) {
        throw "M89X_EXPORT_SUBST_CREATE_FAILED exit=$LASTEXITCODE"
    }
    $createdMapping = $true
}

try {
    if (-not (Test-Path -LiteralPath 'T:\AGENTS.md' -PathType Leaf)) {
        throw 'M89X_EXPORT_SUBST_IDENTITY_FAILED missing=T:\AGENTS.md'
    }
    $env:TELLME_WORKSPACE_ROOT = 'T:/'
    & $vitisRun --mode hls --tcl $tclScript
    if ($LASTEXITCODE -ne 0) {
        throw "M89X_EXPORT_VITIS_FAILED exit=$LASTEXITCODE"
    }
    $zip = 'T:\tmp\m89x_runtime_ip\m89x_runtime_kernel.zip'
    if (-not (Test-Path -LiteralPath $zip -PathType Leaf)) {
        throw "M89X_EXPORT_ZIP_MISSING path=$zip"
    }
    $hash = (Get-FileHash -Algorithm SHA256 -LiteralPath $zip).Hash.ToLowerInvariant()
    $length = (Get-Item -LiteralPath $zip).Length
    Write-Output "M89X1_IP_EXPORT_PASS zip=$zip bytes=$length sha256=$hash"
} finally {
    Remove-Item Env:TELLME_WORKSPACE_ROOT -ErrorAction SilentlyContinue
    if ($createdMapping) {
        & $substExe T: /D | Out-Null
        if ($LASTEXITCODE -ne 0) {
            Write-Warning "M89X_EXPORT_SUBST_REMOVE_FAILED exit=$LASTEXITCODE"
        }
    }
}
