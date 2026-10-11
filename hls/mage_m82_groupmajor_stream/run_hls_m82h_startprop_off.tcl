# M82-H is source-identical to M82-G. The 2026.1 tool no longer accepts the
# legacy disable_start_propagation option, so this uses its supported explicit
# start-task FIFO depth to register/buffer dataflow task admission.
set source_root "C:/Users/30429/Desktop/TeLLMe_FPGA_2026/hls/mage_m82_groupmajor_stream"
set project_root "D:/TeLLMe_FPGA_2026/m82h_twoworker_startprop_off_hls"
open_project -reset $project_root
set_top mage_m82_groupmajor_stream_m82g
add_files "$source_root/mage_m82_groupmajor_stream_m82g.cpp" -cflags {-std=c++14}
add_files -tb "$source_root/tb_mage_m82_groupmajor_stream_m82g.cpp" -cflags {-std=c++14}
open_solution -reset "hls"
set_part {xck26-sfvc784-2LV-c}
create_clock -period 5.000 -name default
config_compile -pipeline_loops 64
config_dataflow -start_fifo_depth 8
csim_design
csynth_design
exit
