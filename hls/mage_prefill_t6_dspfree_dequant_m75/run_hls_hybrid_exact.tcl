set source_root "C:/Users/30429/Desktop/TeLLMe_FPGA_2026/hls/mage_prefill_t6_shared_dequant_v1"
set project_root "C:/Users/30429/Desktop/TeLLMe_FPGA_2026/tmp/mage_prefill_t6_shared_dequant_hybrid_exact_v5/hls_project"
open_project -reset $project_root
set_top mage_prefill_t6_arith
add_files "$source_root/mage_prefill_t6_arith.cpp" -cflags {-DMAGE_T6_WEIGHT_SCALE_HYBRID_EXACT}
add_files -tb "$source_root/tb_mage_prefill_t6_arith.cpp"
open_solution -reset hls
set_part xck26-sfvc784-2LV-c
create_clock -period 3.703703704 -name default
csim_design
csynth_design
exit
