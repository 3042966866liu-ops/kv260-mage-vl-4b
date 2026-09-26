set root {T:/}
cd $root
set project [file join $root tmp op01_decode_one_shapes]
if {![file exists [file join $project REUSED_SYNTHESIS.json]]} {error "Missing verified clone"}
open_project $project
open_solution hls
remove_files [file join $root hls mage_decode_op01_one tb_rtl.cpp]
add_files -tb [file join $root hls mage_decode_op01_one tb_rtl_shapes.cpp]
csim_design -clean
cosim_design -rtl verilog -random_stall -trace_level none
exit
