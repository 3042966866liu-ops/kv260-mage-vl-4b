set source_dir [file dirname [file normalize [info script]]]
set project_dir "D:/CodexHome/visualizations/2026/08/31/01a05594-2ad6-7820-b960-8059a45ae04c/m230_t64_csim"
open_project -reset $project_dir
set staged_hls [file join $project_dir staged_hls_v3]
file copy -force [file dirname $source_dir] $staged_hls
set_top m230_t64_kernel
add_files -tb [file join $staged_hls mage_prefill_m230_t64_reuse tb_m230_t64_numerical.cpp]
open_solution -reset solution1
csim_design
exit
