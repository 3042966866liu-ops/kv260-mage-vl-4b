# Pure CSim fallback: Layer-0 FP16 arithmetic diagnostics do not synthesize,
# place, route or export IP.  It is intentionally separate from the
# target-part CSim flow so a missing synthesis license cannot be mistaken for
# an arithmetic result.
set root [file dirname [file dirname [file dirname [info script]]]]
set fixture [file join $root deployment mage_vl4b artifacts m89x1_layer0_norm_qkv_fixture.bin]
set output [file join $root deployment mage_vl4b artifacts m89x1_layer0_norm_qkv_hls_output.bin]
if {![file isfile $fixture]} { error "M89X1_NORM_QKV_FIXTURE_MISSING $fixture" }
set ::env(M89X1_CSIM_FIXTURE) $fixture
set ::env(M89X1_CSIM_OUTPUT) $output
set scratch {D:/CodexHome/visualizations/2026/08/31/01a05594-2ad6-7820-b960-8059a45ae04c/m89x1_norm_qkv_csim_nopart}
open_project -reset $scratch
set_top m89x_runtime_kernel
add_files [file join $root hls mage_prefill_m89x_runtime mage_prefill_m89x_runtime.cpp]
add_files -tb [file join $root hls mage_prefill_m89x_runtime tb_m89x1_norm_qkv.cpp]
csim_design -clean
exit
