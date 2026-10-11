[CmdletBinding()]
param()

$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest

$workspace = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
$stateRoot = Join-Path $workspace 'tmp\m256_public'
$pidFile = Join-Path $stateRoot 'cloudflared.pid'
$urlFile = Join-Path $stateRoot 'public_url.txt'

if (-not (Test-Path -LiteralPath $pidFile -PathType Leaf)) {
    Write-Output 'M256_TUNNEL_NOT_RUNNING'
    exit 0
}

$tunnelPid = [int](Get-Content -Raw -LiteralPath $pidFile)
$process = Get-Process -Id $tunnelPid -ErrorAction SilentlyContinue
if ($process) {
    if ($process.ProcessName -ne 'cloudflared') {
        throw "Refusing to stop PID $tunnelPid because it is $($process.ProcessName), not cloudflared"
    }
    Stop-Process -Id $tunnelPid -Force
    $process.WaitForExit(10000)
}

Remove-Item -LiteralPath $pidFile,$urlFile -Force -ErrorAction SilentlyContinue
Write-Output 'M256_M255_PUBLIC_TUNNEL_STOPPED'
