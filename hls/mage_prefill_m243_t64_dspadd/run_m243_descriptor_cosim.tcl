set project "V:/m243d"
open_project -reset $project
set_top m243_t64_kernel
add_files "T:/hls/mage_prefill_m243_t64_dspadd/mage_prefill_m243_t64_dspadd.cpp"
add_files -tb "T:/hls/mage_prefill_m243_t64_dspadd/tb_m243_t64_max_descriptor_rtl.cpp" -cflags "-IT:/hls/mage_prefill_m243_t64_dspadd"
open_solution -reset solution1 -flow_target vivado
set_part {xck26-sfvc784-2LV-c}
create_clock -period 4.8 -name default
set_clock_uncertainty 1.3
config_compile -pipeline_loops 0
csynth_design
cosim_design -rtl verilog -trace_level none
exit
