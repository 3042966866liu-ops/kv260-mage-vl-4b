set ready /apatb_m89x_runtime_kernel_top/svtb_top/svr_rx_if/ready
set ar /apatb_m89x_runtime_kernel_top/svtb_top/axi_w0_if/ARREADY
set dut /apatb_m89x_runtime_kernel_top
add_force $ready 0
add_force $ar 0
for {set i 0} {$i < 100} {incr i} {
 run 4.8us
 if {[get_value -radix unsigned $dut/w0_ARVALID] == 1} {break}
}
if {[get_value -radix unsigned $dut/w0_ARVALID] != 1} {error "No actual pending AR"}
run 48us
if {[get_value -radix unsigned $dut/w0_ARREADY] != 0} {error "AR hold failed"}
puts "M441MAX_SHARED_VIP_WEIGHT_AR_HOLD_VERIFIED cycles=10000"
remove_forces $ar
for {set i 0} {$i < 200} {incr i} {
 run 48us
 if {[get_value -radix unsigned $dut/rx_TVALID] == 1} {break}
}
if {[get_value -radix unsigned $dut/rx_TVALID] != 1 || [get_value -radix unsigned $dut/rx_TREADY] != 0} {error "No actual held RX valid"}
run 480us
puts "M441MAX_SHARED_VIP_OUTPUT_HOLD_VERIFIED cycles=100000"
remove_forces $ready
run all
quit
