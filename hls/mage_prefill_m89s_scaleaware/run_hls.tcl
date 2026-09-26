set root [file normalize [pwd]]
open_project -reset [file join $root m89s_scaleaware_hls]
set_top m89s_scaleaware
add_files [file join $root hls mage_prefill_m89s_scaleaware mage_prefill_m89s_scaleaware.cpp]
add_files -tb [file join $root hls mage_prefill_m89s_scaleaware tb_mage_prefill_m89s_scaleaware.cpp]
open_solution -reset hls -flow_target vivado
set_part {xck26-sfvc784-2LV-c}
create_clock -period 5.0 -name default
config_compile -pipeline_loops 0
csim_design -clean
csynth_design
exit
