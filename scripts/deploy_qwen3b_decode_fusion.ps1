param(
    [string]$BoardIp = "192.168.77.2",
    [string]$BoardUser = "ubuntu",
    [string]$SshKey = "tmp\m2_ssh\id_ed25519",
    [string]$BoardCandidateRoot = "/home/ubuntu/tellme_qwen25_3b/decode_fusion_candidate",
    [string]$Timestamp = (Get-Date -Format "yyyyMMdd-HHmmss")
)

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

$workspace = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$candidate = Join-Path $workspace "deployment\qwen25_3b_decode_fusion"
$sshKeyPath = (Resolve-Path (Join-Path $workspace $SshKey)).Path
$python = "C:\Users\30429\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe"
$archive = Join-Path $workspace "tmp\qwen25_3b_decode_fusion_$Timestamp.tar.gz"

& $python -m py_compile `
    (Join-Path $candidate "runtime\qwen_fpga_runtime.py") `
    (Join-Path $candidate "runtime\decode_equivalence.py") `
    (Join-Path $candidate "runtime\decode_profile.py")
if ($LASTEXITCODE -ne 0) { throw "Candidate Python compilation failed" }
& $python (Join-Path $candidate "runtime\decode_equivalence.py")
if ($LASTEXITCODE -ne 0) { throw "Candidate host equivalence failed" }

Push-Location (Join-Path $workspace "deployment")
try {
    & tar.exe -czf $archive --exclude="__pycache__" --exclude="*.pyc" qwen25_3b_decode_fusion
    if ($LASTEXITCODE -ne 0) { throw "Failed to create candidate archive" }
} finally {
    Pop-Location
}

$remoteArchive = "$BoardCandidateRoot/deployment_bundle_$Timestamp.tar.gz"
& ssh.exe -i $sshKeyPath -o BatchMode=yes -o ConnectTimeout=10 -o StrictHostKeyChecking=accept-new "$BoardUser@$BoardIp" "mkdir -p '$BoardCandidateRoot'"
if ($LASTEXITCODE -ne 0) { throw "Failed to create board candidate directory" }
& scp.exe -i $sshKeyPath -o BatchMode=yes -o ConnectTimeout=10 -o StrictHostKeyChecking=accept-new $archive "$BoardUser@${BoardIp}:$remoteArchive"
if ($LASTEXITCODE -ne 0) { throw "Failed to upload candidate archive" }
& ssh.exe -i $sshKeyPath -o BatchMode=yes -o ConnectTimeout=10 "$BoardUser@$BoardIp" "tar -xzf '$remoteArchive' --strip-components=1 -C '$BoardCandidateRoot' && cd '$BoardCandidateRoot/runtime/native' && make clean all && cd .. && PYTHONPATH=. /usr/local/share/pynq-venv/bin/python3 decode_equivalence.py"
if ($LASTEXITCODE -ne 0) { throw "Failed to extract/build board candidate" }

Write-Output "QWEN3B_DECODE_FUSION_DEPLOY_PASS"
Write-Output "BOARD_CANDIDATE_ROOT=$BoardCandidateRoot"
Write-Output "LOCAL_ARCHIVE=$archive"
Write-Output "REMOTE_ARCHIVE=$remoteArchive"
