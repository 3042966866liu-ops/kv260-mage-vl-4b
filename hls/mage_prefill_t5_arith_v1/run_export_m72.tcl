set source_root "T:/hls/mage_prefill_t5_arith_v1"
set project_root "T:/tmp/m72_t5_ip/hls_project"
set output_zip "T:/tmp/m72_t5_ip/mage_prefill_t5_arith.zip"
open_project -reset $project_root
set_top mage_prefill_t6_arith
add_files "$source_root/mage_prefill_t6_arith.cpp"
add_files -tb "$source_root/tb_mage_prefill_t6_arith.cpp"
open_solution -reset hls
set_part xck26-sfvc784-2LV-c
create_clock -period 3.636 -name default
csim_design
csynth_design
export_design -format ip_catalog -output $output_zip
exit
