#pragma once

#include <ap_axi_sdata.h>
#include <ap_int.h>
#include <hls_stream.h>

// M77-A is deliberately a W2 integer-accumulation microarchitecture gate for
// the real Mage q_proj record layout.  It is not an end-to-end model kernel:
// exact FP16 scaling and all W3/W4 paths are added only after this raw dataflow
// proves it can sustain a useful rate.
static const unsigned M77_GROUP_SIZE = 64;
static const unsigned M77_TOKEN_LANES = 2;
static const unsigned M77_SHARDS = 6;
static const unsigned M77_MAX_GROUPS = 40;
static const unsigned M77_MAX_ROWS_PER_SHARD = 512;
static const ap_uint<32> M77_BUILD_ID = 0x4D373744U;  // "M77D"

typedef ap_axiu<128, 0, 0, 0> m77_axis128_t;
typedef ap_axiu<64, 0, 0, 0> m77_axis64_t;

void m77_w2_wide(
    hls::stream<m77_axis128_t> &activation_tx,
    const ap_uint<128> *shard0,
    const ap_uint<128> *shard1,
    const ap_uint<128> *shard2,
    const ap_uint<128> *shard3,
    const ap_uint<128> *shard4,
    const ap_uint<128> *shard5,
    hls::stream<m77_axis64_t> &rx,
    unsigned input_groups,
    unsigned rows_per_shard,
    ap_uint<32> &status,
    ap_uint<32> &build_id,
    ap_uint<32> &call_count,
    ap_uint<32> &processed_macros);
