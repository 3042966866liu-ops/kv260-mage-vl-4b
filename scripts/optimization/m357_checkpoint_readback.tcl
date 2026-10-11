# Independent readback only; no source, checkpoint or shell modification.
set root [file normalize [lindex $argv 0]]
set out [file normalize [lindex $argv 1]]
foreach ip {qwen25_mixed_gs_reset_sync_0 qwen25_mixed_gs_sc_s2mm_0} {
 set dcp [file join $root tmp m357_shell_01 mage_m120_m89x2_highddr.runs ${ip}_synth_1 ${ip}.dcp]
 open_checkpoint $dcp
 if {[get_property PART [current_design]] ne "xck26-sfvc784-2LV-c"} {error "Readback part differs"}
 set blackboxes [get_cells -hier -quiet -filter {IS_BLACKBOX == 1}]
 if {[llength $blackboxes] != 0} {error "Unresolved readback black boxes"}
 report_utilization -file [file join $out ${ip}_readback_utilization.rpt]
 set fd [open [file join $out ${ip}_readback.txt] w]
 puts $fd "PART=[get_property PART [current_design]]"
 puts $fd "BLACKBOXES=[llength $blackboxes]"
 foreach port [lsort [get_ports]] {puts $fd "PORT=$port DIRECTION=[get_property DIRECTION $port]"}
 puts $fd "PRIMITIVES=[llength [get_cells -hier -filter {IS_PRIMITIVE == 1}]]"
 close $fd
 close_design
}
puts "M357_AUXILIARY_CHECKPOINT_READBACK_PASS"
exit
