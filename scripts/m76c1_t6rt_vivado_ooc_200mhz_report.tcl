set workspace_root "C:/Users/30429/Desktop/TeLLMe_FPGA_2026"
set checkpoint "$workspace_root/tmp/m76c1_t6rt_vivado/m76c1_t6rt_ooc.dcp"
set report_dir "$workspace_root/deployment/mage_vl4b/m76c1_t6rt_vivado_ooc"
file mkdir $report_dir

open_checkpoint $checkpoint
catch {delete_clocks [get_clocks *]}
create_clock -name ap_clk -period 5.000 [get_ports ap_clk]
report_timing_summary -delay_type max -report_unconstrained -check_timing_verbose \
    -max_paths 10 -file "$report_dir/timing_summary_200mhz.rpt"
puts "M76C1_T6RT_VIVADO_OOC_200MHZ_REPORT_DONE"
exit 0
