# M82-J tests the non-free-running flushable pipeline style. Arithmetic,
# interfaces, II and the 5-ns/uncertainty gate remain identical to M82-G.
set source_root "C:/Users/30429/Desktop/TeLLMe_FPGA_2026/hls/mage_m82_groupmajor_stream"
set project_root "D:/TeLLMe_FPGA_2026/m82j_twoworker_flp_hls"
open_project -reset $project_root
set_top mage_m82_groupmajor_stream_m82g
add_files "$source_root/mage_m82_groupmajor_stream_m82g.cpp" -cflags {-std=c++14 -DM82B_PIPELINE_STYLE=flp}
add_files -tb "$source_root/tb_mage_m82_groupmajor_stream_m82g.cpp" -cflags {-std=c++14 -DM82B_PIPELINE_STYLE=flp}
open_solution -reset "hls"
set_part {xck26-sfvc784-2LV-c}
create_clock -period 5.000 -name default
config_compile -pipeline_loops 64
csim_design
csynth_design
exit
