set project_dir "V:/m240_t64_csim"
open_project -reset $project_dir
set_top m240_t64_kernel
add_files -tb "T:/hls/mage_prefill_m240_t64_serialpair/tb_m230_t64_numerical.cpp"
open_solution -reset solution1
csim_design
exit
