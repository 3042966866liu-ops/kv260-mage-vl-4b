set root [file normalize [pwd]]
set fixture [file normalize [file join $root deployment mage_vl4b artifacts m89q_real_m56_fourport_fixture.bin]]
set ::env(M89Q_FIXTURE_PATH) $fixture
set project [file normalize [file join $root m89q_real_m56_csim]]
open_project -reset $project
set_top m89p_fourshard
add_files [file join $root hls mage_prefill_m89p_fourshard mage_prefill_m89p_fourshard.cpp]
add_files -tb [file join $root hls mage_prefill_m89q_real_m56 tb_mage_prefill_m89q_real_m56.cpp]
open_solution -reset hls -flow_target vivado
set_part {xck26-sfvc784-2LV-c}
create_clock -period 5.0 -name default
csim_design -clean
exit
