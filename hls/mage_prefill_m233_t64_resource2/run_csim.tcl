set project_dir "D:/CodexHome/visualizations/2026/09/01/01a05cf2-5674-7841-b1b8-a9e9eec650fb/m233_t64_csim"
set source_hls "D:/CodexHome/visualizations/2026/09/01/01a05cf2-5674-7841-b1b8-a9e9eec650fb/m233_hls_source_01"
open_project -reset $project_dir
set staged_hls [file join $project_dir staged_hls_v3]
file copy -force $source_hls $staged_hls
set_top m233_t64_kernel
add_files -tb [file join $staged_hls mage_prefill_m233_t64_resource2 tb_m230_t64_numerical.cpp]
open_solution -reset solution1
csim_design
exit
