set root "T:"
set project_root "$root/tmp/mage_prefill_t6_predecode_shiftadd_m74/hls_project"
set output_zip "$root/tmp/m74_t6_predecode_shiftadd_ip/mage_prefill_t6_predecode_shiftadd.zip"
file mkdir [file dirname $output_zip]
open_project $project_root
open_solution hls
export_design -format ip_catalog -output $output_zip
exit
