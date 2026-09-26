set root [file normalize [pwd]]
set fixture [file join $root deployment mage_vl4b artifacts m89v_real_hidden_allgroups_fixture.bin]
if {![file isfile $fixture]} {
  error "M89X_W2W4_FIXTURE_MISSING $fixture"
}
set ::env(M89V_FIXTURE_PATH) $fixture
open_project -reset [file join $root m89x_w2w4_regression_csim]
set_top m89x_runtime_kernel
add_files [file join $root hls mage_prefill_m89x_runtime mage_prefill_m89x_runtime.cpp]
add_files -tb [file join $root hls mage_prefill_m89x_runtime tb_m89x_w2w4_regression.cpp]
open_solution -reset hls -flow_target vivado
set_part {xck26-sfvc784-2LV-c}
create_clock -period 5.0 -name default
config_compile -pipeline_loops 0
csim_design -clean
exit
