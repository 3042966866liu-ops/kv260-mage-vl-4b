#pragma once

#include <ap_axi_sdata.h>
#include <ap_int.h>
#include <hls_stream.h>

static const unsigned MAGE_V2_GROUP_SIZE = 64;
static const unsigned MAGE_V2_MAC_LANES = 32;
static const unsigned MAGE_V2_MAX_INPUT_GROUPS = 512;
static const unsigned MAGE_V2_MAX_ROWS_PER_SHARD = 512;
static const ap_uint<32> MAGE_V2_BUILD_ID = 0x4D473243U;

typedef ap_axiu<128, 0, 0, 0> mage_v2_axis128_t;
typedef ap_axiu<64, 0, 0, 0> mage_v2_axis64_t;

void mage_decode_sixport_v2(
    hls::stream<mage_v2_axis128_t> &activation_tx,
    const ap_uint<128> *shard0,
    const ap_uint<128> *shard1,
    const ap_uint<128> *shard2,
    const ap_uint<128> *shard3,
    const ap_uint<128> *shard4,
    const ap_uint<128> *shard5,
    hls::stream<mage_v2_axis64_t> &rx,
    unsigned input_groups,
    unsigned rows_per_shard,
    unsigned bits,
    ap_uint<32> &status,
    ap_uint<32> &build_id,
    ap_uint<32> &call_count,
    ap_uint<32> &processed_macros);
