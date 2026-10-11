open_project "C:/Users/30429/qbram3/v3/qwen25_mixed_gs.xpr"
set_property ip_repo_paths [list "C:/Users/30429/qbram3/hls/hls/impl/ip"] [current_project]
update_ip_catalog -rebuild
set bd [lindex [get_files -quiet *.bd] 0]
open_bd_design $bd
puts "QWEN_ALL_IPS=[get_ips -quiet *]"
puts "QWEN_ALL_BD_CELLS=[get_bd_cells -quiet *]"
foreach cell [get_bd_cells -quiet *] {
    puts "QWEN_CELL=[get_property NAME $cell] VLNV=[get_property VLNV $cell]"
}
report_ip_status
close_project
exit
