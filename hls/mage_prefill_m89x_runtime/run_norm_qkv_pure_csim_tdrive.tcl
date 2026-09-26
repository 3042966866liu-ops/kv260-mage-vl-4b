# Pure CSim gate.  Do not select a Vivado flow target, part, clock, synthesis,
# co-simulation, export or RTL command: this gate validates only C++/HLS
# simulation semantics against the independent packed-weight reference.
set root "T:/"
set fixture [file join $root deployment mage_vl4b artifacts m89x1_layer0_norm_qkv_fixture.bin]
set output [file join $root deployment mage_vl4b artifacts m89x1_layer0_norm_qkv_hls_output.bin]
if {![file isfile $fixture]} { error "M89X1_NORM_QKV_FIXTURE_MISSING $fixture" }
set ::env(M89X1_CSIM_FIXTURE) $fixture
set ::env(M89X1_CSIM_OUTPUT) $output
# Keep the project immediately below T:.  Vitis stores design sources relative
# to this project; under T:/tmp it incorrectly emits ../hls (T:/tmp/hls) and
# silently omits the kernel from the CSim link.
open_project -reset [file join $root m89x1_norm_qkv_pure_csim]
set_top m89x_runtime_kernel
add_files [file join $root hls mage_prefill_m89x_runtime mage_prefill_m89x_runtime.cpp]
add_files -tb [file join $root hls mage_prefill_m89x_runtime tb_m89x1_norm_qkv_pure_csim.cpp]
# Vitis HLS requires a solution object for CSim, but without -flow_target it
# remains a simulation-only solution and deliberately has no device binding.
open_solution -reset csim
config_compile -pipeline_loops 0
csim_design -clean
exit
