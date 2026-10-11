# M84 single-IP OOC gate. This script is strictly local: it has no board,
# platform, boot image, SD-card, UART or network command.
set workspace_root "C:/Users/30429/Desktop/TeLLMe_FPGA_2026"
set project_dir "D:/TeLLMe_FPGA_2026/m84_three_shard_vivado_ooc"
set ip_repo "D:/TeLLMe_FPGA_2026/m84_three_shard_lane_hls/hls/impl/ip"
set report_dir "$workspace_root/deployment/mage_vl4b/m84_three_shard_vivado_ooc"
file mkdir $report_dir

create_project -force m84_three_shard_ooc $project_dir -part xck26-sfvc784-2LV-c
set_property ip_repo_paths [list $ip_repo] [current_project]
update_ip_catalog
create_ip -vlnv xilinx.com:hls:mage_m84_three_shard_lane:1.0 -module_name m84_three_shard_ooc
generate_target all [get_ips m84_three_shard_ooc]
create_ip_run [get_ips m84_three_shard_ooc]
set run_name m84_three_shard_ooc_synth_1
launch_runs $run_name -jobs 8
wait_on_run $run_name
set run_status [get_property STATUS [get_runs $run_name]]
if {[string first "synth_design Complete" $run_status] < 0} {
    puts "M84_SINGLE_IP_VIVADO_OOC_FAIL status=$run_status"
    exit 1
}
open_run $run_name
report_utilization -file "$report_dir/utilization.rpt"
report_utilization -hierarchical -file "$report_dir/utilization_hierarchical.rpt"
report_timing_summary -delay_type max -report_unconstrained -check_timing_verbose \
    -max_paths 10 -file "$report_dir/timing_summary.rpt"
report_drc -file "$report_dir/drc.rpt"
write_checkpoint -force "$project_dir/m84_three_shard_ooc.dcp"
puts "M84_SINGLE_IP_VIVADO_OOC_PASS status=$run_status"
exit 0
