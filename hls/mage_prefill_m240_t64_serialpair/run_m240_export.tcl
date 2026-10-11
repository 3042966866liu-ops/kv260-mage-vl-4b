set project "V:/m240_t64_hls_strict48"
set output_zip "V:/m240_t64_ip/m240_t64_kernel.zip"
open_project $project
open_solution solution1
file mkdir [file dirname $output_zip]
export_design -format ip_catalog -output $output_zip -rtl verilog \
    -vendor tellme.local -library hls -ipname m240_t64_kernel \
    -display_name m240_t64_kernel
puts "M240_T64_IP_EXPORT_PASS output=$output_zip"
exit
