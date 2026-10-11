param(
    [Parameter(Mandatory=$true)][string]$LocalPath,
    [Parameter(Mandatory=$true)][string]$RemotePath,
    [string]$Port = 'COM3',
    [string]$ExpectedFtdiSerial = 'XFL1PL5N11BJB',
    [string]$LogPath = 'tmp\m75c_full_layout\put_file_uart.log',
    [int]$TimeoutSeconds = 120,
    [switch]$UseSudo
)

$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest

$workspace = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
$source = (Resolve-Path -LiteralPath (Join-Path $workspace $LocalPath)).Path
$remote = $RemotePath.Replace("'", "'\''")

if (-not ($RemotePath.StartsWith('/home/ubuntu/') -or $RemotePath.StartsWith('/tmp/') -or $RemotePath.StartsWith('/dev/shm/'))) {
    throw "Refusing to write outside /home/ubuntu, /tmp, or /dev/shm: $RemotePath"
}

$bytes = [System.IO.File]::ReadAllBytes($source)
$b64 = [Convert]::ToBase64String($bytes)
$py = "import base64,pathlib,os; p=pathlib.Path('$remote'); p.parent.mkdir(parents=True,exist_ok=True); p.write_bytes(base64.b64decode('$b64')); os.chmod(p,0o755); print('M75C_UART_PUT_FILE_PASS', str(p), p.stat().st_size)"
$command = "python3 -c `"$py`""
if ($UseSudo) {
    $command = "sudo -n " + $command
}

& (Join-Path $PSScriptRoot 'm75c_uart_command.ps1') `
    -Command $command `
    -Port $Port `
    -ExpectedFtdiSerial $ExpectedFtdiSerial `
    -LogPath $LogPath `
    -TimeoutSeconds $TimeoutSeconds
