set source_root "T:/hls/mage_decode_sixport_v2"
set project_root "T:/tmp/mg2e/h"

open_component -reset $project_root -flow_target vivado
set_top mage_decode_sixport_v2
add_files "$source_root/mage_decode_sixport_v2.cpp"
add_files -tb "$source_root/tb_mage_decode_sixport_v2.cpp"
set_part {xck26-sfvc784-2LV-c}
create_clock -period 5.0 -name default
csim_design -clean
csynth_design
export_design -format ip_catalog -rtl verilog -vendor tellme.local -library hls -version 1.0
puts "MAGE_DECODE_SIXPORT_V2_EXPORT=PASS"
exit
