set root {T:/}
cd $root
set project [file join $root tmp op01_decode_one_csim]
if {[file exists $project]} {error "Refuse to overwrite existing candidate project"}
set fixture [file join $root deployment mage_vl4b artifacts m128_m120_real_record_csim_fixture.bin]
if {![file isfile $fixture]} {error "Missing frozen M128 real-record fixture"}
set ::env(M128_FIXTURE_PATH) $fixture
open_project $project
set_top op01_decode_one_kernel
add_files [file join $root hls mage_decode_op01_one decode_one.cpp]
add_files -tb [file join $root hls mage_decode_op01_one tb_decode_one.cpp]
open_solution hls -flow_target vivado
set_part {xck26-sfvc784-2LV-c}
create_clock -period 4.8 -name default
set_clock_uncertainty 1.3
config_compile -pipeline_loops 0
csim_design
exit
