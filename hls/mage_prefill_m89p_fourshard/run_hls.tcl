set root "C:/Users/30429/Desktop/TeLLMe_FPGA_2026/hls/mage_prefill_m89p_fourshard"
open_project -reset "D:/TeLLMe_FPGA_2026/m89p_fourshard_hls"
set_top m89p_fourshard
add_files "$root/mage_prefill_m89p_fourshard.cpp" -cflags {-std=c++14 -DMAGE_T6_DSP_FREE_DEQUANT -DMAGE_T6_PREDECODE_WEIGHTS -DMAGE_T6_EXACT_SHIFT_ADD}
add_files -tb "$root/tb_mage_prefill_m89p_fourshard.cpp" -cflags {-std=c++14 -DMAGE_T6_DSP_FREE_DEQUANT -DMAGE_T6_PREDECODE_WEIGHTS -DMAGE_T6_EXACT_SHIFT_ADD}
open_solution -reset hls
set_part {xck26-sfvc784-2LV-c}
create_clock -period 5.000 -name default
config_compile -pipeline_loops 64
csim_design
csynth_design
exit
