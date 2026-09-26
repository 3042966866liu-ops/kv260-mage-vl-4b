set root {T:/}
cd $root
set project [file join $root tmp op01_decode_one_shapes]
set report [file join $project hls csim report op01_decode_one_kernel_csim.log]
set f [open $report r]
set data [read $f]
close $f
if {[string first "OP01_SHAPE_TRANSACTIONS_PASS" $data] < 0} {error "Missing prior numerical PASS"}
open_project $project
open_solution hls
cosim_design -rtl verilog -random_stall -trace_level none
exit
