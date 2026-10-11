[CmdletBinding()]
param()

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

$Workspace = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot '..')).Path
$NodeExe = 'C:\Users\30429\.cache\codex-runtimes\codex-primary-runtime\dependencies\node\bin\node.exe'
$PythonExe = 'C:\Users\30429\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe'
$Importer = Join-Path $Workspace 'scripts\m304_import_human_review_workbook.mjs'
$Evaluator = Join-Path $Workspace 'scripts\m308_run_one_shot_bact_evaluation.py'
$Finalizer = Join-Path $Workspace 'scripts\m309_generate_bact_final_evidence_pack.py'
$M304ResultPath = Join-Path $Workspace 'deployment\mage_vl4b\M304_HUMAN_REVIEW_IMPORT_RESULT.json'
$M308ResultPath = Join-Path $Workspace 'deployment\mage_vl4b\M308_BACT_HELDOUT_EVALUATION_RESULT.json'
$M308SealPath = Join-Path $Workspace 'deployment\mage_vl4b\M308_BACT_HELDOUT_EVALUATION_SEAL.json'
$M309ResultPath = Join-Path $Workspace 'deployment\mage_vl4b\M309_BACT_FINAL_EVIDENCE_PACK_RESULT.json'

foreach ($RequiredPath in @($NodeExe, $PythonExe, $Importer, $Evaluator, $Finalizer)) {
    if (-not (Test-Path -LiteralPath $RequiredPath -PathType Leaf)) {
        throw "M310_REQUIRED_FILE_MISSING path=$RequiredPath"
    }
}

if (Test-Path -LiteralPath $M308SealPath -PathType Leaf) {
    $ExistingSeal = Get-Content -LiteralPath $M308SealPath -Raw | ConvertFrom-Json
    if ($ExistingSeal.status -ne 'COMPLETE') {
        throw 'M310_M308_INCOMPLETE_OPEN_SEAL: held-out labels were opened but the run did not complete; do not rerun or retune automatically.'
    }
}

Write-Output 'M310_STAGE_BEGIN stage=M304-human-review-import'
& $NodeExe $Importer --workspace $Workspace
if ($LASTEXITCODE -ne 0) {
    throw "M310_M304_IMPORT_BLOCKED exit=$LASTEXITCODE. Finish all 12 workbook rows and coverage conditions; M308 was not started."
}
$M304 = Get-Content -LiteralPath $M304ResultPath -Raw | ConvertFrom-Json
if ($M304.status -ne 'PASS_HUMAN_LABELS_AND_CONDITIONS_FROZEN' -or
    $M304.labelsWritten -ne $true -or
    [int]$M304.qcPassCount -ne 12 -or
    [int]$M304.pendingCount -ne 0) {
    throw 'M310_M304_RESULT_CONTRACT_FAIL'
}
Write-Output "M310_STAGE_PASS stage=M304-human-review-import labels_sha256=$($M304.labelsSha256)"

Write-Output 'M310_STAGE_BEGIN stage=M308-one-shot-held-out-evaluation'
& $PythonExe $Evaluator --workspace $Workspace
if ($LASTEXITCODE -ne 0) {
    throw "M310_M308_EVALUATION_FAIL exit=$LASTEXITCODE"
}
$M308 = Get-Content -LiteralPath $M308ResultPath -Raw | ConvertFrom-Json
$M308Seal = Get-Content -LiteralPath $M308SealPath -Raw | ConvertFrom-Json
if ($M308.status -ne 'PASS_PILOT_HELDOUT_EVALUATION_SEALED' -or
    $M308Seal.status -ne 'COMPLETE') {
    throw 'M310_M308_RESULT_OR_SEAL_CONTRACT_FAIL'
}
$M308Hash = (Get-FileHash -Algorithm SHA256 -LiteralPath $M308ResultPath).Hash.ToLowerInvariant()
if ($M308Hash -ne $M308Seal.resultSha256) {
    throw 'M310_M308_RESULT_HASH_MISMATCH'
}
Write-Output "M310_STAGE_PASS stage=M308-one-shot-held-out-evaluation result_sha256=$M308Hash"

Write-Output 'M310_STAGE_BEGIN stage=M309-final-evidence-pack'
& $PythonExe $Finalizer --workspace $Workspace
if ($LASTEXITCODE -ne 0) {
    throw "M310_M309_FINAL_PACK_FAIL exit=$LASTEXITCODE"
}
$M309 = Get-Content -LiteralPath $M309ResultPath -Raw | ConvertFrom-Json
if ($M309.status -ne 'PASS_FINAL_PILOT_EVIDENCE_PACK') {
    throw 'M310_M309_RESULT_CONTRACT_FAIL'
}
Write-Output "M310_STAGE_PASS stage=M309-final-evidence-pack report_sha256=$($M309.reportSha256) claims_sha256=$($M309.claimsSha256)"
Write-Output 'M310_BACT_POST_LABEL_PIPELINE_PASS next=sync-authoritative-state'
