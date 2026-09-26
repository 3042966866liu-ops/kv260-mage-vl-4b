# Use a clean sibling project because an interrupted XSIM run leaves the
# original solution's generated CoSim directory non-reentrant.  The original
# M131 directory remains untouched as failure evidence.  This gate isolates
# the exact legal M120 maximum chain (10 descriptors, 40 groups, 512
# rows/shard) from randomized interface stalls; M132 supplies complementary
# random-stall and maximum-FIFO-occupancy evidence.
set root {C:/Users/30429/Desktop/TELLME~1}
if {![file isdirectory $root]} {
  error "M131 fixed workspace path is missing: $root"
}
puts "M131_WORKSPACE_ROOT=$root"
cd $root

set project m131b_m120_max_traffic_nostall_hls
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

csynth_design
cosim_design -rtl verilog -trace_level none
exit
