param()

$ErrorActionPreference = 'Stop'
$workspace = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
$sourceRoot = Join-Path $workspace 'tmp\m120_m89x2_highddr'
$outRoot = Join-Path $sourceRoot 'out'
$runRoot = Join-Path $sourceRoot 'mage_m120_m89x2_highddr.runs\impl_1'
$handoffRoot = Join-Path $sourceRoot 'mage_m120_m89x2_highddr.gen\sources_1\bd\qwen25_mixed_gs\hw_handoff'
$destination = Join-Path $workspace 'deployment\mage_vl4b\m120_m89x2_board_candidate'
$staging = Join-Path $workspace 'tmp\m134_m120_m89x2_board_candidate_staging'
$resultPath = Join-Path $workspace 'deployment\mage_vl4b\M134_M120_M89X2_IMPLEMENTATION_GATE_RESULT.json'

if (Test-Path -LiteralPath $destination) {
    throw "M134_DESTINATION_ALREADY_EXISTS path=$destination"
}
if (Test-Path -LiteralPath $staging) {
    throw "M134_STAGING_ALREADY_EXISTS path=$staging"
}

$timingPath = Join-Path $outRoot 'impl_timing_summary.rpt'
$drcPath = Join-Path $outRoot 'impl_drc.rpt'
$routePath = Join-Path $outRoot 'impl_route_status.rpt'
$utilPath = Join-Path $outRoot 'impl_utilization.rpt'
$preflightPath = Join-Path $outRoot 'preflight_gate.txt'
$addressPath = Join-Path $outRoot 'address_audit.txt'
$childGatePath = Join-Path $outRoot 'child_synth_gate.txt'
$bitPath = Join-Path $runRoot 'qwen25_mixed_gs_wrapper.bit'
$hwhPath = Join-Path $handoffRoot 'qwen25_mixed_gs.hwh'
$xsaPath = Join-Path $outRoot 'mage_m120_m89x2_highddr.xsa'
$ipZipPath = Join-Path $workspace 'tmp\m120_m89x2_runtime_ip\m89x_runtime_kernel_m120_m89x2.zip'
$combinedRtlGatePath = Join-Path $workspace 'deployment\mage_vl4b\M134_M120_RTL_COSIM_GATE_RESULT.json'

$required = @(
    $timingPath, $drcPath, $routePath, $utilPath, $preflightPath,
    $addressPath, $childGatePath, $bitPath, $hwhPath, $xsaPath,
    $ipZipPath, $combinedRtlGatePath
)
foreach ($path in $required) {
    if (-not (Test-Path -LiteralPath $path -PathType Leaf)) {
        throw "M134_REQUIRED_FILE_MISSING path=$path"
    }
}

$timingText = Get-Content -LiteralPath $timingPath -Raw
$timingMatch = [regex]::Match(
    $timingText,
    '(?m)^\s*(?<wns>-?\d+\.\d+)\s+0\.000\s+0\s+\d+\s+(?<whs>-?\d+\.\d+)\s+0\.000\s+0\s+\d+'
)
if (-not $timingMatch.Success) {
    throw 'M134_TIMING_SUMMARY_PARSE_FAIL'
}
$wns = [double]::Parse($timingMatch.Groups['wns'].Value, [Globalization.CultureInfo]::InvariantCulture)
$whs = [double]::Parse($timingMatch.Groups['whs'].Value, [Globalization.CultureInfo]::InvariantCulture)
if ($wns -lt 0.0 -or $whs -lt 0.0) {
    throw "M134_TIMING_FAIL wns=$wns whs=$whs"
}

$routeText = Get-Content -LiteralPath $routePath -Raw
foreach ($pattern in @(
    '# of nets with routing errors[^:]*:\s*0\s*:',
    '# of fully routed nets[^:]*:\s*139054\s*:'
)) {
    if ($routeText -notmatch $pattern) {
        throw "M134_ROUTE_GATE_FAIL pattern=$pattern"
    }
}

$drcText = Get-Content -LiteralPath $drcPath -Raw
$seriousDrc = [regex]::Matches($drcText, '(?m)^\|\s*\S+\s*\|\s*(Error|Critical Warning)\s*\|').Count
if ($seriousDrc -ne 0) {
    throw "M134_SERIOUS_DRC_FAIL count=$seriousDrc"
}

$preflightText = Get-Content -LiteralPath $preflightPath -Raw
$addressText = Get-Content -LiteralPath $addressPath -Raw
$childGateText = Get-Content -LiteralPath $childGatePath -Raw
if ($preflightText -notmatch 'status=PASS' -or $preflightText -notmatch 'build_id_expected=0x4D395832') {
    throw 'M134_PREFLIGHT_GATE_FAIL'
}
if ($addressText -notmatch '0x0000000800000000' -or $addressText -notmatch 'ADDR_WIDTH=64') {
    throw 'M134_ADDRESS_AUDIT_FAIL'
}
if ($childGateText -notmatch 'status=PASS') {
    throw 'M134_CHILD_SYNTH_GATE_FAIL'
}

$rtlGate = Get-Content -LiteralPath $combinedRtlGatePath -Raw | ConvertFrom-Json
if ($rtlGate.status -ne 'PASS') {
    throw "M134_RTL_COSIM_GATE_NOT_PASS status=$($rtlGate.status)"
}

