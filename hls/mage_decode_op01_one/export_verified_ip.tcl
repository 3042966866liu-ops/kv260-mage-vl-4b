# Run only after prepare_decode_one_ip_export.py has verified terminal gates.
# Export synthesized RTL from a NEW project copy; do not rerun CSim/synthesis.
set root {T:/}
cd $root
set project [file join $root tmp op01_decode_one_export]
set guard [file join $project EXPORT_PREREQUISITES.json]
if {![file exists $guard]} {error "Missing verified export preparation"}
if {[file exists [file join $project hls impl]]} {error "Refuse existing export output"}
open_project $project
open_solution hls
export_design -format ip_catalog -output [file join $project op01_decode_one_kernel.zip]
close_project
exit
