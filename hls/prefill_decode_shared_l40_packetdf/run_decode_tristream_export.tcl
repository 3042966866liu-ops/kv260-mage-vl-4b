set component_root "C:/Users/30429/Desktop/TeLLMe_FPGA_2026/tmp/decode_tristream/hls"
set output_zip "C:/Users/30429/Desktop/TeLLMe_FPGA_2026/tmp/decode_tristream/qwen25_decode_tristream_l2.zip"

open_component $component_root
export_design -format ip_catalog -output $output_zip
exit
