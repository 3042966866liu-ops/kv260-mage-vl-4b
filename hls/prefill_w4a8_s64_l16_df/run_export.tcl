set component_root "C:/Users/30429/qprefilldf/hls"
set output_zip "Q:/tmp/prefill_v1/qwen25_prefill_w4a8_s64_l16_df.zip"

open_component $component_root
export_design -format ip_catalog -output $output_zip
exit
