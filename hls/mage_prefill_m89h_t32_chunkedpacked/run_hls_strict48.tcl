# M89-H must demonstrate timing margin, not merely meet the 5.0-ns nominal
# clock after 1.35-ns uncertainty.  A 4.8-ns / 1.35-ns run proves positive
# margin at the original 5.0-ns gate only if its own strict slack is positive.
set source_root "C:/Users/30429/Desktop/TeLLMe_FPGA_2026/hls/mage_prefill_m89h_t32_chunkedpacked"
set project_root "D:/TeLLMe_FPGA_2026/m89h_t32_chunkedpacked_strict48_hls"
open_project -reset $project_root
set_top m89h_t32_chunkedpacked
add_files "$source_root/mage_prefill_m89h_t32_chunkedpacked.cpp" -cflags {-std=c++14 -DMAGE_T6_DSP_FREE_DEQUANT -DMAGE_T6_PREDECODE_WEIGHTS -DMAGE_T6_EXACT_SHIFT_ADD}
add_files -tb "$source_root/tb_mage_prefill_m89h_t32_chunkedpacked.cpp" -cflags {-std=c++14 -DMAGE_T6_DSP_FREE_DEQUANT -DMAGE_T6_PREDECODE_WEIGHTS -DMAGE_T6_EXACT_SHIFT_ADD}
open_solution -reset "hls"
set_part {xck26-sfvc784-2LV-c}
create_clock -period 4.800 -name default
config_compile -pipeline_loops 64
csim_design
csynth_design
exit
