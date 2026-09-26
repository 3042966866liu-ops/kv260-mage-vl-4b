set root [file normalize [pwd]]
set project [file join $root m89t_scale_chain_hls_strict48]
set output_zip [file join $root tmp m89t_scale_chain_ip m89t_scale_chain.zip]
open_project $project
open_solution hls
file mkdir [file dirname $output_zip]
config_export -format ip_catalog -output $output_zip -rtl verilog \
    -vendor tellme.local -library hls -ipname m89t_scale_chain \
    -display_name m89t_scale_chain
export_design
puts "M89T_IP_EXPORT_PASS output=$output_zip"
exit
