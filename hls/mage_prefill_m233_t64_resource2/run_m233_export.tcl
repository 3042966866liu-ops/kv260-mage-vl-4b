set project "D:/CodexHome/visualizations/2026/09/01/01a05cf2-5674-7841-b1b8-a9e9eec650fb/m233_t64_hls_strict48"
set output_zip "D:/CodexHome/visualizations/2026/09/01/01a05cf2-5674-7841-b1b8-a9e9eec650fb/m233_t64_ip/m233_t64_kernel.zip"
open_project $project
open_solution solution1
file mkdir [file dirname $output_zip]
export_design -format ip_catalog -output $output_zip -rtl verilog \
    -vendor tellme.local -library hls -ipname m233_t64_kernel \
    -display_name m233_t64_kernel
puts "M233_T64_IP_EXPORT_PASS output=$output_zip"
exit
