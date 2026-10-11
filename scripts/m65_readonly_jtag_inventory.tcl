set output_dir [file normalize "tmp/m65_readonly_jtag_inventory"]
file mkdir $output_dir

open_hw_manager
connect_hw_server -allow_non_jtag
set targets [get_hw_targets]
puts "M65_JTAG_TARGET_COUNT=[llength $targets]"
foreach target $targets {
    puts "M65_JTAG_TARGET=[get_property NAME $target]"
}

if {[llength $targets] > 0} {
    if {[catch {open_hw_target [lindex $targets 0]} open_error]} {
        puts "M65_JTAG_OPEN_FAIL=$open_error"
        puts "M65_JTAG_DEVICE_COUNT=0"
    } else {
        set devices [get_hw_devices]
        puts "M65_JTAG_DEVICE_COUNT=[llength $devices]"
        foreach device $devices {
            puts "M65_JTAG_DEVICE=[get_property NAME $device]"
            puts "M65_JTAG_PART=[get_property PART $device]"
        }
        close_hw_target
    }
} else {
    puts "M65_JTAG_NO_TARGET"
}

disconnect_hw_server
close_hw_manager
exit 0
