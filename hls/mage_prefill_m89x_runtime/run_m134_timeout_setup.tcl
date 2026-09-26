set root {C:/Users/30429/Desktop/TELLME~1}
if {![file isdirectory $root]} {
  error "M134 timeout workspace path is missing: $root"
}
cd $root
set project m134_m120_timeout_expected_failure_hls

open_project -reset $project
set_top m89x_runtime_kernel
add_files [file join $root hls mage_prefill_m89x_runtime mage_prefill_m89x_runtime.cpp]
add_files -tb [file join $root hls mage_prefill_m89x_runtime tb_m133_m120_max_descriptor_rtl.cpp] \
    -cflags "-I[file join $root hls mage_prefill_m89x_runtime]"
open_solution -reset hls -flow_target vivado
set_part {xck26-sfvc784-2LV-c}
create_clock -period 4.8 -name default
set_clock_uncertainty 1.3
config_compile -pipeline_loops 0

csynth_design
# Generate a private RTL simulator tree but do not execute it yet.  The
# generated UVM timeout is then reduced in this isolated project and must
# terminate the otherwise passing M133 transaction before ap_done.
cosim_design -rtl verilog -trace_level none -setup
puts "M134_TIMEOUT_SIMULATOR_SETUP_PASS"
exit

