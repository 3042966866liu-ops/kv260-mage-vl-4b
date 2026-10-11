set root {C:/Users/30429/Desktop/TeLLMe_FPGA_2026/tmp/m441_full_numeric_01}
set project {C:/Users/30429/Desktop/TeLLMe_FPGA_2026/tmp/m441_full_csim_project_01}
if {[file exists $project]} {error "Existing full CSim: collect only"}
set ::env(M441_FULL_FIXTURE_ROOT) $root
open_project $project
set_top m89x_runtime_kernel
add_files [file join $root source hls mage_prefill_m89x_runtime mage_prefill_m89x_runtime.cpp]
add_files -tb [file join $root m441_full_chain_tb.cpp] -cflags "-I[file join $root source hls mage_prefill_m89x_runtime]"
open_solution hls -flow_target vivado
set_part {xck26-sfvc784-2LV-c}
create_clock -period 4.8 -name default
set_clock_uncertainty 1.3
config_compile -pipeline_loops 0
csim_design -clean -O
exit
