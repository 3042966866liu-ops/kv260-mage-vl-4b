<#
Copies the already-created, hash-locked Mage-VL M56 artifact from WSL into the
Windows workspace for *offline* M89 integration. It invokes `wsl.exe` rather
than relying on the optional `\\wsl.localhost` file share, which can be denied
by Windows even when the WSL distribution itself is healthy. It never contacts
KV260 or changes boot/DTB/CMA/service/bitstream state.

Use from PowerShell (the helper automatically selects one installed Ubuntu
distribution):
  powershell -ExecutionPolicy Bypass -File .\scripts\m89_stage_m56_from_wsl.ps1

If the WSL distribution has another name:
  powershell -ExecutionPolicy Bypass -File .\scripts\m89_stage_m56_from_wsl.ps1 -Distro <name>
#>
[CmdletBinding()]
param(
    [string]$Distro = '',
    [switch]$CheckOnly
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

$expectedBlobHash = '24774ce383eb8261257942bb2a7a565d75fa3961754905973759d8e58ac24e4f'
$expectedManifestHash = '3e2cdcbc492dd709974aac28cfa1fe5fef5f08003f5cedefd9c71c74afe05170'
$expectedBlobBytes = [int64]2181949312
$expectedLanguageEntries = 252
# `Split-Path -LiteralPath ... -Parent` is ambiguous in Windows PowerShell
# 5.1.  Use the .NET path API so this helper works in both Windows PowerShell
# and PowerShell 7 before it touches the source artifact.
$projectRoot = [System.IO.Directory]::GetParent($PSScriptRoot).FullName
$sourceUnix = '/home/lyy/artifacts/tellme-mage-vl/m56-full-exhaustive-packed-fp16'
$destinationParent = Join-Path $projectRoot 'deployment\mage_vl4b\artifacts'
$destination = Join-Path $destinationParent 'm56-full-exhaustive-packed-fp16'

function Invoke-WslChecked {
    param([Parameter(Mandatory = $true)][string[]]$Arguments)

    # WSL can emit the non-fatal localhost-proxy warning on stderr while
    # returning exit code 0.  With the script's global Stop preference that
    # warning otherwise becomes a terminating NativeCommandError.  Capture it
    # under Continue, discard it only after an explicit zero exit status, and
    # retain it in the error message for a genuine WSL failure.
    $previousErrorActionPreference = $ErrorActionPreference
    try {
        $ErrorActionPreference = 'Continue'
        $allOutput = @(& wsl.exe -d $Distro -- @Arguments 2>&1)
        $nativeExitCode = $LASTEXITCODE
    }
    finally {
        $ErrorActionPreference = $previousErrorActionPreference
    }
    if ($nativeExitCode -ne 0) {
        $detail = (($allOutput | ForEach-Object { $_.ToString().Trim() }) -join ' ').Trim()
        throw "M89_M56_WSL_COMMAND_FAILED exit=$nativeExitCode command=$($Arguments -join ' ') detail=$detail"
    }
    return @($allOutput | Where-Object { $_ -isnot [System.Management.Automation.ErrorRecord] })
}

function Convert-WindowsPathToWsl {
    param([Parameter(Mandatory = $true)][string]$WindowsPath)

    $fullPath = [System.IO.Path]::GetFullPath($WindowsPath)
    $root = [System.IO.Path]::GetPathRoot($fullPath)
    if ($root -notmatch '^[A-Za-z]:\\$') {
        throw "M89_M56_WINDOWS_PATH_UNSUPPORTED: $fullPath"
    }
    $drive = $root.Substring(0, 1).ToLowerInvariant()
    $suffix = $fullPath.Substring($root.Length).Replace('\', '/')
    return "/mnt/$drive/$suffix"
}

if (-not (Get-Command wsl.exe -ErrorAction SilentlyContinue)) {
    throw 'M89_M56_WSL_NOT_AVAILABLE: wsl.exe was not found. Install or enable WSL before staging the M56 artifact.'
}

if ([string]::IsNullOrWhiteSpace($Distro)) {
    $distroLines = @(& wsl.exe -l -q 2>&1)
    if ($LASTEXITCODE -ne 0) {
        $detail = (($distroLines | ForEach-Object { $_.ToString().Trim() }) -join ' ').Trim()
        throw "M89_M56_WSL_LIST_FAILED exit=$LASTEXITCODE detail=$detail"
    }
    $ubuntuDistros = @(
        $distroLines |
            ForEach-Object { $_.ToString().Trim() } |
            Where-Object { $_ -match '^Ubuntu(?:$|-)' }
    )
    if ($ubuntuDistros.Count -ne 1) {
        $found = (($distroLines | ForEach-Object { $_.ToString().Trim() } | Where-Object { $_ }) -join ', ')
        throw "M89_M56_WSL_DISTRO_AUTO_DETECT_FAIL expected_one_Ubuntu found=[$found]. Rerun with -Distro <one exact installed name>."
    }
    $Distro = $ubuntuDistros[0]
    Write-Host "M89_M56_WSL_DISTRO_AUTO_SELECTED=$Distro"
}

$destinationUnix = Convert-WindowsPathToWsl -WindowsPath $destination
if ([string]::IsNullOrWhiteSpace($destinationUnix)) {
    throw "M89_M56_WSLPATH_EMPTY: cannot map destination $destination into WSL"
}
$destinationParentUnix = Convert-WindowsPathToWsl -WindowsPath $destinationParent

Write-Host "M89_M56_STAGE_SOURCE_WSL=$sourceUnix"
Write-Host "M89_M56_STAGE_DESTINATION=$destination"

$sourceManifestUnix = "$sourceUnix/CHECKPOINT_MANIFEST.json"
$sourceManifestText = (Invoke-WslChecked -Arguments @('cat', $sourceManifestUnix)) -join "`n"
if ([string]::IsNullOrWhiteSpace($sourceManifestText)) {
    throw "M89_M56_SOURCE_MANIFEST_MISSING: $sourceManifestUnix"
}
$sourceData = $sourceManifestText | ConvertFrom-Json
$sourceManifestHashLines = @(Invoke-WslChecked -Arguments @('sha256sum', $sourceManifestUnix))
$sourceManifestHashLine = [string]($sourceManifestHashLines | Select-Object -First 1)
$sourceManifestHash = ($sourceManifestHashLine -split '\s+')[0].ToLowerInvariant()
if ($sourceManifestHash -ne $expectedManifestHash) {
    throw "M89_M56_SOURCE_MANIFEST_HASH_MISMATCH expected=$expectedManifestHash observed=$sourceManifestHash"
}
$sourceBlobUnix = "$sourceUnix/$($sourceData.blob.path)"
Invoke-WslChecked -Arguments @('test', '-f', $sourceBlobUnix) | Out-Null
if ([int64]$sourceData.blob.bytes -ne $expectedBlobBytes -or $sourceData.blob.sha256.ToLowerInvariant() -ne $expectedBlobHash) {
    throw "M89_M56_SOURCE_METADATA_MISMATCH: blob metadata is not the accepted M56 artifact"
}
$sourceLanguageCount = @($sourceData.entries | Where-Object { $_.kind -eq 'packed' -and $_.module -like 'model.language_model.layers.*' }).Count
if ($sourceLanguageCount -ne $expectedLanguageEntries) {
    throw "M89_M56_SOURCE_LANGUAGE_COUNT_MISMATCH expected=$expectedLanguageEntries observed=$sourceLanguageCount"
}
$sourceBlobHashLines = @(Invoke-WslChecked -Arguments @('sha256sum', $sourceBlobUnix))
$sourceBlobHashLine = [string]($sourceBlobHashLines | Select-Object -First 1)
$sourceBlobHash = ($sourceBlobHashLine -split '\s+')[0].ToLowerInvariant()
if ($sourceBlobHash -ne $expectedBlobHash) {
    throw "M89_M56_SOURCE_BLOB_HASH_MISMATCH expected=$expectedBlobHash observed=$sourceBlobHash"
}

$targetDrive = (Get-Item -LiteralPath $projectRoot).PSDrive
$requiredFree = $expectedBlobBytes + 512MB
if ($targetDrive.Free -lt $requiredFree) {
    throw "M89_M56_INSUFFICIENT_SPACE drive=$($targetDrive.Name) free=$($targetDrive.Free) required=$requiredFree"
}
if (Test-Path -LiteralPath $destination) {
    throw "M89_M56_DESTINATION_EXISTS: $destination`nRefusing to overwrite an existing artifact. Ask Codex to audit it first."
}

Write-Host "M89_M56_SOURCE_AUDIT_PASS manifest_sha256=$sourceManifestHash blob_sha256=$sourceBlobHash language_entries=$sourceLanguageCount"
if ($CheckOnly) {
    Write-Host 'M89_M56_CHECK_ONLY_PASS'
    exit 0
}

Invoke-WslChecked -Arguments @('mkdir', '-p', $destinationParentUnix) | Out-Null
Invoke-WslChecked -Arguments @('cp', '-a', $sourceUnix, $destinationParentUnix) | Out-Null

$destinationManifest = Join-Path $destination 'CHECKPOINT_MANIFEST.json'
$destinationData = Get-Content -LiteralPath $destinationManifest -Raw | ConvertFrom-Json
$destinationManifestHash = (Get-FileHash -Algorithm SHA256 -LiteralPath $destinationManifest).Hash.ToLowerInvariant()
$destinationBlob = Join-Path $destination $destinationData.blob.path
$destinationBlobHash = (Get-FileHash -Algorithm SHA256 -LiteralPath $destinationBlob).Hash.ToLowerInvariant()
$destinationLanguageCount = @($destinationData.entries | Where-Object { $_.kind -eq 'packed' -and $_.module -like 'model.language_model.layers.*' }).Count
if ($destinationManifestHash -ne $expectedManifestHash -or $destinationBlobHash -ne $expectedBlobHash -or $destinationLanguageCount -ne $expectedLanguageEntries) {
    throw "M89_M56_DESTINATION_VERIFY_FAIL manifest=$destinationManifestHash blob=$destinationBlobHash language_entries=$destinationLanguageCount"
}
Write-Host "M89_M56_STAGE_PASS manifest_sha256=$destinationManifestHash blob_sha256=$destinationBlobHash language_entries=$destinationLanguageCount"
