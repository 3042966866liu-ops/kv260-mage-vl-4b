set root {C:/Users/30429/Desktop/TELLME~1}
if {![file isdirectory $root]} {
  error "M134 fixed workspace path is missing: $root"
}
cd $root
set project m132_m120_fifo_backpressure_hls
set output_dir [file join $root tmp m120_m89x2_runtime_ip]
file mkdir $output_dir

open_project $project
open_solution hls
export_design -format ip_catalog -rtl verilog \
    -vendor tellme.local -library hls -version 1.0 \
    -output [file join $output_dir m89x_runtime_kernel_m120_m89x2.zip]
puts "M134_M120_M89X2_IP_EXPORT_PASS"
exit

