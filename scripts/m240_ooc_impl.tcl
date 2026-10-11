set root "V:"
set ip_root "$root/m240_t64_hls_strict48/solution1/impl/ip"
set project_dir "$root/m240o"
set report_dir "$root/m240_ooc_reports"
set xdc_file "T:/scripts/m240_ooc.xdc"
file mkdir $report_dir

create_project -force m240o $project_dir -part xck26-sfvc784-2LV-c
set_property target_language Verilog [current_project]
set_property simulator_language Mixed [current_project]
set_param general.maxThreads 12

set hls_rtl [glob -nocomplain "$ip_root/hdl/verilog/*.v"]
set subcores [glob -nocomplain "$ip_root/hdl/ip/*/*.xci"]
if {[llength $hls_rtl] == 0 || [llength $subcores] != 6} {
    puts "M240_OOC_INPUT_DISCOVERY_FAIL hls_rtl=[llength $hls_rtl] subcores=[llength $subcores]"
    exit 1
}
foreach source $hls_rtl { read_verilog $source }
foreach subcore $subcores { read_ip $subcore }
generate_target all [get_ips]
read_xdc $xdc_file
set_property source_mgmt_mode None [current_project]
set_property top m240_t64_kernel [get_filesets sources_1]
update_compile_order -fileset sources_1

synth_design -top m240_t64_kernel -part xck26-sfvc784-2LV-c -mode out_of_context -flatten_hierarchy rebuilt
report_utilization -file "$report_dir/post_synth_utilization.rpt"
report_timing_summary -delay_type min_max -report_unconstrained -check_timing_verbose -max_paths 20 -file "$report_dir/post_synth_timing_summary.rpt"
write_checkpoint -force "$report_dir/post_synth.dcp"

opt_design -directive Explore
place_design -directive Explore
phys_opt_design -directive AggressiveExplore
route_design -directive Explore

report_utilization -file "$report_dir/post_route_utilization.rpt"
report_utilization -hierarchical -hierarchical_depth 4 -file "$report_dir/post_route_utilization_hierarchical.rpt"
report_timing_summary -delay_type min_max -report_unconstrained -check_timing_verbose -max_paths 50 -file "$report_dir/post_route_timing_summary.rpt"
report_route_status -file "$report_dir/post_route_status.rpt"
report_design_analysis -congestion -file "$report_dir/post_route_congestion.rpt"
report_drc -file "$report_dir/post_route_drc.rpt"
write_checkpoint -force "$report_dir/m240_t64_post_route.dcp"

set setup_path [get_timing_paths -delay_type max -max_paths 1]
set hold_path [get_timing_paths -delay_type min -max_paths 1]
set wns [expr {[llength $setup_path] == 0 ? "NA" : [get_property SLACK $setup_path]}]
set whs [expr {[llength $hold_path] == 0 ? "NA" : [get_property SLACK $hold_path]}]
set route_status [get_property ROUTE_STATUS [current_design]]
puts "M240_T64_VIVADO_OOC_COMPLETE wns=$wns whs=$whs route_status={$route_status}"
if {$wns eq "NA" || $whs eq "NA" || $wns < 0.0 || $whs < 0.0} {
    puts "M240_T64_VIVADO_OOC_TIMING_FAIL"
    exit 2
}
puts "M240_T64_VIVADO_OOC_PASS"
exit 0
