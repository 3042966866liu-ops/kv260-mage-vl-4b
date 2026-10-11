# M85 keeps M84's exact source but requests one additional URAM read pipeline
# stage. It is an offline timing screen only.
set source_root "C:/Users/30429/Desktop/TeLLMe_FPGA_2026/hls/mage_m82_groupmajor_stream"
set project_root "D:/TeLLMe_FPGA_2026/m85_uramreg_hls"
open_project -reset $project_root
set_top mage_m84_three_shard_lane
add_files "$source_root/mage_m84_three_shard_lane.cpp" -cflags {-std=c++14 -DM84_ACTIVATION_RAM_LATENCY=3}
add_files -tb "$source_root/tb_mage_m84_three_shard_lane.cpp" -cflags {-std=c++14 -DM84_ACTIVATION_RAM_LATENCY=3}
open_solution -reset "hls"
set_part {xck26-sfvc784-2LV-c}
create_clock -period 5.000 -name default
config_compile -pipeline_loops 64
csim_design
csynth_design
exit
