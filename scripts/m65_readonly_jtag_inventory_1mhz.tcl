set output_dir [file normalize "tmp/m65_readonly_jtag_inventory_1mhz"]
file mkdir $output_dir
open_hw_manager
connect_hw_server -allow_non_jtag
set targets [get_hw_targets]
puts "M65_JTAG_1MHZ_TARGET_COUNT=[llength $targets]"
foreach target $targets {
    puts "M65_JTAG_1MHZ_TARGET=[get_property NAME $target]"
}
if {[llength $targets] > 0} {
    set target [lindex $targets 0]
    if {[catch {set_property PARAM.FREQUENCY 1000000 $target} freq_error]} {
        puts "M65_JTAG_1MHZ_SET_FREQUENCY_FAIL=$freq_error"
    } else {
        puts "M65_JTAG_1MHZ_FREQUENCY=[get_property PARAM.FREQUENCY $target]"
    }
    if {[catch {open_hw_target $target} open_error]} {
        puts "M65_JTAG_1MHZ_OPEN_FAIL=$open_error"
        puts "M65_JTAG_1MHZ_DEVICE_COUNT=0"
    } else {
        set devices [get_hw_devices]
        puts "M65_JTAG_1MHZ_DEVICE_COUNT=[llength $devices]"
        foreach device $devices {
            puts "M65_JTAG_1MHZ_DEVICE=[get_property NAME $device]"
            puts "M65_JTAG_1MHZ_PART=[get_property PART $device]"
        }
        close_hw_target
    }
} else {
    puts "M65_JTAG_1MHZ_NO_TARGET"
}
disconnect_hw_server
close_hw_manager
exit 0
