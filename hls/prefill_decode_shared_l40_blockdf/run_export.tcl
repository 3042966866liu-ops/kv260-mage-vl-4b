set component_root "C:/Users/30429/Desktop/TeLLMe_FPGA_2026/tmp/blockdf/hls_project"
set output_zip "C:/Users/30429/Desktop/TeLLMe_FPGA_2026/tmp/blockdf/qwen25_prefill_decode_shared_l40_blockdf.zip"

open_component $component_root
export_design -format ip_catalog -output $output_zip
exit
