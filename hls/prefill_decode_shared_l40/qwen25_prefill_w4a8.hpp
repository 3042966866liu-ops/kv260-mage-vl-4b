#pragma once

#include <ap_axi_sdata.h>
#include <ap_int.h>
#include <hls_stream.h>

static const unsigned PREFILL_GROUP_SIZE = 64;
static const unsigned PREFILL_OUTPUTS_PER_BLOCK = 8;
static const unsigned PREFILL_MAX_TOKENS = 64;
// Feasibility candidate: one 40-token prompt batch is processed in a single
// lane wave.  This is evaluated in isolation before deciding whether Decode
// and Prefill must share DSP/LUT resources in one dual-mode datapath.
static const unsigned PREFILL_TOKEN_LANES = 40;
static const unsigned PREFILL_TOKEN_BATCHES =
    (PREFILL_MAX_TOKENS + PREFILL_TOKEN_LANES - 1) / PREFILL_TOKEN_LANES;
static const unsigned PREFILL_ACTIVATION_SLOTS =
    PREFILL_TOKEN_BATCHES * 4;
// Input groups are streamed and do not dimension an on-chip weight array.
// Keep the validation ceiling above Qwen2.5-7B's 18,944-wide MLP
// (296 groups at GS=64) so larger models remain tileable without reserving a
// model-sized buffer in PL.  The LM head continues to use its own tiled path.
static const unsigned PREFILL_MAX_INPUT_GROUPS = 512;
// Output dimensions are chunked by the host.  560 blocks cover 4480 values,
// so Qwen2.5-1.5B's 8960-wide MLP needs two calls while larger models remain
// supported by additional chunks rather than a larger on-chip allocation.
static const unsigned PREFILL_MAX_OUTPUT_BLOCKS = 560;
static const unsigned PREFILL_ACTIVATION_WORDS = 5;
static const unsigned PREFILL_WEIGHT_WORDS = 18;
static const unsigned PREFILL_RESULT_WORDS = 4;
// A single-token request remaps three PE groups across output blocks.  This
// matches the DDR weight-stream rate without instantiating the old FP16
// Decode kernel beside the 40-token Prefill datapath.
static const unsigned PREFILL_SINGLE_PARALLEL_BLOCKS = 3;
static const unsigned PREFILL_BUILD_ID = 0x51317142U;

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
