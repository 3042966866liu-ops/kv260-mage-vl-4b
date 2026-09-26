set root [file normalize [pwd]]
open_project -reset [file join $root m89x_w3_lmhead_csim]
set_top m89x_runtime_kernel
add_files [file join $root hls mage_prefill_m89x_runtime mage_prefill_m89x_runtime.cpp]
add_files -tb [file join $root hls mage_prefill_m89x_runtime tb_m89x_w3_lmhead.cpp]
open_solution -reset hls -flow_target vivado
set_part {xck26-sfvc784-2LV-c}
create_clock -period 5.0 -name default
config_compile -pipeline_loops 0
csim_design -clean
exit
