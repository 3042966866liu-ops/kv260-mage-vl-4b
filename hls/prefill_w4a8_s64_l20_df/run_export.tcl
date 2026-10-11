set component_root "C:/Users/30429/qprefill20/hls"
set output_zip "C:/Users/30429/Desktop/TeLLMe_FPGA_2026/tmp/prefill_v1/qwen25_prefill_w4a8_s64_l20_df.zip"

open_component $component_root
export_design -format ip_catalog -output $output_zip
exit
