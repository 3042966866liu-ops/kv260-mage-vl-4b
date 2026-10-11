set component_root "C:/Users/30429/Desktop/TeLLMe_FPGA_2026/tmp/dualhp_decode/hls"
set output_zip "C:/Users/30429/Desktop/TeLLMe_FPGA_2026/tmp/dualhp_decode/qwen25_decode_dualhp_l2.zip"

open_component $component_root
export_design -format ip_catalog -output $output_zip
exit
