#include "mage_m82_groupmajor_stream_m82g.hpp"

// Reuse M82-B's unmodified II=2 exact arithmetic and long-burst readers.
#include "mage_m82_groupmajor_stream_m82b.cpp"

static void m82g_worker_triple(
    hls::stream<ap_uint<128> > &words_a, hls::stream<ap_uint<128> > &words_b, hls::stream<ap_uint<128> > &words_c,
    const ap_uint<128> activations[M82_MAX_INPUT_GROUPS][MAGE_T6_TOKENS][4], const ap_uint<16> activation_scales[M82_MAX_INPUT_GROUPS][MAGE_T6_TOKENS],
    float even_a[MAGE_T6_TOKENS][M82_PAIRS_PER_SHARD], float odd_a[MAGE_T6_TOKENS][M82_PAIRS_PER_SHARD],
    float even_b[MAGE_T6_TOKENS][M82_PAIRS_PER_SHARD], float odd_b[MAGE_T6_TOKENS][M82_PAIRS_PER_SHARD],
    float even_c[MAGE_T6_TOKENS][M82_PAIRS_PER_SHARD], float odd_c[MAGE_T6_TOKENS][M82_PAIRS_PER_SHARD],
    unsigned input_groups, unsigned bits) {
#pragma HLS INLINE off
    m82b_clear(even_a, odd_a); m82b_clear(even_b, odd_b); m82b_clear(even_c, odd_c);
triple_group:
    for (unsigned group = 0; group < input_groups; ++group) {
        // Each shard sees g=0..N-1 in its original order; only different
        // shards run on the other concurrent worker.
        m82b_consume_group(words_a, activations[group], activation_scales[group], even_a, odd_a, bits);
        m82b_consume_group(words_b, activations[group], activation_scales[group], even_b, odd_b, bits);
        m82b_consume_group(words_c, activations[group], activation_scales[group], even_c, odd_c, bits);
    }
}

static void m82g_readers_and_workers(
    const ap_uint<128> *shard0, const ap_uint<128> *shard1, const ap_uint<128> *shard2,
    const ap_uint<128> *shard3, const ap_uint<128> *shard4, const ap_uint<128> *shard5,
    const ap_uint<128> activations[M82_MAX_INPUT_GROUPS][MAGE_T6_TOKENS][4], const ap_uint<16> activation_scales[M82_MAX_INPUT_GROUPS][MAGE_T6_TOKENS],
    float output_even[M82_SHARDS][MAGE_T6_TOKENS][M82_PAIRS_PER_SHARD], float output_odd[M82_SHARDS][MAGE_T6_TOKENS][M82_PAIRS_PER_SHARD],
    unsigned word_count, unsigned input_groups, unsigned bits) {
#pragma HLS INLINE off
#pragma HLS DATAFLOW
    hls::stream<ap_uint<128> > words0, words1, words2, words3, words4, words5;
#pragma HLS STREAM variable=words0 depth=192
#pragma HLS STREAM variable=words1 depth=192
#pragma HLS STREAM variable=words2 depth=192
#pragma HLS STREAM variable=words3 depth=192
#pragma HLS STREAM variable=words4 depth=192
#pragma HLS STREAM variable=words5 depth=192
    m82_burst_reader(shard0, words0, word_count); m82_burst_reader(shard1, words1, word_count); m82_burst_reader(shard2, words2, word_count);
    m82_burst_reader(shard3, words3, word_count); m82_burst_reader(shard4, words4, word_count); m82_burst_reader(shard5, words5, word_count);
    m82g_worker_triple(words0, words1, words2, activations, activation_scales, output_even[0], output_odd[0], output_even[1], output_odd[1], output_even[2], output_odd[2], input_groups, bits);
    m82g_worker_triple(words3, words4, words5, activations, activation_scales, output_even[3], output_odd[3], output_even[4], output_odd[4], output_even[5], output_odd[5], input_groups, bits);
}

