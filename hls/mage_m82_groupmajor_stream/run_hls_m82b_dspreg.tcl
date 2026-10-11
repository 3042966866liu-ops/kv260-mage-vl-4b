set source_root "C:/Users/30429/Desktop/TeLLMe_FPGA_2026/hls/mage_m82_groupmajor_stream"
set project_root "D:/TeLLMe_FPGA_2026/m82b_groupmajor_threeworker_dspreg_hls"
open_project -reset $project_root
set_top mage_m82_groupmajor_stream_m82b
add_files "$source_root/mage_m82_groupmajor_stream_m82b.cpp" -cflags {-std=c++14}
add_files -tb "$source_root/tb_mage_m82_groupmajor_stream_m82b.cpp" -cflags {-std=c++14}
open_solution -reset "hls"
set_part {xck26-sfvc784-2LV-c}
create_clock -period 5.000 -name default
config_compile -pipeline_loops 64
config_schedule -enable_dsp_full_reg
csim_design
csynth_design
exit
