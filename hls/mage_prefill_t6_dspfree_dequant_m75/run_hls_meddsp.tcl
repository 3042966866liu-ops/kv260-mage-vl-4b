set root_dir "C:/Users/30429/Desktop/TeLLMe_FPGA_2026"
set project_dir "$root_dir/tmp/mage_prefill_t6_shared_dequant_meddsp_v3/hls_project"

open_project -reset $project_dir
set_top mage_prefill_t6_arith
add_files [file join $root_dir hls mage_prefill_t6_shared_dequant_v1 mage_prefill_t6_arith.cpp] -cflags "-std=c++14 -DMAGE_T6_WEIGHT_SCALE_MEDDSP"
add_files -tb [file join $root_dir hls mage_prefill_t6_shared_dequant_v1 tb_mage_prefill_t6_arith.cpp] -cflags "-std=c++14 -DMAGE_T6_WEIGHT_SCALE_MEDDSP"
open_solution -reset hls -flow_target vivado
set_part {xck26-sfvc784-2LV-c}
create_clock -period 3.703703704 -name default
config_interface -m_axi_addr64
csim_design -clean
csynth_design
exit
