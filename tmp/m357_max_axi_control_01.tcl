set ready_path /apatb_m89x_runtime_kernel_top/svtb_top/svr_rx_if/ready
set arready_path /apatb_m89x_runtime_kernel_top/svtb_top/axi_w0_if/ARREADY
add_force $ready_path 0
add_force $arready_path 0
run 48us
if {[get_value -radix unsigned /apatb_m89x_runtime_kernel_top/w0_ARREADY] != 0} {error "Shared AXI ARREADY hold not effective"}
if {[get_value -radix unsigned /apatb_m89x_runtime_kernel_top/w0_ARVALID] != 1} {error "No real pending AXI address under hold"}
puts "M357_SHARED_VIP_WEIGHT_AR_HOLD_VERIFIED cycles=10000"
remove_forces $arready_path
run 2832us
if {[get_value -radix unsigned /apatb_m89x_runtime_kernel_top/rx_TREADY] != 0} {error "Shared VIP output backpressure not effective"}
puts "M357_SHARED_VIP_OUTPUT_HOLD_VERIFIED cycles=600000"
remove_forces $ready_path
run all
quit
