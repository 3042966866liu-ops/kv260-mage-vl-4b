#pragma once

#include "../mage_prefill_m89_t32_reuse/mage_prefill_m89_t32_reuse.hpp"

// M89-D retains M89-C's W2/T32 arithmetic but changes the output ABI order to
// descriptor microtile -> token -> shard -> row-pair.  This lets a completed
// eight-row output tile be emitted without keeping an entire 512-row layer in
// per-token BRAM banks.
void m89d_t32_microtile(
    hls::stream<m89_axis128_t> &activation_tx,
    const ap_uint<128> *shard0, const ap_uint<128> *shard1,
    const ap_uint<128> *shard2, const ap_uint<128> *shard3,
    const ap_uint<128> *shard4, const ap_uint<128> *shard5,
    hls::stream<m89_axis64_t> &rx,
    unsigned input_groups, unsigned rows_per_shard,
    ap_uint<32> &status, ap_uint<32> &build_id, ap_uint<32> &call_count,
    ap_uint<32> &processed_macros);
