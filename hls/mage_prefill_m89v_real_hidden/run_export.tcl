set root [file normalize [pwd]]
set project [file join $root m89v_fullgroup_chain_hls_strict48]
set output_zip [file join $root tmp m89v_fullgroup_chain_ip m89v_fullgroup_chain.zip]
open_project $project
open_solution hls
file mkdir [file dirname $output_zip]
config_export -format ip_catalog -output $output_zip -rtl verilog \
    -vendor tellme.local -library hls -ipname m89v_fullgroup_chain \
    -display_name m89v_fullgroup_chain
export_design
puts "M89V_IP_EXPORT_PASS output=$output_zip"
exit
