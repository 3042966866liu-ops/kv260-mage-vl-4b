#pragma once

#include "mage_m82_groupmajor_stream.hpp"

static const ap_uint<32> M87_EXPECT_BUILD_ID = 0x4D383337U;  // "M837"

void mage_m87_dot_module(
    hls::stream<mage_t6_axis128_t> &activation_tx,
    const ap_uint<128> *shard0, const ap_uint<128> *shard1,
    const ap_uint<128> *shard2, hls::stream<mage_t6_axis64_t> &rx,
    unsigned input_groups, unsigned bits, ap_uint<32> &status,
    ap_uint<32> &build_id, ap_uint<32> &completed_words_per_port);
