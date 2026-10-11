param(
    [string]$BoardIp = "192.168.77.2",
    [string]$BoardUser = "ubuntu",
    [string]$SshKey = "tmp\m2_ssh\id_ed25519",
    [string]$BoardWebRoot = "/home/ubuntu/tellme_qwen25_3b_web",
    [string]$Timestamp = (Get-Date -Format "yyyyMMdd-HHmmss")
)

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

$workspace = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$candidate = Join-Path $workspace "deployment\qwen25_3b_web"
$sshKeyPath = (Resolve-Path (Join-Path $workspace $SshKey)).Path
$archive = Join-Path $workspace "tmp\qwen25_3b_web_$Timestamp.tar.gz"
New-Item -ItemType Directory -Path (Split-Path $archive) -Force | Out-Null

if ($BoardWebRoot -eq "/home/ubuntu/tellme_qwen25_3b/packetdf_candidate") {
    throw "Web candidate target must not be the stable 3B root"
}

$python = "C:\Users\30429\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe"
& $python -m py_compile `
    (Join-Path $candidate "server.py") `
    (Join-Path $candidate "runtime_adapter.py")
if ($LASTEXITCODE -ne 0) { throw "Web candidate Python compilation failed" }
& $python -m unittest discover -s (Join-Path $candidate "tests") -v
if ($LASTEXITCODE -ne 0) { throw "Web candidate host tests failed" }

Push-Location (Join-Path $workspace "deployment")
try {
    & tar.exe -czf $archive --exclude="__pycache__" --exclude="*.pyc" qwen25_3b_web
    if ($LASTEXITCODE -ne 0) { throw "Failed to create Web candidate archive" }
} finally {
    Pop-Location
}

$remoteArchive = "$BoardWebRoot/deployment_bundle_$Timestamp.tar.gz"
& ssh.exe -i $sshKeyPath -o BatchMode=yes -o ConnectTimeout=10 -o StrictHostKeyChecking=accept-new "$BoardUser@$BoardIp" "mkdir -p '$BoardWebRoot'"
if ($LASTEXITCODE -ne 0) { throw "Failed to create board Web candidate directory" }
& scp.exe -i $sshKeyPath -o BatchMode=yes -o ConnectTimeout=10 -o StrictHostKeyChecking=accept-new $archive "$BoardUser@${BoardIp}:$remoteArchive"
if ($LASTEXITCODE -ne 0) { throw "Failed to upload Web candidate archive" }
& ssh.exe -i $sshKeyPath -o BatchMode=yes -o ConnectTimeout=10 "$BoardUser@$BoardIp" "tar -xzf '$remoteArchive' --strip-components=1 -C '$BoardWebRoot' && printf 'WEB3B_DEPLOYED\n'"
if ($LASTEXITCODE -ne 0) { throw "Failed to extract Web candidate" }

Write-Output "WEB3B_DEPLOY_PASS"
Write-Output "BOARD_WEB_ROOT=$BoardWebRoot"
Write-Output "LOCAL_ARCHIVE=$archive"
Write-Output "REMOTE_ARCHIVE=$remoteArchive"
