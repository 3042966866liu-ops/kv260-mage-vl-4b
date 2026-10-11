#pragma once

#include <ap_axi_sdata.h>
#include <ap_int.h>
#include <hls_stream.h>

static const unsigned QWEN_GS_GROUP = 64;
static const unsigned QWEN_GS_OUTPUTS = 8;
static const unsigned QWEN_GS_ACTIVATION_BYTES = 128;
static const unsigned QWEN_GS_ACTIVATION_WORDS = 8;
static const unsigned QWEN_GS_WEIGHT_BYTES = 288;
static const unsigned QWEN_GS_WEIGHT_WORDS = 18;
static const unsigned QWEN_GS_CODE_WORDS = 16;
static const unsigned QWEN_GS_CODE_WORDS_PER_OUTPUT = 2;
static const unsigned QWEN_GS_RESULT_WORDS = 4;
static const unsigned QWEN_GS_PARALLEL_BLOCKS = 3;
static const unsigned QWEN_GS_MAX_MACROS = 524288;
static const unsigned QWEN_GS_MAX_INPUT_GROUPS = 256;
// A multiple of the three-lane width keeps padded tail writes in-bounds and
// keeps each output accumulator bank below the next BRAM depth threshold.
static const unsigned QWEN_GS_MAX_OUTPUT_BLOCKS = 2046;
static const unsigned QWEN_GS_OUTPUT_STORAGE = QWEN_GS_MAX_OUTPUT_BLOCKS;
static const unsigned QWEN_GS_BUILD_ID = 0x51315F42U;

typedef ap_axiu<128, 0, 0, 0> qwen_axis128_t;
typedef ap_axiu<64, 0, 0, 0> qwen_axis64_t;

void qwen25_mixed_gs_macro(
    hls::stream<qwen_axis128_t> &tx,
    hls::stream<qwen_axis64_t> &rx,
    unsigned input_groups,
    unsigned output_blocks,
    ap_uint<32> &status,
    ap_uint<32> &build_id,
    ap_uint<32> &call_count,
    ap_uint<32> &processed_macros);
