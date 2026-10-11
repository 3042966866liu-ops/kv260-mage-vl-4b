#pragma once

#include <ap_axi_sdata.h>
#include <ap_int.h>
#include <hls_stream.h>

// M75-B: runtime-facing single-G64 smoke wrapper around the M75-A
// six-token arithmetic with DSP-free/time-shared exact dequant.
static const unsigned MAGE_T6_TOKENS = 6;
static const unsigned MAGE_T6_SHARDS = 6;
static const unsigned MAGE_T6_GROUP_SIZE = 64;
static const unsigned MAGE_T6_MAC_LANES = 32;
static const unsigned MAGE_T6_DEQUANT_TOKEN_LANES = 3;
static const ap_uint<32> MAGE_T6_BUILD_ID = 0x4D47324AU;

typedef ap_axiu<128, 0, 0, 0> mage_t6_axis128_t;
typedef ap_axiu<64, 0, 0, 0> mage_t6_axis64_t;

// Bit-exact round-to-nearest-even binary16 multiply used by the M73
// fabric-dequant candidate.  Exposed so the C testbench can compare the
// integer implementation directly with the Vitis half reference model.
ap_uint<16> mage_t6_half_mul_bits_rne(ap_uint<16> a, ap_uint<16> b);

void m75b_t6rt(
    hls::stream<mage_t6_axis128_t> &activation_tx,
    const ap_uint<128> *shard0,
    const ap_uint<128> *shard1,
    const ap_uint<128> *shard2,
    const ap_uint<128> *shard3,
    const ap_uint<128> *shard4,
    const ap_uint<128> *shard5,
    hls::stream<mage_t6_axis64_t> &rx,
    unsigned input_groups,
    unsigned rows_per_shard,
    unsigned bits,
    ap_uint<32> &status,
    ap_uint<32> &build_id,
    ap_uint<32> &call_count,
    ap_uint<32> &processed_macros);
