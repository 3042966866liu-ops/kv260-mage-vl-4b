set workspace_root "C:/Users/30429/Desktop/TeLLMe_FPGA_2026"
set project_dir "$workspace_root/tmp/v"
set report_dir "$workspace_root/deployment/mage_vl4b/m89v_combined_vivado_ooc"
set ip_repo "$workspace_root/m89v_fullgroup_chain_hls_strict48/hls/impl/ip"
set rtl_file "$workspace_root/rtl/m89u_axis_tlast_coalescer.v"
set wrapper_file "$workspace_root/tmp/m89v_combined_vivado_ooc/m89v_combined_wrapper.v"
set xdc_file "$workspace_root/scripts/m89v_combined_vivado_ooc.xdc"

foreach required [list $ip_repo $rtl_file $wrapper_file $xdc_file] {
    if {![file exists $required]} { puts "M89V_COMBINED_INPUT_MISSING path=$required"; exit 1 }
}
file mkdir $report_dir
create_project -force v $project_dir -part xck26-sfvc784-2LV-c
set_property target_language Verilog [current_project]
set_property simulator_language Mixed [current_project]
set_param general.maxThreads 8
set ip_hls_rtl [glob -nocomplain "$ip_repo/hdl/verilog/*.v"]
set ip_subcores [glob -nocomplain "$ip_repo/hdl/ip/*/*.xci"]
if {[llength $ip_hls_rtl] == 0 || [llength $ip_subcores] != 4} {
    puts "M89V_IP_OUTPUT_DISCOVERY_FAIL hls_rtl=[llength $ip_hls_rtl] subcores=[llength $ip_subcores]"
    exit 1
}
foreach source [concat $ip_hls_rtl [list $rtl_file $wrapper_file]] { read_verilog $source }
foreach subcore $ip_subcores { read_ip $subcore }
generate_target all [get_ips]
read_xdc $xdc_file
set_property source_mgmt_mode None [current_project]
set_property top m89v_combined_wrapper [get_filesets sources_1]
update_compile_order -fileset sources_1
synth_design -top m89v_combined_wrapper -part xck26-sfvc784-2LV-c -mode out_of_context
report_utilization -file "$report_dir/utilization.rpt"
report_utilization -hierarchical -file "$report_dir/utilization_hierarchical.rpt"
report_timing_summary -delay_type max -report_unconstrained -check_timing_verbose -max_paths 20 -file "$report_dir/timing_summary.rpt"
report_drc -file "$report_dir/drc.rpt"
write_checkpoint -force "$report_dir/m89v_combined_ooc.dcp"
set worst_path [get_timing_paths -delay_type max -max_paths 1]
set wns [expr {[llength $worst_path] == 0 ? "NA" : [get_property SLACK $worst_path]}]
puts "M89V_COMBINED_VIVADO_OOC_PASS wns=$wns"
exit 0
