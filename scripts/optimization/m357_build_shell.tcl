# Runs only via the guarded host driver, in a fresh candidate project.
set root [file normalize [lindex $argv 0]]
set inputs [file join $root tmp m357_shell_inputs_01]
set project_dir [file join $root tmp m357_shell_01]
if {[file exists $project_dir]} {error "Existing candidate shell directory: inspect only"}
set source_bd [file join $inputs qwen25_mixed_gs.bd]
set candidate_repo [file join $inputs ip]
create_project mage_m120_m89x2_highddr $project_dir -part xck26-sfvc784-2LV-c
set_property board_part xilinx.com:kv260_som:part0:1.4 [current_project]
set_property ip_repo_paths [list $candidate_repo] [current_project]
update_ip_catalog
set def [get_ipdefs -all xilinx.com:hls:m89x_runtime_kernel:1.0]
if {[llength $def] != 1} {error "Candidate IP definition not unique"}
set xml_file [file normalize [get_property XML_FILE_NAME $def]]
if {$xml_file ne [file normalize [file join $candidate_repo component.xml]]} {
    error "Unexpected IP catalog source: $xml_file"
}
set reports [file join $project_dir out]
file mkdir $reports
report_property -all $def -file [file join $reports candidate_ip_definition.rpt]
set bd_dir [file join $project_dir mage_m120_m89x2_highddr.srcs sources_1 bd qwen25_mixed_gs]
file mkdir $bd_dir
set candidate_bd [file join $bd_dir qwen25_mixed_gs.bd]
file copy $source_bd $candidate_bd
add_files -norecurse $candidate_bd
open_bd_design $candidate_bd
set kernel [get_bd_cells mage_m120_m89x2_0]
if {[get_property VLNV $kernel] ne "xilinx.com:hls:m89x_runtime_kernel:1.0"} {error "Wrong kernel IP"}
validate_bd_design
save_bd_design
generate_target all [get_files $candidate_bd]
make_wrapper -files [get_files $candidate_bd] -top -import
set_property top qwen25_mixed_gs_wrapper [current_fileset]
update_compile_order -fileset sources_1
report_ip_status -file [file join $reports ip_status.rpt]
launch_runs synth_1 -jobs 4
wait_on_run synth_1
if {[get_property PROGRESS [get_runs synth_1]] ne "100%"} {error "Synthesis incomplete"}
open_run synth_1
report_utilization -file [file join $reports synth_utilization.rpt]
report_timing_summary -delay_type min_max -report_unconstrained -check_timing_verbose -file [file join $reports synth_timing.rpt]
close_design
launch_runs impl_1 -to_step route_design -jobs 4
wait_on_run impl_1
if {![string match "*route_design Complete*" [get_property STATUS [get_runs impl_1]]]} {error "Route incomplete"}
open_run impl_1
report_route_status -file [file join $reports route_status.rpt]
report_utilization -file [file join $reports impl_utilization.rpt]
report_timing_summary -delay_type min_max -report_unconstrained -check_timing_verbose -max_paths 20 -file [file join $reports impl_timing.rpt]
report_drc -file [file join $reports impl_drc.rpt]
set setup [get_timing_paths -delay_type max -max_paths 1]
set hold [get_timing_paths -delay_type min -max_paths 1]
if {[llength $setup] != 1 || [llength $hold] != 1} {error "Timing endpoints missing"}
set wns [get_property SLACK $setup]
set whs [get_property SLACK $hold]
set unrouted [llength [get_nets -hier -filter {ROUTE_STATUS == UNROUTED || ROUTE_STATUS == PARTIAL}]]
set fd [open [file join $reports shell_route_receipt.txt] w]
puts $fd "WNS_NS=$wns"
puts $fd "WHS_NS=$whs"
puts $fd "UNROUTED_NETS=$unrouted"
close $fd
if {$wns < 0 || $whs < 0 || $unrouted != 0} {error "Candidate shell timing/route rejected"}
write_checkpoint [file join $reports candidate_routed.dcp]
write_bitstream [file join $reports m357_t32.bit]
write_hw_platform -fixed -include_bit -file [file join $reports m357_t32.xsa]
puts "M357_FULL_SHELL_ROUTED timing_pass=1 build=0x4D333537"
close_project
exit
