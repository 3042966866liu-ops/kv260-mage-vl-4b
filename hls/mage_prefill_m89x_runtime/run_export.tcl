if {![info exists ::env(TELLME_WORKSPACE_ROOT)] || $::env(TELLME_WORKSPACE_ROOT) eq ""} {
    error "TELLME_WORKSPACE_ROOT must be an explicit absolute workspace path"
}
set root $::env(TELLME_WORKSPACE_ROOT)
puts "M89X_EXPORT_WORKSPACE_ROOT=$root"
set project [file join $root m89x_runtime_hls_strict48]
set output_zip [file join $root tmp m89x_runtime_ip m89x_runtime_kernel.zip]
open_project $project
open_solution hls
file mkdir [file dirname $output_zip]
export_design -format ip_catalog -output $output_zip \
    -vendor tellme.local -library hls -ipname m89x_runtime_kernel \
    -display_name m89x_runtime_kernel
exit
