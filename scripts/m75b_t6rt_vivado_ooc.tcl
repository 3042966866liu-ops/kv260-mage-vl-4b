set workspace_root "C:/Users/30429/Desktop/TeLLMe_FPGA_2026"
set project_dir "$workspace_root/tmp/m75b_t6rt_vivado"
set ip_repo "$workspace_root/tmp/m75b_t6rt_ip/ip_repo"
set report_dir "$workspace_root/deployment/mage_vl4b/m75b_t6rt_vivado_ooc"
file mkdir $report_dir

create_project -force m75b_t6rt_ooc $project_dir -part xck26-sfvc784-2LV-c
set_property ip_repo_paths [list $ip_repo] [current_project]
update_ip_catalog
create_ip -vlnv xilinx.com:hls:m75b_t6rt:1.0 -module_name m75b_t6rt_ooc
generate_target all [get_ips m75b_t6rt_ooc]
create_ip_run [get_ips m75b_t6rt_ooc]
set run_name m75b_t6rt_ooc_synth_1
launch_runs $run_name -jobs 8
wait_on_run $run_name
set run_status [get_property STATUS [get_runs $run_name]]
if {[string first "synth_design Complete" $run_status] < 0} {
    puts "M75B_T6RT_VIVADO_OOC_FAIL status=$run_status"
    exit 1
}
open_run $run_name
report_utilization -file "$report_dir/utilization.rpt"
report_utilization -hierarchical -file "$report_dir/utilization_hierarchical.rpt"
report_timing_summary -delay_type max -report_unconstrained -check_timing_verbose \
    -max_paths 10 -file "$report_dir/timing_summary.rpt"
report_drc -file "$report_dir/drc.rpt"
write_checkpoint -force "$project_dir/m75b_t6rt_ooc.dcp"
puts "M75B_T6RT_VIVADO_OOC_PASS status=$run_status"
exit 0
