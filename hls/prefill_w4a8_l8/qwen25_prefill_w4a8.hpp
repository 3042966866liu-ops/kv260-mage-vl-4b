#pragma once

#include <ap_axi_sdata.h>
#include <ap_int.h>
#include <hls_stream.h>

static const unsigned PREFILL_GROUP_SIZE = 64;
static const unsigned PREFILL_OUTPUTS_PER_BLOCK = 8;
static const unsigned PREFILL_MAX_TOKENS = 16;
static const unsigned PREFILL_TOKEN_LANES = 8;
// This kernel is only for Transformer-layer projections.  Qwen2.5-1.5B's
// largest input/output dimension is the 8960-wide MLP, or 140 input groups
// and 1120 blocks.  The tied 32000-word LM head has its own streaming kernel;
// reserving its shape here would waste every URAM on the device.
static const unsigned PREFILL_MAX_INPUT_GROUPS = 140;
static const unsigned PREFILL_MAX_OUTPUT_BLOCKS = 1120;
static const unsigned PREFILL_ACTIVATION_WORDS = 5;
static const unsigned PREFILL_WEIGHT_WORDS = 18;
static const unsigned PREFILL_RESULT_WORDS = 4;
static const unsigned PREFILL_BUILD_ID = 0x51316842U;

typedef ap_axiu<128, 0, 0, 0> prefill_axis128_t;
typedef ap_axiu<64, 0, 0, 0> prefill_axis64_t;

void qwen25_prefill_w4a8(
    hls::stream<prefill_axis128_t> &tx,
    hls::stream<prefill_axis64_t> &rx,
    unsigned token_count,
    unsigned input_groups,
    unsigned output_blocks,
    ap_uint<32> &status,
    ap_uint<32> &build_id,
    ap_uint<32> &call_count,
    ap_uint<32> &processed_macros);
