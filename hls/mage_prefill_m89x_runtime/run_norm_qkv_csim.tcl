# vitis-run does not guarantee that [pwd] remains the invoking workspace.
# Resolve the repository root from this script so the fixture path is stable.
# Do not normalize this Windows path: on this host the Desktop alias resolves
# differently inside Vitis than it does for the invoking PowerShell process.
set root [file dirname [file dirname [file dirname [info script]]]]
set fixture [file join $root deployment mage_vl4b artifacts m89x1_layer0_norm_qkv_fixture.bin]
set output [file join $root deployment mage_vl4b artifacts m89x1_layer0_norm_qkv_hls_output.bin]
if {![file isfile $fixture]} { error "M89X1_NORM_QKV_FIXTURE_MISSING $fixture" }
set ::env(M89X1_CSIM_FIXTURE) $fixture
set ::env(M89X1_CSIM_OUTPUT) $output
# Keep Vitis-generated intermediates outside Desktop.  The 2026.1 launcher
# rewrites that Windows alias for its project directory, but source paths are
# still read from $root unchanged.
set scratch {D:/CodexHome/visualizations/2026/08/31/01a05594-2ad6-7820-b960-8059a45ae04c/m89x1_norm_qkv_csim}
open_project -reset $scratch
set_top m89x_runtime_kernel
add_files [file join $root hls mage_prefill_m89x_runtime mage_prefill_m89x_runtime.cpp]
add_files -tb [file join $root hls mage_prefill_m89x_runtime tb_m89x1_norm_qkv.cpp]
open_solution -reset hls -flow_target vivado
set_part {xck26-sfvc784-2LV-c}
create_clock -period 5.0 -name default
config_compile -pipeline_loops 0
csim_design -clean
exit
