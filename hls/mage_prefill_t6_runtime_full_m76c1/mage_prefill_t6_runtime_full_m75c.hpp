#pragma once

#include "../mage_prefill_t6_runtime_wrapper_m75b/mage_prefill_t6_arith.hpp"

// M75-C: runtime-shaped multi-G64/multi-row extension of the M75-B T6
// arithmetic candidate.  It keeps the M75-B six-token packed MAC and
// DSP-free/two-stage FP16 dequant helpers, but removes the single-G64 smoke
// gate so the candidate can be screened as a deployable prefill block.
static const unsigned MAGE_T6C_MAX_INPUT_GROUPS = 320;
static const unsigned MAGE_T6C_MAX_ROWS_PER_SHARD = 512;
static const ap_uint<32> MAGE_T6C_BUILD_ID = 0x4D47324BU;

void m75c_t6rt(
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
