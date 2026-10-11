set source_root "C:/Users/30429/Desktop/TeLLMe_FPGA_2026/hls/prefill_decode_shared_l40_packetdf"
set project_root "C:/Users/30429/Desktop/TeLLMe_FPGA_2026/tmp/dualtx_shared/csim"

open_component -reset $project_root -flow_target vivado
set_top qwen25_prefill_w4a8_dualtx
add_files "$source_root/qwen25_prefill_w4a8.cpp" -cflags {-DAP_INT_MAX_W=8192}
add_files -tb "$source_root/tb_qwen25_prefill_w4a8_single.cpp" -cflags {-DTEST_DUALTX_SHARED -DAP_INT_MAX_W=8192}
set_part {xck26-sfvc784-2LV-c}
create_clock -period 6.0 -name default
csim_design -clean
exit
