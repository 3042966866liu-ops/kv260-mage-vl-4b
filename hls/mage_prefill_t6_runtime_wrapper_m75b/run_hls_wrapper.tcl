set source_root "C:/Users/30429/Desktop/TeLLMe_FPGA_2026/hls/mage_prefill_t6_runtime_wrapper_m75b"
set project_root "T:/tmp/m75b_t6rt_hls"
open_project -reset $project_root
set_top m75b_t6rt
add_files "$source_root/mage_prefill_t6_arith.cpp" -cflags {-DMAGE_T6_DSP_FREE_DEQUANT -DMAGE_T6_EXACT_SHIFT_ADD -DMAGE_T6_PREDECODE_WEIGHTS}
add_files -tb "$source_root/tb_mage_prefill_t6_arith.cpp" -cflags {-DMAGE_T6_DSP_FREE_DEQUANT -DMAGE_T6_EXACT_SHIFT_ADD -DMAGE_T6_PREDECODE_WEIGHTS}
open_solution -reset hls
set_part {xck26-sfvc784-2LV-c}
create_clock -period 3.704 -name default
csim_design
csynth_design
exit
