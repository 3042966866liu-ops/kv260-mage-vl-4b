#pragma once

#include <ap_axi_sdata.h>
#include <ap_int.h>
#include <hls_stream.h>

// M89-C is an offline W2-only architecture screen.  It deliberately retains
// one M77-width two-token MAC array, but holds each fetched record across a
// T32 activation tile.  It is not a complete Mage-VL layer or model kernel.
static const unsigned M89_GROUP_SIZE = 64;
static const unsigned M89_TOKEN_LANES = 32;
static const unsigned M89_TOKEN_PAIRS = M89_TOKEN_LANES / 2;
static const unsigned M89_SHARDS = 6;
#ifndef M89_MAX_GROUPS_VALUE
#define M89_MAX_GROUPS_VALUE 40
#endif
static const unsigned M89_MAX_GROUPS = M89_MAX_GROUPS_VALUE;
static const unsigned M89_MAX_ROWS_PER_SHARD = 512;
static const ap_uint<32> M89_BUILD_ID = 0x4D383943U;  // "M89C"

typedef ap_axiu<128, 0, 0, 0> m89_axis128_t;
typedef ap_axiu<64, 0, 0, 0> m89_axis64_t;

void m89_t32_reuse(
    hls::stream<m89_axis128_t> &activation_tx,
    const ap_uint<128> *shard0,
    const ap_uint<128> *shard1,
    const ap_uint<128> *shard2,
    const ap_uint<128> *shard3,
    const ap_uint<128> *shard4,
    const ap_uint<128> *shard5,
    hls::stream<m89_axis64_t> &rx,
    unsigned input_groups,
    unsigned rows_per_shard,
    ap_uint<32> &status,
    ap_uint<32> &build_id,
    ap_uint<32> &call_count,
    ap_uint<32> &processed_macros);
