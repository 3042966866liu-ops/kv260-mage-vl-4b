set ready_path /apatb_m89x_runtime_kernel_top/svtb_top/svr_rx_if/ready
add_force $ready_path 0
run 2880us
if {[get_value -radix unsigned /apatb_m89x_runtime_kernel_top/rx_TREADY] != 0} {error "Shared VIP output backpressure not effective"}
puts "M357_SHARED_VIP_OUTPUT_HOLD_VERIFIED cycles=600000"
remove_forces $ready_path
run all
quit
