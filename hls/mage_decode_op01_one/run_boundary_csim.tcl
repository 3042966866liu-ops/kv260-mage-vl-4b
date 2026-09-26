set root {T:/}
cd $root
set project [file join $root tmp op01_decode_one_boundary_csim_02]
if {[file exists $project]} {error "Refuse existing project"}
open_project $project
set_top op01_decode_one_kernel
add_files [file join $root hls mage_decode_op01_one decode_one.cpp]
add_files -tb [file join $root hls mage_decode_op01_one tb_boundary.cpp]
open_solution hls -flow_target vivado
set_part {xck26-sfvc784-2LV-c}
create_clock -period 4.8 -name default
set_clock_uncertainty 1.3
config_compile -pipeline_loops 0
csim_design
exit
