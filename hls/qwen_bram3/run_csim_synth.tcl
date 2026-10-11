set source_root "Q:/tmp/qwen-bram3-source"
set data_root "Q:/tmp/qwen-bram3-data"
set project_root "C:/Users/30429/qbram3/hls"

open_component -reset $project_root -flow_target vivado
set_top qwen25_mixed_gs_macro
add_files "$source_root/qwen25_mixed_gs_macro.cpp"
add_files -tb "$source_root/tb_qwen25_mixed_gs_macro.cpp"
set_part {xck26-sfvc784-2LV-c}
create_clock -period 6.0 -name default
set ::env(QWEN_GS_DATA_DIR) $data_root
csim_design -clean
csynth_design
# RTL co-sim is intentionally omitted here because the installed BASIC XSIM
# license caps designs at 50,000 instances; this design has 57,961. CSim,
# synthesis, Vivado implementation, and board golden gates remain mandatory.
export_design -format ip_catalog \
    -output "C:/Users/30429/qbram3/qwen25_mixed_gs_macro.zip"
exit
