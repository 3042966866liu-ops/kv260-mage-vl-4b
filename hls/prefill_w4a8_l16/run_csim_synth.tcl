set source_root "Q:/hls/prefill_w4a8_l16"
set project_root "C:/Users/30429/qprefill16/hls"

open_component -reset $project_root -flow_target vivado
set_top qwen25_prefill_w4a8
add_files "$source_root/qwen25_prefill_w4a8.cpp"
add_files -tb "$source_root/tb_qwen25_prefill_w4a8.cpp"
set_part {xck26-sfvc784-2LV-c}
create_clock -period 6.0 -name default
csim_design -clean
csynth_design
exit
