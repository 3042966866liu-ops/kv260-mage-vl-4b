set root [file normalize [pwd]]
open_project -reset [file join $root m89x_runtime_hls_strict48]
set_top m89x_runtime_kernel
add_files [file join $root hls mage_prefill_m89x_runtime mage_prefill_m89x_runtime.cpp]
open_solution -reset hls -flow_target vivado
set_part {xck26-sfvc784-2LV-c}
create_clock -period 4.8 -name default
set_clock_uncertainty 1.3
config_compile -pipeline_loops 0
csynth_design
exit