$ipZipSha256 = (Get-FileHash -LiteralPath $ipZipPath -Algorithm SHA256).Hash.ToLowerInvariant()
$expectedIpZipSha256 = '22170cf239811820c20d71a5cf8aa9e958a860988dcc7fb630378097b92c9bd7'
if ($ipZipSha256 -ne $expectedIpZipSha256) {
    throw "M134_IP_ZIP_HASH_FAIL expected=$expectedIpZipSha256 observed=$ipZipSha256"
}

$utilText = Get-Content -LiteralPath $utilPath -Raw
function Get-UsedResource([string]$name) {
    $match = [regex]::Match($utilText, "(?m)^\| $([regex]::Escape($name))\s*\|\s*(?<used>\d+)\s*\|")
    if (-not $match.Success) {
        throw "M134_RESOURCE_PARSE_FAIL resource=$name"
    }
    return [int]$match.Groups['used'].Value
}

$resources = [ordered]@{
    clb_luts = Get-UsedResource 'CLB LUTs'
    clb_registers = Get-UsedResource 'CLB Registers'
    block_ram_tiles = Get-UsedResource 'Block RAM Tile'
    uram = Get-UsedResource 'URAM'
    dsps = Get-UsedResource 'DSPs'
}

New-Item -ItemType Directory -Path (Join-Path $staging 'overlay') -Force | Out-Null
New-Item -ItemType Directory -Path (Join-Path $staging 'full_shell_reports') -Force | Out-Null

$copyMap = [ordered]@{
    'overlay\m120_m89x2_t32.bit' = $bitPath
    'overlay\m120_m89x2_t32.hwh' = $hwhPath
    'overlay\mage_m120_m89x2_highddr.xsa' = $xsaPath
    'full_shell_reports\impl_timing_summary.rpt' = $timingPath
    'full_shell_reports\impl_drc.rpt' = $drcPath
    'full_shell_reports\impl_route_status.rpt' = $routePath
    'full_shell_reports\impl_utilization.rpt' = $utilPath
    'full_shell_reports\preflight_gate.txt' = $preflightPath
    'full_shell_reports\address_audit.txt' = $addressPath
    'full_shell_reports\child_synth_gate.txt' = $childGatePath
}
foreach ($entry in $copyMap.GetEnumerator()) {
    $target = Join-Path $staging $entry.Key
    Copy-Item -LiteralPath $entry.Value -Destination $target
}

$manifest = @()
foreach ($relative in ($copyMap.Keys | Sort-Object)) {
    $path = Join-Path $staging $relative
    $item = Get-Item -LiteralPath $path
    $manifest += [ordered]@{
        path = $relative.Replace('\', '/')
        bytes = $item.Length
        sha256 = (Get-FileHash -LiteralPath $path -Algorithm SHA256).Hash.ToLowerInvariant()
    }
}
$manifestPath = Join-Path $staging 'ARTIFACT_MANIFEST.json'
$manifest | ConvertTo-Json -Depth 4 | Set-Content -LiteralPath $manifestPath -Encoding UTF8
$manifestSha256 = (Get-FileHash -LiteralPath $manifestPath -Algorithm SHA256).Hash.ToLowerInvariant()

$result = [ordered]@{
    gate = 'M134-M120-M89X2-full-shell-implementation'
    status = 'PASS'
    classification = 'Full KV260 Vivado implementation and artifact integrity PASS; board execution not yet run.'
    build_id = '0x4D395832'
    config_register = '0x80'
    timing = [ordered]@{ wns_ns = $wns; whs_ns = $whs; tns_ns = 0.0; ths_ns = 0.0 }
    routing = [ordered]@{ fully_routed_nets = 139054; routing_error_nets = 0 }
    serious_drc_count = $seriousDrc
    resources = $resources
    ip_zip_sha256 = $ipZipSha256
    artifact_manifest_sha256 = $manifestSha256
    artifact_file_count = $manifest.Count
    artifact_total_bytes = [long](($manifest | ForEach-Object { $_['bytes'] } | Measure-Object -Sum).Sum)
    candidate_directory = 'deployment/mage_vl4b/m120_m89x2_board_candidate'
    numerical_and_rtl_cosim_gate = 'deployment/mage_vl4b/M134_M120_RTL_COSIM_GATE_RESULT.json'
    stable_boot_dtb_cma_partitions_changed = $false
    board_execution_run = $false
    next_gate = 'Build a clean hash-locked M120 runtime package, then COM3 Build-ID -> descriptor -> chain -> layer -> fixed-text E2E.'
    rejected_collection_attempt = 'A second Vivado process failed to check out a license before executing the collection Tcl. No artifact or board state was changed; this verifier consumes only the completed implementation outputs.'
}

Move-Item -LiteralPath $staging -Destination $destination
$result | ConvertTo-Json -Depth 6 | Set-Content -LiteralPath $resultPath -Encoding UTF8

Write-Output "M134_M120_M89X2_IMPLEMENTATION_GATE_PASS"
Write-Output "M134_M120_M89X2_WNS=$wns"
Write-Output "M134_M120_M89X2_WHS=$whs"
Write-Output "M134_M120_M89X2_ARTIFACT_MANIFEST_SHA256=$manifestSha256"
