set root "D:/CodexHome/visualizations/2026/09/01/01a05cf2-5674-7841-b1b8-a9e9eec650fb/m233_hls_source_01"
set project "V:/m233d"
open_project -reset $project
set_top m233_t64_kernel
add_files [file join $root mage_prefill_m233_t64_resource2 mage_prefill_m230_t64_reuse.cpp]
add_files -tb [file join $root mage_prefill_m233_t64_resource2 tb_m233_t64_max_descriptor_rtl.cpp] -cflags "-I[file join $root mage_prefill_m233_t64_resource2]"
open_solution -reset solution1 -flow_target vivado
set_part {xck26-sfvc784-2LV-c}
create_clock -period 4.8 -name default
set_clock_uncertainty 1.3
config_compile -pipeline_loops 0
csim_design -clean
csynth_design
cosim_design -rtl verilog -trace_level none
exit
