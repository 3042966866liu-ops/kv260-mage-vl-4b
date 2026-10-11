set ready /apatb_m89x_runtime_kernel_top/svtb_top/svr_rx_if/ready
set ar /apatb_m89x_runtime_kernel_top/svtb_top/axi_w0_if/ARREADY
set core /apatb_m89x_runtime_kernel_top/AESL_inst_m89x_runtime_kernel/grp_m89x_four_fu_404
add_force $ready 0
add_force $ar 0
run 48us
if {[get_value -radix unsigned /apatb_m89x_runtime_kernel_top/w0_ARREADY] != 0 || [get_value -radix unsigned /apatb_m89x_runtime_kernel_top/w0_ARVALID] != 1} {error "Actual pending AXI hold missing"}
puts "M441MAX_SHARED_VIP_WEIGHT_AR_HOLD_VERIFIED cycles=10000"
remove_forces $ar
for {set i 1} {$i <= 9} {incr i} {run 48us; puts "M441MAX_CHUNK_PROGRESS time=[current_time]"}
if {[get_value -radix unsigned /apatb_m89x_runtime_kernel_top/rx_TREADY] != 0 || [get_value -radix unsigned /apatb_m89x_runtime_kernel_top/rx_TVALID] != 1} {error "Actual held valid output missing"}
set full 0
foreach name {result_num_data_valid result_1_num_data_valid result_2_num_data_valid result_3_num_data_valid} {
 set occupancy [get_value -radix unsigned $core/$name]
 puts "M441MAX_FIFO_HOLD_SNAPSHOT name=$name occupancy=$occupancy"
 if {$occupancy > 8192} {error "FIFO capacity overflow"}
 if {$occupancy == 8192} {incr full}
}
if {$full < 1} {error "Maximum legal FIFO occupancy not reached before release"}
puts "M441MAX_SHARED_VIP_OUTPUT_HOLD_VERIFIED cycles=100000"
remove_forces $ready
for {set i 1} {$i <= 300} {incr i} {
 run 48us
 puts "M441MAX_CHUNK_PROGRESS time=[current_time] words=[get_value -radix unsigned /m441_max_monitor/words]"
 if {[get_value -radix unsigned /m441_max_monitor/words] == 327680 && [get_value -radix unsigned /m441_max_monitor/lasts] == 1} {break}
}
if {[get_value -radix unsigned /m441_max_monitor/words] != 327680} {error "Bounded maximum cycle budget exceeded"}
run 480ns
quit
