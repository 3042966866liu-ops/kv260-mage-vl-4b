#pragma once

#include "../mage_prefill_m89x_runtime/mage_prefill_m89x_runtime.hpp"

// M230 preserves the accepted M120 W2/W4 arithmetic array and time-multiplexes
// it across two T32 activation blocks.  Descriptor/weight records are read
// once while the decoded weight pair serves all 64 tokens.
ap_uint<32> m230_t64_kernel(
    hls::stream<m89_axis128_t> &tx,
    const ap_uint<128> *s0,
    const ap_uint<128> *s1,
    const ap_uint<128> *s2,
    const ap_uint<128> *s3,
    hls::stream<m89_axis64_t> &rx,
    ap_uint<32> config);

