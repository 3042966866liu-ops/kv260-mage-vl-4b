set root {C:/Users/30429/Desktop/TELLME~1}
if {![file isdirectory $root]} {
  error "M133 fixed workspace path is missing: $root"
}
puts "M133_WORKSPACE_ROOT=$root"
cd $root
set project m133_m120_max_descriptor_hls

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

csim_design -clean
csynth_design
cosim_design -rtl verilog -trace_level none
exit

