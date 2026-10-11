param(
    [string]$InputTop = "m89t_scale_chain_hls_strict48\hls\impl\ip\hdl\verilog\m89t_scale_chain.v",
    [string]$OutputPath = "tmp\m89u_combined_vivado_ooc\m89u_combined_wrapper.v"
)

$ErrorActionPreference = 'Stop'
$lines = Get-Content -LiteralPath $InputTop
$moduleStart = -1
$headerEnd = -1
for ($i = 0; $i -lt $lines.Count; $i++) {
    if ($moduleStart -lt 0 -and $lines[$i] -match '^module\s+m89t_scale_chain\s*\(') {
        $moduleStart = $i
        continue
    }
    if ($moduleStart -ge 0 -and $lines[$i].Trim() -eq ');') {
        $headerEnd = $i
        break
    }
}
if ($moduleStart -lt 0 -or $headerEnd -lt 0) {
    throw 'M89U_WRAPPER_SOURCE_MODULE_HEADER_NOT_FOUND'
}

$ports = [System.Collections.Generic.List[string]]::new()
for ($i = $moduleStart + 1; $i -lt $headerEnd; $i++) {
    $name = $lines[$i].Trim().TrimEnd(',')
    if ($name) { $ports.Add($name) }
}

$parameters = @($lines | Where-Object { $_ -match '^parameter\s+' })
$declarations = @{}
foreach ($line in $lines) {
    if ($line -match '^\s*(input|output)\s+(?:(?:wire|reg)\s+)?(?:\[[^\]]+\]\s+)?([A-Za-z_][A-Za-z0-9_]*)\s*;') {
        $declarations[$Matches[2]] = $line.Trim()
    }
}
foreach ($port in $ports) {
    if (-not $declarations.ContainsKey($port)) {
        throw "M89U_WRAPPER_PORT_DECLARATION_MISSING port=$port"
    }
}

$rxPorts = @('rx_TDATA','rx_TVALID','rx_TREADY','rx_TKEEP','rx_TSTRB','rx_TLAST')
# The packaged Vivado IP intentionally removes zero-width AXI USER channels,
# although the raw HLS RTL keeps one-bit placeholders for them.
$instancePorts = @($ports | Where-Object {
    $_ -notmatch '^m_axi_w[0-3]_(AWUSER|WUSER|ARUSER|RUSER|BUSER)$'
})
$externalPorts = @($instancePorts | Where-Object { $_ -notin $rxPorts }) + @(
    'descriptor_count', 'm_axis_tdata', 'm_axis_tkeep', 'm_axis_tstrb',
    'm_axis_tlast', 'm_axis_tvalid', 'm_axis_tready'
)

$out = [System.Collections.Generic.List[string]]::new()
$out.Add('`timescale 1ns/1ps')
$out.Add('')
$out.Add('module m89u_combined_wrapper (')
for ($i = 0; $i -lt $externalPorts.Count; $i++) {
    $comma = if ($i -eq $externalPorts.Count - 1) { '' } else { ',' }
    $out.Add("    $($externalPorts[$i])$comma")
}
$out.Add(');')
$out.Add('')
foreach ($parameter in $parameters) { $out.Add($parameter) }
$out.Add('')
foreach ($port in $instancePorts) {
    if ($port -notin $rxPorts) { $out.Add($declarations[$port]) }
}
$out.Add('input  [3:0] descriptor_count;')
$out.Add('output [63:0] m_axis_tdata;')
$out.Add('output [7:0] m_axis_tkeep;')
$out.Add('output [7:0] m_axis_tstrb;')
$out.Add('output m_axis_tlast;')
$out.Add('output m_axis_tvalid;')
$out.Add('input  m_axis_tready;')
$out.Add('')
$out.Add('wire [63:0] rx_TDATA;')
$out.Add('wire rx_TVALID;')
$out.Add('wire rx_TREADY;')
$out.Add('wire [7:0] rx_TKEEP;')
$out.Add('wire [7:0] rx_TSTRB;')
$out.Add('wire [0:0] rx_TLAST;')
$out.Add('')
$out.Add('(* DONT_TOUCH = "yes" *) m89t_scale_chain_ip m89t_i (')
for ($i = 0; $i -lt $instancePorts.Count; $i++) {
    $port = $instancePorts[$i]
    $comma = if ($i -eq $instancePorts.Count - 1) { '' } else { ',' }
    $out.Add("    .$port($port)$comma")
}
$out.Add(');')
$out.Add('')
$out.Add('(* DONT_TOUCH = "yes" *) m89u_axis_tlast_coalescer tlast_coalescer_i (')
$out.Add('    .aclk(ap_clk),')
$out.Add('    .aresetn(ap_rst_n),')
$out.Add('    .descriptor_count(descriptor_count),')
$out.Add('    .s_axis_tdata(rx_TDATA),')
$out.Add('    .s_axis_tkeep(rx_TKEEP),')
$out.Add('    .s_axis_tstrb(rx_TSTRB),')
$out.Add('    .s_axis_tlast(rx_TLAST[0]),')
$out.Add('    .s_axis_tvalid(rx_TVALID),')
$out.Add('    .s_axis_tready(rx_TREADY),')
$out.Add('    .m_axis_tdata(m_axis_tdata),')
$out.Add('    .m_axis_tkeep(m_axis_tkeep),')
$out.Add('    .m_axis_tstrb(m_axis_tstrb),')
$out.Add('    .m_axis_tlast(m_axis_tlast),')
$out.Add('    .m_axis_tvalid(m_axis_tvalid),')
$out.Add('    .m_axis_tready(m_axis_tready)')
$out.Add(');')
$out.Add('endmodule')

$parent = Split-Path -Parent $OutputPath
New-Item -ItemType Directory -Force -Path $parent | Out-Null
[System.IO.File]::WriteAllLines(
    [System.IO.Path]::GetFullPath($OutputPath),
    $out,
    [System.Text.UTF8Encoding]::new($false)
)
Write-Output "M89U_COMBINED_WRAPPER_GENERATION_PASS raw_ports=$($ports.Count) packaged_ports=$($instancePorts.Count) output=$OutputPath"
