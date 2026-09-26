set root "T:"
set project_root "$root/tmp/m75b_t6rt_hls"
set output_zip "$root/tmp/m75b_t6rt_ip/m75b_t6rt.zip"
open_project $project_root
open_solution hls
file mkdir [file dirname $output_zip]
config_export -format ip_catalog -output $output_zip -rtl verilog -ipname m75b_t6rt -display_name m75b_t6rt
export_design
puts "M75B_T6RT_EXPORT=PASS"
exit
