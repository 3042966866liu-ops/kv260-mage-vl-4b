set source_root "C:/Users/30429/Desktop/TeLLMe_FPGA_2026/hls/prefill_decode_shared_l40_packetdf_multisubtile"
set project_root "C:/Users/30429/Desktop/TeLLMe_FPGA_2026/tmp/multisubtile/csim_multisubtile/hls"

open_component -reset $project_root -flow_target vivado
set_top qwen25_prefill_w4a8
add_files "$source_root/qwen25_prefill_w4a8.cpp"
add_files -tb "$source_root/tb_qwen25_prefill_w4a8_multisubtile.cpp"
set_part {xck26-sfvc784-2LV-c}
create_clock -period 6.0 -name default
csim_design -clean
exit
