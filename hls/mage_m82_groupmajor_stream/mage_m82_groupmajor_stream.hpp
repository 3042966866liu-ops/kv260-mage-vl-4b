#pragma once

#include "../mage_prefill_t6_runtime_wrapper_m75b/mage_prefill_t6_arith.hpp"

// M82-A is the exact, bounded-worker reference for the group-major redesign.
// It deliberately keeps only one copy of the activation payload and reuses
// one exact worker across the six burst-reader FIFOs.
static const unsigned M82_MAX_INPUT_GROUPS = 320;
static const unsigned M82_ROWS_PER_SHARD = 8;
static const unsigned M82_PAIRS_PER_SHARD = M82_ROWS_PER_SHARD / 2;
static const unsigned M82_SHARDS = 6;
static const ap_uint<32> M82A_BUILD_ID = 0x4D383241U;  // "M82A"

void mage_m82_groupmajor_stream(
    hls::stream<mage_t6_axis128_t> &activation_tx,
    const ap_uint<128> *shard0,
    const ap_uint<128> *shard1,
    const ap_uint<128> *shard2,
    const ap_uint<128> *shard3,
    const ap_uint<128> *shard4,
    const ap_uint<128> *shard5,
    hls::stream<mage_t6_axis64_t> &rx,
    unsigned input_groups,
    unsigned bits,
    ap_uint<32> &status,
    ap_uint<32> &build_id,
    ap_uint<32> &completed_words_per_port);
