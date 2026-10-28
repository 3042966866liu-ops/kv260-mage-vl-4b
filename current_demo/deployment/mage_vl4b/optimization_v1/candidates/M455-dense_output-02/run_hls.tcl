set root {C:/Users/30429/Desktop/TeLLMe_FPGA_2026/deployment/mage_vl4b/optimization_v1/candidates/M455-dense_output-02}
set project {D:/CodexHome/visualizations/2026/10/11/01a12a98-44b4-7503-9ea1-46a7b5bcdc3f/native_hls/M455-dense_output-02}
if {[file exists $project]} {error "Existing HLS project: collect only"}
set ::env(M441_FULL_FIXTURE_ROOT) $root
set ::env(M128_FIXTURE_PATH) [file join $root boundary_fixture.bin]
open_project $project
set_top m89x_runtime_kernel
add_files [file join $root hls/mage_prefill_m89x_runtime/mage_prefill_m89x_runtime.cpp]
add_files -tb [file join $root full_tb.cpp] -cflags "-I[file join $root hls mage_prefill_m89x_runtime]"
add_files -tb [file join $root boundary_tb.cpp] -cflags "-I[file join $root hls mage_prefill_m89x_runtime]"
open_solution hls -flow_target vivado
set_part {xck26-sfvc784-2LV-c}
create_clock -period 4.8 -name default
set_clock_uncertainty 1.3
config_compile -pipeline_loops 0
csim_design -clean -O
csynth_design
exit
