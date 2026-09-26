set root [file normalize [pwd]]
open_project -reset [file join $root m89v_real_hidden_csim]
set_top m89v_fullgroup_chain
add_files [file join $root hls mage_prefill_m89v_real_hidden mage_prefill_m89v_fullgroup_chain.cpp]
add_files -tb [file join $root hls mage_prefill_m89v_real_hidden tb_mage_prefill_m89v_real_hidden.cpp]
open_solution -reset hls -flow_target vivado
set_part {xck26-sfvc784-2LV-c}
create_clock -period 5.0 -name default
config_compile -pipeline_loops 0
csim_design -clean
exit
