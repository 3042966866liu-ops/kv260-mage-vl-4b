set source_root "C:/Users/30429/Desktop/TeLLMe_FPGA_2026/hls/mage_packed_mac2_v1"
set project_root "C:/Users/30429/Desktop/TeLLMe_FPGA_2026/tmp/mage_packed_mac2_v1/hls_project"

open_component -reset $project_root -flow_target vivado
set_top mage_packed_mac2
add_files "$source_root/mage_packed_mac2.cpp"
add_files -tb "$source_root/tb_mage_packed_mac2.cpp"
set_part {xck26-sfvc784-2LV-c}
create_clock -period 5.0 -name default
csim_design -clean
csynth_design
exit
