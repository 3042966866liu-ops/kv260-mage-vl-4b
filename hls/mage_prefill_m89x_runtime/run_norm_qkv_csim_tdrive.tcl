# Historical M89 HLS invocation: the repository is mapped to T: before this
# script is called.  It avoids Vitis 2026.1's Desktop-alias rewrite.
set root "T:/"
set fixture [file join $root deployment mage_vl4b artifacts m89x1_layer0_norm_qkv_fixture.bin]
set output [file join $root deployment mage_vl4b artifacts m89x1_layer0_norm_qkv_hls_output.bin]
if {![file isfile $fixture]} { error "M89X1_NORM_QKV_FIXTURE_MISSING $fixture" }
set ::env(M89X1_CSIM_FIXTURE) $fixture
set ::env(M89X1_CSIM_OUTPUT) $output
open_project -reset [file join $root tmp m89x1_norm_qkv_csim]
set_top m89x_runtime_kernel
add_files [file join $root hls mage_prefill_m89x_runtime mage_prefill_m89x_runtime.cpp]
add_files -tb [file join $root hls mage_prefill_m89x_runtime tb_m89x1_norm_qkv.cpp]
open_solution -reset hls -flow_target vivado
set_part {xck26-sfvc784-2LV-c}
create_clock -period 5.0 -name default
config_compile -pipeline_loops 0
csim_design -clean
exit
