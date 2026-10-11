set source_root "C:/Users/30429/Desktop/TeLLMe_FPGA_2026/hls/prefill_decode_shared_l40_packetdf"
set project_root "C:/Users/30429/Desktop/TeLLMe_FPGA_2026/tmp/decode_tristream/csim"

open_component -reset $project_root -flow_target vivado
set_top qwen25_decode_w4a8_tristream
add_files "$source_root/qwen25_prefill_w4a8.cpp" -cflags {-DPREFILL_SINGLE_PARALLEL_BLOCKS_VALUE=2}
add_files -tb "$source_root/tb_qwen25_prefill_w4a8_single.cpp" -cflags {-DTEST_DECODE_TRISTREAM -DPREFILL_SINGLE_PARALLEL_BLOCKS_VALUE=2}
set_part {xck26-sfvc784-2LV-c}
create_clock -period 6.0 -name default
csim_design -clean
exit
