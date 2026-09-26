set root [file normalize [pwd]]
set fixture [file join $root deployment mage_vl4b artifacts m128_m120_real_record_csim_fixture.bin]
if {![file isfile $fixture]} {
  error "M128_FIXTURE_MISSING $fixture"
}
set ::env(M128_FIXTURE_PATH) $fixture
open_project -reset [file join $root m128_m120_numerical_csim]
set_top m89x_runtime_kernel
add_files [file join $root hls mage_prefill_m89x_runtime mage_prefill_m89x_runtime.cpp]
add_files -tb [file join $root hls mage_prefill_m89x_runtime tb_m128_m120_numerical.cpp] -cflags "-I[file join $root hls mage_prefill_m89x_runtime]"
open_solution -reset hls -flow_target vivado
set_part {xck26-sfvc784-2LV-c}
create_clock -period 5.0 -name default
config_compile -pipeline_loops 0
csim_design -clean
exit
