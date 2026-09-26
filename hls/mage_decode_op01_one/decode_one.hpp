#pragma once

#include "../mage_prefill_m89d_t32_microtile/mage_prefill_m89d_t32_microtile.hpp"

// Public board/runtime contract.  Keep the declaration in one header so HLS,
// CSim, host-side build checks and deliverable packaging cannot drift.
ap_uint<32> op01_decode_one_kernel(
    hls::stream<m89_axis128_t> &tx,
    const ap_uint<128> *s0,
    const ap_uint<128> *s1,
    const ap_uint<128> *s2,
    const ap_uint<128> *s3,
    hls::stream<m89_axis64_t> &rx,
    ap_uint<32> config);
