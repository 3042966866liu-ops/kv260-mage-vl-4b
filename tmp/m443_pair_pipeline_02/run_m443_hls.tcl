set root {C:/Users/30429/Desktop/TeLLMe_FPGA_2026/tmp/m443_pair_pipeline_02}
set project {C:/Users/30429/Desktop/TeLLMe_FPGA_2026/tmp/m443_hls_project_02}
if {[file exists $project]} {error "Existing project: collect only"}
set ::env(M128_FIXTURE_PATH) {C:/Users/30429/Desktop/TeLLMe_FPGA_2026/deployment/mage_vl4b/artifacts/m128_m120_real_record_csim_fixture.bin}
cd [file dirname $root]
open_project $project
set_top m89x_runtime_kernel
add_files [file join $root hls/mage_prefill_m89x_runtime/mage_prefill_m89x_runtime.cpp]
add_files -tb [file join $root hls/mage_prefill_m89x_runtime/tb_m128_m120_numerical.cpp] -cflags "-I[file join $root hls mage_prefill_m89x_runtime]"
open_solution hls -flow_target vivado
set_part {xck26-sfvc784-2LV-c}
create_clock -period 4.8 -name default
set_clock_uncertainty 1.3
config_compile -pipeline_loops 0
csim_design -clean
csynth_design
exit
