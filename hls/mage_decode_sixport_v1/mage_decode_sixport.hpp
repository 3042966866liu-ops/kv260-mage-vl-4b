#pragma once

#include <ap_axi_sdata.h>
#include <ap_int.h>
#include <hls_stream.h>

static const unsigned MAGE_GROUP_SIZE = 64;
static const unsigned MAGE_MAC_LANES = 16;
static const unsigned MAGE_MAX_INPUT_GROUPS = 512;
static const unsigned MAGE_MAX_ROWS_PER_SHARD = 256;
static const ap_uint<32> MAGE_SIXPORT_BUILD_ID = 0x4D473142U;

typedef ap_axiu<128, 0, 0, 0> mage_axis128_t;
typedef ap_axiu<64, 0, 0, 0> mage_axis64_t;

void mage_decode_sixport(
    hls::stream<mage_axis128_t> &activation_tx,
    const ap_uint<128> *shard0,
    const ap_uint<128> *shard1,
    const ap_uint<128> *shard2,
    const ap_uint<128> *shard3,
    const ap_uint<128> *shard4,
    const ap_uint<128> *shard5,
    hls::stream<mage_axis64_t> &rx,
    unsigned input_groups,
    unsigned rows_per_shard,
    unsigned bits,
    unsigned scale_base_words,
    ap_uint<32> &status,
    ap_uint<32> &build_id,
    ap_uint<32> &call_count,
    ap_uint<32> &processed_macros);
