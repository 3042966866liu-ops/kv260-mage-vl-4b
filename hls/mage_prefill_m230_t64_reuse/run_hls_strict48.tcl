set project_dir "D:/CodexHome/visualizations/2026/09/01/01a05cf2-5674-7841-b1b8-a9e9eec650fb/m230_t64_hls_strict48"
set source_hls "D:/CodexHome/visualizations/2026/08/31/01a05594-2ad6-7820-b960-8059a45ae04c/m230_hls_source_01"
open_project -reset $project_dir
set staged_hls [file join $project_dir staged_hls]
file copy -force $source_hls $staged_hls
set_top m230_t64_kernel
add_files [file join $staged_hls mage_prefill_m230_t64_reuse mage_prefill_m230_t64_reuse.cpp]
open_solution -reset solution1 -flow_target vivado
set_part {xck26-sfvc784-2LV-c}
create_clock -period 4.8 -name default
set_clock_uncertainty 1.3
config_compile -pipeline_loops 0
csynth_design
exit
