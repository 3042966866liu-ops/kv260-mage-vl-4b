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
// A single-token request remaps PE groups across output blocks.  The promoted
// shared kernel uses three lanes.  A separately synthesized second-HP
// companion may use two: 36 stream-load cycles for two blocks still dominate
// its 32 compute cycles, while the smaller lane count fits beside the shared
// kernel.  This compile-time value does not alter the promoted bitstream.
#ifndef PREFILL_SINGLE_PARALLEL_BLOCKS_VALUE
#define PREFILL_SINGLE_PARALLEL_BLOCKS_VALUE 3
#endif
static const unsigned PREFILL_SINGLE_PARALLEL_BLOCKS =
    PREFILL_SINGLE_PARALLEL_BLOCKS_VALUE;
static const unsigned PREFILL_BUILD_ID = 0x51317342U;
// A decode-only companion kernel can be placed behind a second PS DDR port.
// It deliberately keeps the exact W4A8 arithmetic used by the shared kernel;
// the different ID prevents a dual-HP candidate from being mistaken for the
// promoted single-channel build.
static const unsigned DECODE_DUALHP_BUILD_ID = 0x51317642U;
static const unsigned DUALTX_SHARED_BUILD_ID = 0x51317742U;
static const unsigned DECODE_TRISTREAM_BUILD_ID = 0x51317842U;
static const unsigned DECODE_DIRECTDDR_BUILD_ID = 0x51317942U;
static const unsigned DECODE_DIRECTDDR_CHAIN_BUILD_ID = 0x51317A42U;
static const unsigned DIRECTDDR_MAX_CHAIN_TILES = 8;

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

void qwen25_decode_w4a8(
    hls::stream<prefill_axis128_t> &tx,
    hls::stream<prefill_axis64_t> &rx,
    unsigned input_groups,
    unsigned output_blocks,
    ap_uint<32> &status,
    ap_uint<32> &build_id,
    ap_uint<32> &call_count,
    ap_uint<32> &processed_macros);

void qwen25_prefill_w4a8_dualtx(
    hls::stream<prefill_axis128_t> &tx,
    hls::stream<prefill_axis128_t> &tx_decode,
    hls::stream<prefill_axis64_t> &rx,
    unsigned token_count,
    unsigned input_groups,
    unsigned primary_blocks,
    unsigned secondary_blocks,
    ap_uint<32> &status,
    ap_uint<32> &build_id,
    ap_uint<32> &call_count,
    ap_uint<32> &processed_macros);

void qwen25_decode_w4a8_tristream(
    hls::stream<prefill_axis128_t> &tx0,
    hls::stream<prefill_axis128_t> &tx1,
    hls::stream<prefill_axis128_t> &tx2,
    hls::stream<prefill_axis64_t> &rx,
    unsigned input_groups,
    unsigned blocks0,
    unsigned blocks1,
    unsigned blocks2,
    ap_uint<32> &status,
    ap_uint<32> &build_id,
    ap_uint<32> &call_count,
    ap_uint<32> &processed_macros);

void qwen25_decode_w4a8_directddr(
    hls::stream<prefill_axis128_t> &activation_tx,
    const ap_uint<128> *weights0,
    const ap_uint<128> *weights1,
    const ap_uint<128> *weights2,
    hls::stream<prefill_axis64_t> &rx,
    unsigned input_groups,
    unsigned blocks0,
    unsigned blocks1,
    unsigned blocks2,
    ap_uint<32> &status,
    ap_uint<32> &build_id,
    ap_uint<32> &call_count,
    ap_uint<32> &processed_macros);

void qwen25_decode_w4a8_directddr_chain(
    hls::stream<prefill_axis128_t> &activation_tx,
    const ap_uint<128> *weights0,
    const ap_uint<128> *weights1,
    const ap_uint<128> *weights2,
    const ap_uint<128> *tile_descriptors,
    hls::stream<prefill_axis64_t> &rx,
    unsigned input_groups,
    unsigned tile_count,
    ap_uint<32> &status,
    ap_uint<32> &build_id,
    ap_uint<32> &call_count,
    ap_uint<32> &processed_macros);
