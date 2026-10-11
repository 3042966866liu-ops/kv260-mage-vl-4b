set project_root "D:/TeLLMe_FPGA_2026/m84_three_shard_lane_hls"
set output_zip "C:/Users/30429/Desktop/TeLLMe_FPGA_2026/tmp/m84_three_shard_lane_ip/m84_three_shard_lane.zip"
open_project $project_root
open_solution hls
file mkdir [file dirname $output_zip]
config_export -format ip_catalog -output $output_zip -rtl verilog \
    -ipname mage_m84_three_shard_lane -display_name mage_m84_three_shard_lane
export_design
puts "M84_IP_EXPORT_PASS"
exit
