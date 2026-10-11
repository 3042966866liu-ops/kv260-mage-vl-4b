set root "T:"
set project_root "$root/tmp/mage_prefill_t6_shared_dequant_hybrid_exact_v5/hls_project"
set output_zip "$root/tmp/m73_t6_hybrid_exact_ip/mage_prefill_t6_hybrid_exact.zip"
file mkdir [file dirname $output_zip]
open_project $project_root
open_solution hls
export_design -format ip_catalog -output $output_zip
exit
