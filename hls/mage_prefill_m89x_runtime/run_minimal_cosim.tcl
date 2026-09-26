set root [file normalize [pwd]]
open_project [file join $root m89x_runtime_hls_strict48]
set_top m89x_runtime_kernel
add_files -tb [file join $root hls mage_prefill_m89x_runtime tb_m89x_minimal_rtl.cpp] -cflags "-I[file join $root hls mage_prefill_m89x_runtime]"
open_solution hls -flow_target vivado
cosim_design -rtl verilog -trace_level port
exit
