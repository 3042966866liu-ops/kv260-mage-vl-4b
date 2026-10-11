set project_dir "V:/m243_t64_hls_strict48"
open_project $project_dir
set_top m243_t64_kernel
open_solution solution1
export_design -format ip_catalog -rtl verilog -output "V:/m243_t64_ip/m243_t64_kernel.zip"
exit
