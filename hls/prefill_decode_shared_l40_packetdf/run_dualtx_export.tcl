set component_root "C:/Users/30429/Desktop/TeLLMe_FPGA_2026/tmp/dualtx_shared/hls"
set output_zip "C:/Users/30429/Desktop/TeLLMe_FPGA_2026/tmp/dualtx_shared/qwen25_prefill_dualtx.zip"

open_component $component_root
export_design -format ip_catalog -output $output_zip
exit
