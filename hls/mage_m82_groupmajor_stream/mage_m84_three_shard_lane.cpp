#include "mage_m84_three_shard_lane.hpp"

// M84 is the validated default. M85 changes this compile-time storage latency
// only, so the bit-accurate arithmetic and external protocol remain identical.
#ifndef M84_ACTIVATION_RAM_LATENCY
#define M84_ACTIVATION_RAM_LATENCY 2
#endif

// Reuse the already exact packed decoder, burst reader, dot and FP16
// accumulation functions.  M84 deliberately has only one worker controller
// inside this IP; system-level parallelism comes from two independent IPs.
#include "mage_m82_groupmajor_stream.cpp"

static void m84_read_then_consume_one(
    const ap_uint<128> *shard,
    const ap_uint<128> activations[M82_MAX_INPUT_GROUPS][MAGE_T6_TOKENS][4],
    const ap_uint<16> activation_scales[M82_MAX_INPUT_GROUPS][MAGE_T6_TOKENS],
    float output_even[MAGE_T6_TOKENS][M82_PAIRS_PER_SHARD],
    float output_odd[MAGE_T6_TOKENS][M82_PAIRS_PER_SHARD],
    unsigned word_count, unsigned input_groups, unsigned bits) {
#pragma HLS INLINE off
#pragma HLS DATAFLOW
    hls::stream<ap_uint<128> > words;
#pragma HLS STREAM variable=words depth=192
    m82_burst_reader(shard, words, word_count);
    m82_consume_shard(words, activations, activation_scales, output_even, output_odd, input_groups, bits);
}

static void m84_readers_and_worker(
    const ap_uint<128> *shard0, const ap_uint<128> *shard1,
    const ap_uint<128> *shard2,
    const ap_uint<128> activations[M82_MAX_INPUT_GROUPS][MAGE_T6_TOKENS][4],
    const ap_uint<16> activation_scales[M82_MAX_INPUT_GROUPS][MAGE_T6_TOKENS],
    float output_even[M84_SHARDS][MAGE_T6_TOKENS][M82_PAIRS_PER_SHARD],
    float output_odd[M84_SHARDS][MAGE_T6_TOKENS][M82_PAIRS_PER_SHARD],
    unsigned word_count, unsigned input_groups, unsigned bits) {
#pragma HLS INLINE off
    // Calls are deliberately sequential, so Vitis can reuse one exact
    // accumulator controller. Each call internally overlaps its own reader
    // and consumer, preserving long bursts without requiring a full-shard FIFO.
    m84_read_then_consume_one(shard0, activations, activation_scales, output_even[0], output_odd[0], word_count, input_groups, bits);
    m84_read_then_consume_one(shard1, activations, activation_scales, output_even[1], output_odd[1], word_count, input_groups, bits);
    m84_read_then_consume_one(shard2, activations, activation_scales, output_even[2], output_odd[2], word_count, input_groups, bits);
}

void mage_m84_three_shard_lane(
    hls::stream<mage_t6_axis128_t> &activation_tx,
    const ap_uint<128> *shard0, const ap_uint<128> *shard1,
    const ap_uint<128> *shard2, hls::stream<mage_t6_axis64_t> &rx,
    unsigned input_groups, unsigned bits, ap_uint<32> &status,
    ap_uint<32> &build_id, ap_uint<32> &completed_words_per_port) {
#pragma HLS INTERFACE axis port=activation_tx
#pragma HLS INTERFACE m_axi port=shard0 offset=slave bundle=weights0 depth=524288 max_read_burst_length=64 num_read_outstanding=32
#pragma HLS INTERFACE m_axi port=shard1 offset=slave bundle=weights1 depth=524288 max_read_burst_length=64 num_read_outstanding=32
#pragma HLS INTERFACE m_axi port=shard2 offset=slave bundle=weights2 depth=524288 max_read_burst_length=64 num_read_outstanding=32
#pragma HLS INTERFACE axis port=rx
#pragma HLS INTERFACE s_axilite port=shard0 bundle=control
#pragma HLS INTERFACE s_axilite port=shard1 bundle=control
#pragma HLS INTERFACE s_axilite port=shard2 bundle=control
#pragma HLS INTERFACE s_axilite port=input_groups bundle=control
#pragma HLS INTERFACE s_axilite port=bits bundle=control
#pragma HLS INTERFACE s_axilite port=status bundle=control
#pragma HLS INTERFACE s_axilite port=build_id bundle=control
#pragma HLS INTERFACE s_axilite port=completed_words_per_port bundle=control
#pragma HLS INTERFACE s_axilite port=return bundle=control
    status = 0;
    build_id = M84_EXPECT_BUILD_ID;
    completed_words_per_port = 0;
    if (input_groups < 1 || input_groups > M82_MAX_INPUT_GROUPS ||
        (bits != 2 && bits != 3 && bits != 4)) { status = 1; return; }
    ap_uint<128> activations[M82_MAX_INPUT_GROUPS][MAGE_T6_TOKENS][4];
    ap_uint<16> activation_scales[M82_MAX_INPUT_GROUPS][MAGE_T6_TOKENS];
#pragma HLS BIND_STORAGE variable=activations type=ram_2p impl=uram latency=M84_ACTIVATION_RAM_LATENCY
#pragma HLS BIND_STORAGE variable=activation_scales type=ram_2p impl=bram latency=2
    m82_load_activations(activation_tx, activations, activation_scales, input_groups, status);
    if (status != 0) return;
    float output_even[M84_SHARDS][MAGE_T6_TOKENS][M82_PAIRS_PER_SHARD];
    float output_odd[M84_SHARDS][MAGE_T6_TOKENS][M82_PAIRS_PER_SHARD];
#pragma HLS ARRAY_PARTITION variable=output_even complete dim=2
#pragma HLS ARRAY_PARTITION variable=output_odd complete dim=2
    const unsigned word_count = input_groups * (1 + 4 * bits);
    m84_readers_and_worker(shard0, shard1, shard2, activations, activation_scales,
                           output_even, output_odd, word_count, input_groups, bits);
emit_token:
    for (unsigned token = 0; token < MAGE_T6_TOKENS; ++token) {
    emit_shard:
        for (unsigned shard = 0; shard < M84_SHARDS; ++shard) {
        emit_pair:
            for (unsigned pair = 0; pair < M82_PAIRS_PER_SHARD; ++pair) {
#pragma HLS PIPELINE II=1
                mage_t6_axis64_t item;
                item.data.range(31, 0) = m82_float_to_bits(output_even[shard][token][pair]);
                item.data.range(63, 32) = m82_float_to_bits(output_odd[shard][token][pair]);
                item.keep = -1; item.strb = -1;
                item.last = token == MAGE_T6_TOKENS - 1 && shard == M84_SHARDS - 1 && pair == M82_PAIRS_PER_SHARD - 1;
                rx.write(item);
            }
        }
    }
    completed_words_per_port = word_count;
}
