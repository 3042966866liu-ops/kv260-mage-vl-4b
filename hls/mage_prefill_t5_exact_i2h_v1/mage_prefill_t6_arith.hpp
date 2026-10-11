#pragma once

#include <ap_axi_sdata.h>
#include <ap_int.h>
#include <hls_stream.h>

// M69 resource-recovery candidate: retain the proven arithmetic and reduce
// token replication from six to five so the full dequant path can fit.
static const unsigned MAGE_T6_TOKENS = 5;
static const unsigned MAGE_T6_SHARDS = 6;
static const unsigned MAGE_T6_GROUP_SIZE = 64;
static const unsigned MAGE_T6_MAC_LANES = 32;
static const ap_uint<32> MAGE_T6_BUILD_ID = 0x4D473246U;

typedef ap_axiu<128, 0, 0, 0> mage_t6_axis128_t;
typedef ap_axiu<64, 0, 0, 0> mage_t6_axis64_t;

// Exposed for the CSim exhaustive equivalence gate. The synthesized top uses
// the same function, so the gate tests the actual replacement logic.
ap_uint<16> mage_t6_int24_to_half_bits(ap_int<24> value);

void mage_prefill_t6_arith(
    hls::stream<mage_t6_axis128_t> &activation_tx,
    const ap_uint<128> *shard0,
    const ap_uint<128> *shard1,
    const ap_uint<128> *shard2,
    const ap_uint<128> *shard3,
    const ap_uint<128> *shard4,
    const ap_uint<128> *shard5,
    hls::stream<mage_t6_axis64_t> &rx,
    unsigned bits,
    ap_uint<32> &status,
    ap_uint<32> &build_id,
    ap_uint<32> &call_count,
    ap_uint<32> &processed_macros);
