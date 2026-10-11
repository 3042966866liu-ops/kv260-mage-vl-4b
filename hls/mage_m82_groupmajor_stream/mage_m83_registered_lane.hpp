#pragma once

#include "mage_m82_groupmajor_stream.hpp"

static const ap_uint<32> M83_EXPECT_BUILD_ID = 0x4D383333U;  // "M833"

void mage_m83_registered_lane(
    hls::stream<mage_t6_axis128_t> &activation_tx,
    const ap_uint<128> *shard0, const ap_uint<128> *shard1,
    const ap_uint<128> *shard2, const ap_uint<128> *shard3,
    const ap_uint<128> *shard4, const ap_uint<128> *shard5,
    hls::stream<mage_t6_axis64_t> &rx, unsigned input_groups, unsigned bits,
    ap_uint<32> &status, ap_uint<32> &build_id,
    ap_uint<32> &completed_words_per_port);
