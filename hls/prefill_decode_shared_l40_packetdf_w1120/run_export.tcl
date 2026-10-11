set source_snapshot "C:/qdb/w1120_src.cpp"
set header_snapshot "C:/qdb/qwen25_prefill_w4a8.hpp"
set component_root "C:/qdb/w1120_hls"
set output_zip "C:/Users/30429/Desktop/TeLLMe_FPGA_2026/tmp/packetdf_w1120/qwen25_prefill_decode_shared_l40_packetdf_w1120.zip"

open_component -reset $component_root -flow_target vivado
file copy -force $source_snapshot "$component_root/w1120_src.cpp"
file copy -force $header_snapshot "$component_root/qwen25_prefill_w4a8.hpp"
cd $component_root
set_top qwen25_prefill_w4a8
add_files "w1120_src.cpp"
set_part {xck26-sfvc784-2LV-c}
create_clock -period 6.0 -name default
csynth_design
export_design -format ip_catalog -output $output_zip
exit
