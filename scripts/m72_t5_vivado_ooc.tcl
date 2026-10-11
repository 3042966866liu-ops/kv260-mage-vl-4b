set root "C:/Users/30429/Desktop/TeLLMe_FPGA_2026"
set project_dir "$root/tmp/m72_t5_vivado"
set ip_repo "$root/tmp/m72_t5_ip/ip_repo"
set report_dir "$root/deployment/mage_vl4b/m72_t5_vivado_ooc"

file mkdir $report_dir
create_project -force m72_t5_ooc $project_dir -part xck26-sfvc784-2LV-c
set_property target_language Verilog [current_project]
set_property ip_repo_paths $ip_repo [current_project]
update_ip_catalog

create_ip -vlnv xilinx.com:hls:mage_prefill_t6_arith:1.0 \
    -module_name mage_prefill_t5_ooc
generate_target all [get_ips mage_prefill_t5_ooc]
create_ip_run [get_ips mage_prefill_t5_ooc]

set run_name mage_prefill_t5_ooc_synth_1
launch_runs $run_name -jobs 6
wait_on_run $run_name
set run_status [get_property STATUS [get_runs $run_name]]

if {![string match "*Complete*" $run_status]} {
    puts "M72_VIVADO_OOC_FAIL status=$run_status"
    exit 1
}

open_run $run_name
report_utilization -hierarchical -file "$report_dir/utilization_hierarchical.rpt"
report_timing_summary -delay_type max -report_unconstrained -check_timing_verbose \
    -max_paths 10 -file "$report_dir/timing_summary.rpt"
report_drc -file "$report_dir/drc.rpt"

puts "M72_VIVADO_OOC_PASS status=$run_status"
exit 0
