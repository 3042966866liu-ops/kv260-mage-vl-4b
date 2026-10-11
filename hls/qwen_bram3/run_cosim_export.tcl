set data_root "Q:/tmp/qwen-bram3-data"
set component_root "C:/Users/30429/qbram3/hls"
set output_zip "C:/Users/30429/qbram3/qwen25_mixed_gs_macro.zip"

open_component $component_root
set ::env(QWEN_GS_DATA_DIR) $data_root
cosim_design -rtl verilog -trace_level none -disable_deadlock_detection
export_design -format ip_catalog -output $output_zip
exit
