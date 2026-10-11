set source_root "T:/hls/prefill_decode_shared_l40_packetdf"
set project_root "T:/tmp/decode_tristream/hls_export_short"
set output_zip "T:/tmp/decode_tristream/qwen25_decode_tristream_l2.zip"

open_component -reset $project_root -flow_target vivado
set_top qwen25_decode_w4a8_tristream
add_files "$source_root/qwen25_prefill_w4a8.cpp" -cflags {-DPREFILL_SINGLE_PARALLEL_BLOCKS_VALUE=2}
set_part {xck26-sfvc784-2LV-c}
create_clock -period 6.0 -name default
config_export -ipname qd3 -display_name qd3
csynth_design
export_design -format ip_catalog -output $output_zip
exit
