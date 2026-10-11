# Export hardware description only. Original routed DCP and bitstream remain exact.
set root [file normalize [lindex $argv 0]]
set out [file normalize [lindex $argv 1]]
open_project -read_only [file join $root tmp m357_shell_01 mage_m120_m89x2_highddr.xpr]
open_run impl_1
# PYNQ receives the independently SHA-bound .bit and matching .hwh. This XSA
# describes hardware and intentionally does not embed another bitstream.
write_hw_platform -fixed -file [file join $out m357_t32.xsa]
puts "M357_HARDWARE_DESCRIPTION_EXPORT_PASS_ORIGINAL_BIT_UNCHANGED"
close_project
exit
