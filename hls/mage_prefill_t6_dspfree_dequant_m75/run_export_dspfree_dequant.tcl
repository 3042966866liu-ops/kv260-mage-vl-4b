set root "C:/Users/30429/Desktop/TeLLMe_FPGA_2026"
set project_root "$root/tmp/mage_prefill_t6_dspfree_dequant_m75/hls_project"
set output_zip "$root/tmp/m75_t6_dspfree_dequant_ip/mage_prefill_t6_dspfree_dequant.zip"
open_project $project_root
open_solution "hls"
export_design -format ip_catalog -output $output_zip
exit
