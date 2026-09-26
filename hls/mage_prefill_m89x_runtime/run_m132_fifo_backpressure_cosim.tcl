set root {C:/Users/30429/Desktop/TELLME~1}
if {![file isdirectory $root]} {
  error "M132 fixed workspace path is missing: $root"
}
puts "M132_WORKSPACE_ROOT=$root"
cd $root
set project m132_m120_fifo_backpressure_hls

open_project -reset $project
set_top m89x_runtime_kernel
add_files [file join $root hls mage_prefill_m89x_runtime mage_prefill_m89x_runtime.cpp]
add_files -tb [file join $root hls mage_prefill_m89x_runtime tb_m132_m120_fifo_backpressure_rtl.cpp] \
    -cflags "-I[file join $root hls mage_prefill_m89x_runtime]"
open_solution -reset hls -flow_target vivado
set_part {xck26-sfvc784-2LV-c}
create_clock -period 4.8 -name default
set_clock_uncertainty 1.3
config_compile -pipeline_loops 0

csim_design -clean
csynth_design
# Randomized stalls apply to the top-level AXI interfaces.  The test fixture
# simultaneously forces the result FIFO to its legal maximum occupancy.
cosim_design -rtl verilog -random_stall -trace_level none
exit

