set source_root "C:/Users/30429/Desktop/TeLLMe_FPGA_2026/hls/mage_prefill_t6_runtime_full_m76c1"
set project_root "T:/tmp/m76c1_t6rt_hls"
open_project -reset $project_root
set_top m75c_t6rt
add_files "$source_root/mage_prefill_t6_runtime_full_m75c.cpp" -cflags {-std=c++14 -DMAGE_T6_DSP_FREE_DEQUANT -DMAGE_T6_PREDECODE_WEIGHTS -DMAGE_T6_EXACT_SHIFT_ADD}
add_files -tb "$source_root/tb_mage_prefill_t6_runtime_full_m75c.cpp" -cflags {-std=c++14 -DMAGE_T6_DSP_FREE_DEQUANT -DMAGE_T6_PREDECODE_WEIGHTS -DMAGE_T6_EXACT_SHIFT_ADD}
open_solution -reset "hls"
set_part {xck26-sfvc784-2LV-c}
create_clock -period 3.704 -name default
config_compile -pipeline_loops 64
csim_design
csynth_design
exit