void mage_m82_groupmajor_stream_m82g(
    hls::stream<mage_t6_axis128_t> &activation_tx, const ap_uint<128> *shard0, const ap_uint<128> *shard1,
    const ap_uint<128> *shard2, const ap_uint<128> *shard3, const ap_uint<128> *shard4, const ap_uint<128> *shard5,
    hls::stream<mage_t6_axis64_t> &rx, unsigned input_groups, unsigned bits,
    ap_uint<32> &status, ap_uint<32> &build_id, ap_uint<32> &completed_words_per_port) {
#pragma HLS INTERFACE axis port=activation_tx
#pragma HLS INTERFACE m_axi port=shard0 offset=slave bundle=weights0 depth=524288 max_read_burst_length=64 num_read_outstanding=32
#pragma HLS INTERFACE m_axi port=shard1 offset=slave bundle=weights1 depth=524288 max_read_burst_length=64 num_read_outstanding=32
#pragma HLS INTERFACE m_axi port=shard2 offset=slave bundle=weights2 depth=524288 max_read_burst_length=64 num_read_outstanding=32
#pragma HLS INTERFACE m_axi port=shard3 offset=slave bundle=weights3 depth=524288 max_read_burst_length=64 num_read_outstanding=32
#pragma HLS INTERFACE m_axi port=shard4 offset=slave bundle=weights4 depth=524288 max_read_burst_length=64 num_read_outstanding=32
#pragma HLS INTERFACE m_axi port=shard5 offset=slave bundle=weights5 depth=524288 max_read_burst_length=64 num_read_outstanding=32
#pragma HLS INTERFACE axis port=rx
#pragma HLS INTERFACE s_axilite port=shard0 bundle=control
#pragma HLS INTERFACE s_axilite port=shard1 bundle=control
#pragma HLS INTERFACE s_axilite port=shard2 bundle=control
#pragma HLS INTERFACE s_axilite port=shard3 bundle=control
#pragma HLS INTERFACE s_axilite port=shard4 bundle=control
#pragma HLS INTERFACE s_axilite port=shard5 bundle=control
#pragma HLS INTERFACE s_axilite port=input_groups bundle=control
#pragma HLS INTERFACE s_axilite port=bits bundle=control
#pragma HLS INTERFACE s_axilite port=status bundle=control
#pragma HLS INTERFACE s_axilite port=build_id bundle=control
#pragma HLS INTERFACE s_axilite port=completed_words_per_port bundle=control
#pragma HLS INTERFACE s_axilite port=return bundle=control
    status = 0; build_id = M82G_EXPECT_BUILD_ID; completed_words_per_port = 0;
    if (input_groups < 1 || input_groups > M82_MAX_INPUT_GROUPS || (bits != 2 && bits != 3 && bits != 4)) { status = 1; return; }
    ap_uint<128> activations[M82_MAX_INPUT_GROUPS][MAGE_T6_TOKENS][4]; ap_uint<16> activation_scales[M82_MAX_INPUT_GROUPS][MAGE_T6_TOKENS];
#pragma HLS BIND_STORAGE variable=activations type=ram_2p impl=uram latency=2
#pragma HLS BIND_STORAGE variable=activation_scales type=ram_2p impl=bram latency=2
    m82_load_activations(activation_tx, activations, activation_scales, input_groups, status); if (status != 0) return;
    float output_even[M82_SHARDS][MAGE_T6_TOKENS][M82_PAIRS_PER_SHARD]; float output_odd[M82_SHARDS][MAGE_T6_TOKENS][M82_PAIRS_PER_SHARD];
#pragma HLS ARRAY_PARTITION variable=output_even complete dim=2
#pragma HLS ARRAY_PARTITION variable=output_odd complete dim=2
    const unsigned word_count = input_groups * (1 + 4 * bits);
    m82g_readers_and_workers(shard0, shard1, shard2, shard3, shard4, shard5, activations, activation_scales, output_even, output_odd, word_count, input_groups, bits);
emit_token:
    for (unsigned token = 0; token < MAGE_T6_TOKENS; ++token) for (unsigned shard = 0; shard < M82_SHARDS; ++shard) for (unsigned pair = 0; pair < M82_PAIRS_PER_SHARD; ++pair) {
#pragma HLS PIPELINE II=1
        mage_t6_axis64_t item; item.data.range(31, 0) = m82_float_to_bits(output_even[shard][token][pair]); item.data.range(63, 32) = m82_float_to_bits(output_odd[shard][token][pair]); item.keep = -1; item.strb = -1;
        item.last = token == MAGE_T6_TOKENS - 1 && shard == M82_SHARDS - 1 && pair == M82_PAIRS_PER_SHARD - 1; rx.write(item);
    }
    completed_words_per_port = word_count;
}
