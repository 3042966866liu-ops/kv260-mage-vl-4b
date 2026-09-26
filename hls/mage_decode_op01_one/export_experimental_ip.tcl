# Explicit experimental path; never substitutes for verified export prerequisites.
cd T:/
set project T:/tmp/op01_decode_one_experimental_export
if {![file exists [file join $project EXPERIMENTAL_PREREQUISITES.json]]} {error "Missing experimental identity evidence"}
if {[file exists [file join $project hls impl]]} {error "Refuse existing export output"}
open_project $project
open_solution hls
# Export trace proves cosim_export_main checks impl top before RTL staging.
# Seed complete synthesized RTL without editing any functional Verilog/VHDL.
file mkdir [file join $project hls impl]
foreach language {verilog vhdl} {
    set src [file join $project hls syn $language]
    if {![file isdirectory $src]} {error "Missing synthesized RTL: $src"}
    file copy $src [file join $project hls impl $language]
}
config_rtl -deadlock_detection none
if {[catch {export_design -format ip_catalog -output [file join $project op01_decode_one_kernel.zip]} export_error export_options]} {
    puts stderr "EXPERIMENTAL_EXPORT_ERROR: $export_error"
    puts stderr "EXPERIMENTAL_EXPORT_OPTIONS: $export_options"
    if {[dict exists $export_options -errorinfo]} {puts stderr [dict get $export_options -errorinfo]}
    exit 1
}
close_project
exit
