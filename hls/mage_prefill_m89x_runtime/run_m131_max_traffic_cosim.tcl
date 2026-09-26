# Vitis HLS 2026.1 mis-normalizes this machine's long Desktop path while
# creating a project.  The verified DOS short name addresses the same existing
# workspace and avoids that launcher defect; no second workspace is created.
set root {C:/Users/30429/Desktop/TELLME~1}
if {![file isdirectory $root]} {
  error "M131 fixed workspace path is missing: $root"
}
puts "M131_WORKSPACE_ROOT=$root"
cd $root
set project m131_m120_m89x2_hls

open_project -reset $project
set_top m89x_runtime_kernel
add_files [file join $root hls mage_prefill_m89x_runtime mage_prefill_m89x_runtime.cpp]
add_files -tb [file join $root hls mage_prefill_m89x_runtime tb_m131_m120_max_traffic_rtl.cpp] \
    -cflags "-I[file join $root hls mage_prefill_m89x_runtime]"
open_solution -reset hls -flow_target vivado
set_part {xck26-sfvc784-2LV-c}
create_clock -period 4.8 -name default
set_clock_uncertainty 1.3
config_compile -pipeline_loops 0

# Compile and execute the exact max-traffic fixture before spending time on
# synthesis, so any fixture/header defect fails early.
csim_design -clean
csynth_design
# Vitis HLS inserts randomized stalls on the top-level AXI interfaces.  This
# is the required backpressure coverage, not a CSim-only stream check.
cosim_design -rtl verilog -random_stall -trace_level port
exit
