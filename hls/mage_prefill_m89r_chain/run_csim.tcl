set root [file normalize [pwd]]
set ::env(M89R_FIXTURE_PATH) [file normalize [file join $root deployment mage_vl4b artifacts m89r_real_m56_chain_fixture.bin]]
open_project -reset [file join $root m89r_chain_csim]
set_top m89r_chain
add_files [file join $root hls mage_prefill_m89r_chain mage_prefill_m89r_chain.cpp]
add_files -tb [file join $root hls mage_prefill_m89r_chain tb_mage_prefill_m89r_chain.cpp]
open_solution -reset hls -flow_target vivado
set_part {xck26-sfvc784-2LV-c}
create_clock -period 5.0 -name default
csim_design -clean
exit
