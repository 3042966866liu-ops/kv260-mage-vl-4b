param(
    [string]$Port = 'COM3',
    [string]$ExpectedFtdiSerial = 'XFL1PL5N11BJB',
    [int]$TimeoutSeconds = 90,
    [switch]$RequireExistingShell,
    [ValidateSet('qkv-tolerance', 'layer0-diagnostic')][string]$Profile = 'qkv-tolerance'
)

$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest

$workspace = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
$uploads = switch ($Profile) {
    'qkv-tolerance' {
        @(
            @{ Local = 'scripts\m89x1_qkv_tolerance_gate.py'; Remote = '/home/ubuntu/tellme_m89x1_qkv_20260831/m89x_board_candidate/runtime/m89x1_qkv_tolerance_gate.py' },
            @{ Local = 'scripts\run_m89x1_qkv_tolerance_gate.sh'; Remote = '/home/ubuntu/tellme_m89x1_qkv_20260831/m89x_board_candidate/runtime/run_m89x1_qkv_tolerance_gate.sh' }
        )
    }
    'layer0-diagnostic' {
        @(
            @{ Local = 'scripts\m89x1_layer0_tolerance_diagnostic.py'; Remote = '/home/ubuntu/tellme_m89x1_qkv_20260831/m89x_board_candidate/runtime/m89x1_layer0_tolerance_diagnostic.py' },
            @{ Local = 'scripts\run_m89x1_layer0_tolerance_diagnostic.sh'; Remote = '/home/ubuntu/tellme_m89x1_qkv_20260831/m89x_board_candidate/runtime/run_m89x1_layer0_tolerance_diagnostic.sh' }
        )
    }
}
$logPath = Join-Path $workspace 'tmp\m89x1_qkv_tolerance_authenticated_upload_uart.log'
New-Item -ItemType Directory -Force -Path (Split-Path $logPath) | Out-Null
Set-Content -LiteralPath $logPath -Value '' -Encoding utf8

$device = Get-CimInstance Win32_PnPEntity | Where-Object { $_.Name -match "\($([regex]::Escape($Port))\)$" }
if (-not $device) { throw "Serial port $Port is not present" }
if ($ExpectedFtdiSerial -and $device.PNPDeviceID -notmatch [regex]::Escape($ExpectedFtdiSerial)) {
    throw "Serial port $Port does not match expected FTDI serial $ExpectedFtdiSerial"
}

function Read-Until {
    param([System.IO.Ports.SerialPort]$Serial, [string]$Pattern, [int]$Seconds)
    $deadline = [DateTime]::UtcNow.AddSeconds($Seconds)
    $captured = [System.Text.StringBuilder]::new()
    while ([DateTime]::UtcNow -lt $deadline) {
        $chunk = $Serial.ReadExisting()
        if ($chunk.Length -gt 0) {
            [void]$captured.Append($chunk)
            [System.IO.File]::AppendAllText($logPath, $chunk)
            Write-Host -NoNewline $chunk
            if ($captured.ToString() -match $Pattern) { return $captured.ToString() }
        }
        Start-Sleep -Milliseconds 100
    }
    throw "Timed out waiting for serial pattern: $Pattern"
}

$serial = [System.IO.Ports.SerialPort]::new($Port, 115200, [System.IO.Ports.Parity]::None, 8, [System.IO.Ports.StopBits]::One)
$serial.Handshake = [System.IO.Ports.Handshake]::None
$serial.Encoding = [Text.Encoding]::UTF8
$serial.NewLine = "`n"
$serial.ReadTimeout = 250
$serial.WriteTimeout = 3000

try {
    $serial.Open()
    $serial.Write("`n")
    $initial = Read-Until -Serial $serial -Pattern '(login:|ubuntu@kria:.*[$#])' -Seconds 8
    if ($initial -match 'login:') {
        if ($RequireExistingShell) {
            throw 'KV260 is at login prompt; no upload attempted because an existing authenticated shell was required.'
        }
        $password = Read-Host 'KV260 ubuntu password (not stored or logged)' -AsSecureString
        $serial.WriteLine('ubuntu')
        [void](Read-Until -Serial $serial -Pattern '(?i)password:' -Seconds 8)
        $bstr = [Runtime.InteropServices.Marshal]::SecureStringToBSTR($password)
        try {
            $plain = [Runtime.InteropServices.Marshal]::PtrToStringBSTR($bstr)
            $serial.WriteLine($plain)
        } finally {
            [Runtime.InteropServices.Marshal]::ZeroFreeBSTR($bstr)
        }
        [void](Read-Until -Serial $serial -Pattern 'ubuntu@kria:.*[$#]' -Seconds 15)
    }

    $index = 0
    foreach ($upload in $uploads) {
        $source = Join-Path $workspace $upload.Local
        if (-not (Test-Path -LiteralPath $source)) { throw "missing local source: $source" }
        $bytes = [System.IO.File]::ReadAllBytes($source)
        $b64 = [Convert]::ToBase64String($bytes)
        $sha = (Get-FileHash -LiteralPath $source -Algorithm SHA256).Hash.ToLower()
        $remote = $upload.Remote.Replace("'", "'\''")
        $py = "import base64,hashlib,pathlib,os; d=base64.b64decode('$b64'); p=pathlib.Path('$remote'); p.parent.mkdir(parents=True,exist_ok=True); p.write_bytes(d); os.chmod(p,0o755); got=hashlib.sha256(p.read_bytes()).hexdigest(); assert got=='$sha',(got,'$sha'); print('M89X1_AUTH_PUT_PASS',p,got)"
        $marker = "__M89X1_AUTH_UPLOAD_${index}_RC_"
        $wrapped = "python3 -c `"$py`"; rc=`$?; echo ${marker}`${rc}__"
        $serial.WriteLine($wrapped)
        $output = Read-Until -Serial $serial -Pattern ([regex]::Escape($marker) + '(\d+)__') -Seconds $TimeoutSeconds
        $match = [regex]::Match($output, [regex]::Escape($marker) + '(\d+)__')
        if (-not $match.Success -or [int]$match.Groups[1].Value -ne 0) { throw "upload failed for $($upload.Local)" }
        $index++
    }
    Write-Output 'M89X1_AUTHENTICATED_UPLOAD_PASS files=2'
} finally {
    if ($serial.IsOpen) { $serial.Close() }
    $serial.Dispose()
}
