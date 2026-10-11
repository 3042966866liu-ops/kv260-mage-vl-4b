set project_dir "V:/m240_t64_hls_strict48"
open_project -reset $project_dir
set_top m240_t64_kernel
add_files "T:/hls/mage_prefill_m240_t64_serialpair/mage_prefill_m230_t64_reuse.cpp"
open_solution -reset solution1 -flow_target vivado
set_part {xck26-sfvc784-2LV-c}
create_clock -period 4.8 -name default
set_clock_uncertainty 1.3
config_compile -pipeline_loops 0
csynth_design
exit
