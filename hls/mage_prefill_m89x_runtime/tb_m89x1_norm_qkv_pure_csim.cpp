// Vitis 2026.1 simulation-only solutions do not add a non-testbench design
// file to csim.mk until a device-bound platform is created.  Including the
// exact kernel translation unit here keeps the gate pure CSim (no part,
// synthesis, RTL or co-simulation) while exercising the same C++ arithmetic.
#include "mage_prefill_m89x_runtime.cpp"
#include "tb_m89x1_norm_qkv.cpp"
