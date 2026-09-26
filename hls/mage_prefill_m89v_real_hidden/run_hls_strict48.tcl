set root [file normalize [pwd]]
open_project -reset [file join $root m89v_fullgroup_chain_hls_strict48]
set_top m89v_fullgroup_chain
add_files [file join $root hls mage_prefill_m89v_real_hidden mage_prefill_m89v_fullgroup_chain.cpp]
open_solution -reset hls -flow_target vivado
set_part {xck26-sfvc784-2LV-c}
create_clock -period 4.8 -name default
config_compile -pipeline_loops 0
csynth_design
exit
