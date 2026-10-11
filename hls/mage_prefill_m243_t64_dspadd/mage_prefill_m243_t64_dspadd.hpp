#pragma once

#include "../mage_prefill_m89x_runtime/mage_prefill_m89x_runtime.hpp"

// Isolated T64 candidate: keep the M240 serial-token architecture but replace
// the route-dominated final packed-dot reductions with registered DSP adds.
ap_uint<32> m243_t64_kernel(
    hls::stream<m89_axis128_t> &tx,
    const ap_uint<128> *s0,
    const ap_uint<128> *s1,
    const ap_uint<128> *s2,
    const ap_uint<128> *s3,
    hls::stream<m89_axis64_t> &rx,
    ap_uint<32> config);
