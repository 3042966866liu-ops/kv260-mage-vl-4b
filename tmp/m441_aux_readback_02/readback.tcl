open_checkpoint {C:/Users/30429/Desktop/TeLLMe_FPGA_2026/tmp/m441_shell_01/mage_m120_m89x2_highddr.runs/qwen25_mixed_gs_axi_dma_prefill_0_synth_1/qwen25_mixed_gs_axi_dma_prefill_0.dcp}
if {[get_property PART [current_design]] ne "xck26-sfvc784-2LV-c"} {error "Readback part differs"}
set boxes [get_cells -hier -quiet -filter {IS_BLACKBOX == 1}]
if {[llength $boxes] != 0} {error "Readback blackboxes"}
set fd [open {C:/Users/30429/Desktop/TeLLMe_FPGA_2026/tmp/m441_aux_readback_02/qwen25_mixed_gs_axi_dma_prefill_0_readback.txt} w]
puts $fd "PART=[get_property PART [current_design]]"
puts $fd "BLACKBOXES=[llength $boxes]"
puts $fd "PRIMITIVES=[llength [get_cells -hier -filter {IS_PRIMITIVE == 1}]]"
close $fd
close_design
open_checkpoint {C:/Users/30429/Desktop/TeLLMe_FPGA_2026/tmp/m441_shell_01/mage_m120_m89x2_highddr.runs/qwen25_mixed_gs_sc_s2mm_0_synth_1/qwen25_mixed_gs_sc_s2mm_0.dcp}
if {[get_property PART [current_design]] ne "xck26-sfvc784-2LV-c"} {error "Readback part differs"}
set boxes [get_cells -hier -quiet -filter {IS_BLACKBOX == 1}]
if {[llength $boxes] != 0} {error "Readback blackboxes"}
set fd [open {C:/Users/30429/Desktop/TeLLMe_FPGA_2026/tmp/m441_aux_readback_02/qwen25_mixed_gs_sc_s2mm_0_readback.txt} w]
puts $fd "PART=[get_property PART [current_design]]"
puts $fd "BLACKBOXES=[llength $boxes]"
puts $fd "PRIMITIVES=[llength [get_cells -hier -filter {IS_PRIMITIVE == 1}]]"
close $fd
close_design
puts "M441_AUXILIARY_CHECKPOINT_READBACK_PASS"
exit
