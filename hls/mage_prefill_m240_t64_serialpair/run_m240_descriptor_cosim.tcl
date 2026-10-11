set project "V:/m240d"
open_project -reset $project
set_top m240_t64_kernel
add_files "T:/hls/mage_prefill_m240_t64_serialpair/mage_prefill_m230_t64_reuse.cpp"
add_files -tb "T:/hls/mage_prefill_m240_t64_serialpair/tb_m233_t64_max_descriptor_rtl.cpp" -cflags "-IT:/hls/mage_prefill_m240_t64_serialpair"
open_solution -reset solution1 -flow_target vivado
set_part {xck26-sfvc784-2LV-c}
create_clock -period 4.8 -name default
set_clock_uncertainty 1.3
config_compile -pipeline_loops 0
csynth_design
cosim_design -rtl verilog -trace_level none
exit
