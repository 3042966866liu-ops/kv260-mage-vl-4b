[CmdletBinding()]
param(
    [Parameter(Mandatory=$true)][string]$LocalPath,
    [Parameter(Mandatory=$true)][string]$RemotePath,
    [string]$Port = 'COM3',
    [string]$ExpectedFtdiSerial = 'XFL1PL5N11BJB',
    [string]$LogPrefix = 'tmp\m212_live_service\chunked_upload',
    [ValidateRange(256,2048)][int]$ChunkBytes = 1800,
    [int]$TimeoutSeconds = 45
)

$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest

$workspace = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
$source = (Resolve-Path -LiteralPath (Join-Path $workspace $LocalPath)).Path
if (-not ($RemotePath.StartsWith('/home/ubuntu/') -or $RemotePath.StartsWith('/tmp/') -or $RemotePath.StartsWith('/dev/shm/'))) {
    throw "Refusing to write outside approved board roots: $RemotePath"
}
if ($RemotePath.Contains("'")) { throw 'Single quotes are not supported in the remote path' }

$bytes = [System.IO.File]::ReadAllBytes($source)
$sha256 = (Get-FileHash -Algorithm SHA256 -LiteralPath $source).Hash.ToLowerInvariant()
$part = "$RemotePath.m212-part"
$commandTool = Join-Path $PSScriptRoot 'm75c_uart_command.ps1'

& $commandTool `
    -Command "python3 -c `"import pathlib; p=pathlib.Path('$part'); p.parent.mkdir(parents=True,exist_ok=True); p.write_bytes(b'')`"" `
    -Port $Port -ExpectedFtdiSerial $ExpectedFtdiSerial `
    -LogPath "${LogPrefix}_init.log" -TimeoutSeconds $TimeoutSeconds

$chunkCount = [Math]::Ceiling($bytes.Length / [double]$ChunkBytes)
for ($index = 0; $index -lt $chunkCount; $index++) {
    $offset = $index * $ChunkBytes
    $count = [Math]::Min($ChunkBytes, $bytes.Length - $offset)
    $chunk = [byte[]]::new($count)
    [Array]::Copy($bytes, $offset, $chunk, 0, $count)
    $encoded = [Convert]::ToBase64String($chunk)
    $ordinal = $index + 1
    & $commandTool `
        -Command "python3 -c `"import base64,pathlib; p=pathlib.Path('$part'); p.open('ab').write(base64.b64decode('$encoded')); print('M212_CHUNK_PASS',$ordinal,$chunkCount,p.stat().st_size)`"" `
        -Port $Port -ExpectedFtdiSerial $ExpectedFtdiSerial `
        -LogPath ("{0}_chunk_{1:D3}.log" -f $LogPrefix,$ordinal) -TimeoutSeconds $TimeoutSeconds
}

& $commandTool `
    -Command "python3 -c `"import hashlib,os,pathlib; p=pathlib.Path('$part'); q=pathlib.Path('$RemotePath'); got=hashlib.sha256(p.read_bytes()).hexdigest(); assert got=='$sha256',(got,'$sha256'); os.chmod(p,0o755); os.replace(p,q); print('M212_CHUNKED_FILE_PASS',q,q.stat().st_size,got)`"" `
    -Port $Port -ExpectedFtdiSerial $ExpectedFtdiSerial `
    -LogPath "${LogPrefix}_final.log" -TimeoutSeconds $TimeoutSeconds

Write-Output "M212_UART_CHUNKED_UPLOAD_PASS remote=$RemotePath bytes=$($bytes.Length) sha256=$sha256 chunks=$chunkCount"
