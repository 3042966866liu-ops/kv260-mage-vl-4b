set project_root [file normalize [file join [pwd] hls mage_prefill_m89p_fourshard]]
set solution_root [file normalize [file join [pwd] .. TeLLMe_FPGA_2026 m89p_fourshard_hls_strict48]]

open_project -reset $solution_root
set_top m89p_fourshard
add_files [file join $project_root mage_prefill_m89p_fourshard.cpp]
open_solution -reset hls -flow_target vivado
set_part {xck26-sfvc784-2LV-c}
create_clock -period 4.8 -name default
config_compile -pipeline_loops 0
csynth_design
exit
