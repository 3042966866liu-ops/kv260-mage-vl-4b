set target {xck26-sfvc784-2LV-c}
puts "M89X2_VIVADO_VERSION=[version -short]"
set exact [get_parts -quiet $target]
puts "M89X2_VIVADO_EXACT_PART_COUNT=[llength $exact]"
puts "M89X2_VIVADO_EXACT_PARTS=$exact"
set family [get_parts -quiet *xck26*]
puts "M89X2_VIVADO_XCK26_PART_COUNT=[llength $family]"
puts "M89X2_VIVADO_XCK26_PARTS=$family"
if {[llength $exact] != 1} {
  error "M89X2_VIVADO_TARGET_PART_NOT_INSTALLED"
}
create_project -in_memory -part $target m89x2_part_probe
puts "M89X2_VIVADO_CREATE_PROJECT_PASS part=[get_property PART [current_project]]"
close_project
exit
