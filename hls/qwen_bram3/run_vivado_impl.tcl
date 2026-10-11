set project_file "C:/Users/30429/qbram3/v3/qwen25_mixed_gs.xpr"
set ip_repo "C:/Users/30429/qbram3/hls/hls/impl/ip"
set output_dir "Q:/tmp/qwen-bram3-overlay"

file mkdir $output_dir
open_project $project_file
set_property ip_repo_paths [list $ip_repo] [current_project]
update_ip_catalog -rebuild

set bd_files [get_files -quiet *.bd]
if {[llength $bd_files] != 1} {
    error "Expected exactly one block design, found [llength $bd_files]"
}
set bd [lindex $bd_files 0]
open_bd_design $bd

# Block-design IP instances are materialized only after the BD is opened.
set kernel_ips [get_ips -quiet qwen25_mixed_gs_qwen25_mixed_gs_macro_0_0]
if {[llength $kernel_ips] != 1} {
    error "Expected exactly one Qwen HLS IP, found [llength $kernel_ips]"
}
puts "QWEN_VIVADO_KERNEL_IP=[get_property NAME $kernel_ips]"
upgrade_ip $kernel_ips
puts "QWEN_VIVADO_KERNEL_IP_UPGRADE=COMPLETE"

validate_bd_design
save_bd_design
generate_target all $bd

reset_run synth_1
launch_runs impl_1 -to_step write_bitstream -jobs 8
wait_on_run impl_1
set impl_status [get_property STATUS [get_runs impl_1]]
puts "QWEN_VIVADO_IMPL_STATUS=$impl_status"
if {![string match "*Complete*" $impl_status]} {
    error "Implementation did not complete: $impl_status"
}

open_run impl_1
report_utilization -file "$output_dir/utilization.rpt"
report_timing_summary -delay_type min_max -report_unconstrained \
    -check_timing_verbose -max_paths 20 -file "$output_dir/timing_summary.rpt"
report_drc -file "$output_dir/drc.rpt"
report_route_status -file "$output_dir/route_status.rpt"

set setup_path [get_timing_paths -quiet -delay_type max -max_paths 1 -nworst 1]
set hold_path [get_timing_paths -quiet -delay_type min -max_paths 1 -nworst 1]
if {[llength $setup_path] != 1 || [llength $hold_path] != 1} {
    error "Unable to obtain setup/hold timing paths"
}
set wns [get_property SLACK $setup_path]
set whs [get_property SLACK $hold_path]
puts "QWEN_VIVADO_WNS=$wns"
puts "QWEN_VIVADO_WHS=$whs"
if {$wns < 0.0 || $whs < 0.0} {
    error "Timing failed: WNS=$wns WHS=$whs"
}

write_hw_platform -fixed -include_bit -force \
    -file "$output_dir/qwen25_mixed_gs.xsa"
puts "QWEN_BRAM3_VIVADO_RESULT=PASS"
close_project
exit
