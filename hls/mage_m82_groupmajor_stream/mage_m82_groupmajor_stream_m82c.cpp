#include "mage_m82_groupmajor_stream_m82c.hpp"

// M82-A supplies the already-gated packed decode, dot arithmetic, activation
// loader, long-burst reader and bit-exact FP16 helpers.
#include "mage_m82_groupmajor_stream.cpp"

struct m82c_dot_item_t {
    ap_int<24> dot0;
    ap_int<24> dot1;
    ap_uint<16> tagged0;
    ap_uint<16> tagged1;
    ap_uint<16> activation_scale;
    ap_uint<1> which;
    ap_uint<2> pair;
    ap_uint<3> token;
};

static void m82c_clear(
    float output_even[MAGE_T6_TOKENS][M82_PAIRS_PER_SHARD],
    float output_odd[MAGE_T6_TOKENS][M82_PAIRS_PER_SHARD]) {
#pragma HLS INLINE off
clear_token:
    for (unsigned token = 0; token < MAGE_T6_TOKENS; ++token) {
    clear_pair:
        for (unsigned pair = 0; pair < M82_PAIRS_PER_SHARD; ++pair) {
#pragma HLS PIPELINE II=1
            output_even[token][pair] = 0.0f;
            output_odd[token][pair] = 0.0f;
        }
    }
}

static void m82c_emit_group(
    hls::stream<ap_uint<128> > &words,
    const ap_uint<128> activation[MAGE_T6_TOKENS][4],
    const ap_uint<16> activation_scales[MAGE_T6_TOKENS],
    ap_uint<1> which,
    unsigned bits,
    hls::stream<m82c_dot_item_t> &dot_tx) {
#pragma HLS INLINE off
    const ap_uint<128> scale_word = words.read();
emit_slot:
    for (unsigned slot = 0; slot < 4; ++slot) {
        ap_uint<512> codes = 0;
    emit_code_word:
        for (unsigned word = 0; word < 4; ++word) {
#pragma HLS PIPELINE II=1
            if (word < bits) codes.range(128 * word + 127, 128 * word) = words.read();
        }
        const ap_uint<16> tagged0 = scale_word.range(32 * slot + 15, 32 * slot);
        const ap_uint<16> tagged1 = scale_word.range(32 * slot + 31, 32 * slot + 16);
    emit_token:
        for (unsigned token = 0; token < MAGE_T6_TOKENS; ++token) {
#pragma HLS PIPELINE II=2
            m82c_dot_item_t item;
            m82_dot_pair(codes, activation, token, bits, item.dot0, item.dot1, tagged0, tagged1);
            item.tagged0 = tagged0;
            item.tagged1 = tagged1;
            item.activation_scale = activation_scales[token];
            item.which = which;
            item.pair = slot;
            item.token = token;
            dot_tx.write(item);
        }
    }
}

static void m82c_dot_producer(
    hls::stream<ap_uint<128> > &words_a, hls::stream<ap_uint<128> > &words_b,
    const ap_uint<128> activations[M82_MAX_INPUT_GROUPS][MAGE_T6_TOKENS][4],
    const ap_uint<16> activation_scales[M82_MAX_INPUT_GROUPS][MAGE_T6_TOKENS],
    unsigned input_groups, unsigned bits,
    hls::stream<m82c_dot_item_t> &dot_tx) {
#pragma HLS INLINE off
dot_group:
    for (unsigned group = 0; group < input_groups; ++group) {
        // The order A(g), B(g), A(g+1), B(g+1) preserves group order inside
        // both shard accumulators while keeping each FIFO actively drained.
        m82c_emit_group(words_a, activations[group], activation_scales[group], 0, bits, dot_tx);
        m82c_emit_group(words_b, activations[group], activation_scales[group], 1, bits, dot_tx);
    }
}

static void m82c_ordered_accumulator(
    hls::stream<m82c_dot_item_t> &dot_rx,
    float output_even_a[MAGE_T6_TOKENS][M82_PAIRS_PER_SHARD],
    float output_odd_a[MAGE_T6_TOKENS][M82_PAIRS_PER_SHARD],
    float output_even_b[MAGE_T6_TOKENS][M82_PAIRS_PER_SHARD],
    float output_odd_b[MAGE_T6_TOKENS][M82_PAIRS_PER_SHARD],
    unsigned input_groups) {
#pragma HLS INLINE off
    const unsigned item_count = input_groups * 2 * 4 * MAGE_T6_TOKENS;
accumulate_item:
    for (unsigned index = 0; index < item_count; ++index) {
#pragma HLS PIPELINE II=2
        const m82c_dot_item_t item = dot_rx.read();
        const ap_uint<16> dot0_bits = t6_half_to_bits((half)item.dot0);
        const ap_uint<16> dot1_bits = t6_half_to_bits((half)item.dot1);
        const ap_uint<16> scaled0 = mage_t6_half_mul_bits_rne(dot0_bits, item.activation_scale);
        const ap_uint<16> scaled1 = mage_t6_half_mul_bits_rne(dot1_bits, item.activation_scale);
        const ap_uint<16> term0 = mage_t6_half_mul_bits_rne(scaled0, item.tagged0 & 0x7FFFU);
        const ap_uint<16> term1 = mage_t6_half_mul_bits_rne(scaled1, item.tagged1 & 0x7FFFU);
        if (item.which == 0) {
            output_even_a[item.token][item.pair] += (float)t6_bits_to_half(term0);
            output_odd_a[item.token][item.pair] += (float)t6_bits_to_half(term1);
        } else {
            output_even_b[item.token][item.pair] += (float)t6_bits_to_half(term0);
            output_odd_b[item.token][item.pair] += (float)t6_bits_to_half(term1);
        }
    }
}

static void m82c_worker_pair(
    hls::stream<ap_uint<128> > &words_a, hls::stream<ap_uint<128> > &words_b,
    const ap_uint<128> activations[M82_MAX_INPUT_GROUPS][MAGE_T6_TOKENS][4],
    const ap_uint<16> activation_scales[M82_MAX_INPUT_GROUPS][MAGE_T6_TOKENS],
    float output_even_a[MAGE_T6_TOKENS][M82_PAIRS_PER_SHARD],
    float output_odd_a[MAGE_T6_TOKENS][M82_PAIRS_PER_SHARD],
    float output_even_b[MAGE_T6_TOKENS][M82_PAIRS_PER_SHARD],
    float output_odd_b[MAGE_T6_TOKENS][M82_PAIRS_PER_SHARD],
    unsigned input_groups, unsigned bits) {
#pragma HLS INLINE off
    m82c_clear(output_even_a, output_odd_a);
    m82c_clear(output_even_b, output_odd_b);
#pragma HLS DATAFLOW
    hls::stream<m82c_dot_item_t> dot_fifo;
#pragma HLS STREAM variable=dot_fifo depth=192
    m82c_dot_producer(words_a, words_b, activations, activation_scales, input_groups, bits, dot_fifo);
    m82c_ordered_accumulator(dot_fifo, output_even_a, output_odd_a, output_even_b, output_odd_b, input_groups);
}

static void m82c_readers_and_workers(
    const ap_uint<128> *shard0, const ap_uint<128> *shard1, const ap_uint<128> *shard2,
    const ap_uint<128> *shard3, const ap_uint<128> *shard4, const ap_uint<128> *shard5,
    const ap_uint<128> activations[M82_MAX_INPUT_GROUPS][MAGE_T6_TOKENS][4],
    const ap_uint<16> activation_scales[M82_MAX_INPUT_GROUPS][MAGE_T6_TOKENS],
    float output_even[M82_SHARDS][MAGE_T6_TOKENS][M82_PAIRS_PER_SHARD],
    float output_odd[M82_SHARDS][MAGE_T6_TOKENS][M82_PAIRS_PER_SHARD],
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
    m82_burst_reader(shard0, words0, word_count); m82_burst_reader(shard1, words1, word_count);
    m82_burst_reader(shard2, words2, word_count); m82_burst_reader(shard3, words3, word_count);
    m82_burst_reader(shard4, words4, word_count); m82_burst_reader(shard5, words5, word_count);
    m82c_worker_pair(words0, words1, activations, activation_scales, output_even[0], output_odd[0], output_even[1], output_odd[1], input_groups, bits);
    m82c_worker_pair(words2, words3, activations, activation_scales, output_even[2], output_odd[2], output_even[3], output_odd[3], input_groups, bits);
    m82c_worker_pair(words4, words5, activations, activation_scales, output_even[4], output_odd[4], output_even[5], output_odd[5], input_groups, bits);
}

void mage_m82_groupmajor_stream_m82c(
    hls::stream<mage_t6_axis128_t> &activation_tx,
    const ap_uint<128> *shard0, const ap_uint<128> *shard1, const ap_uint<128> *shard2,
    const ap_uint<128> *shard3, const ap_uint<128> *shard4, const ap_uint<128> *shard5,
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
    status = 0; build_id = M82C_EXPECT_BUILD_ID; completed_words_per_port = 0;
    if (input_groups < 1 || input_groups > M82_MAX_INPUT_GROUPS || (bits != 2 && bits != 3 && bits != 4)) { status = 1; return; }
    ap_uint<128> activations[M82_MAX_INPUT_GROUPS][MAGE_T6_TOKENS][4];
    ap_uint<16> activation_scales[M82_MAX_INPUT_GROUPS][MAGE_T6_TOKENS];
#pragma HLS BIND_STORAGE variable=activations type=ram_2p impl=uram latency=2
#pragma HLS BIND_STORAGE variable=activation_scales type=ram_2p impl=bram latency=2
    m82_load_activations(activation_tx, activations, activation_scales, input_groups, status);
    if (status != 0) return;
    float output_even[M82_SHARDS][MAGE_T6_TOKENS][M82_PAIRS_PER_SHARD];
    float output_odd[M82_SHARDS][MAGE_T6_TOKENS][M82_PAIRS_PER_SHARD];
#pragma HLS ARRAY_PARTITION variable=output_even complete dim=2
#pragma HLS ARRAY_PARTITION variable=output_odd complete dim=2
    const unsigned word_count = input_groups * (1 + 4 * bits);
    m82c_readers_and_workers(shard0, shard1, shard2, shard3, shard4, shard5, activations, activation_scales,
                             output_even, output_odd, word_count, input_groups, bits);
emit_token:
    for (unsigned token = 0; token < MAGE_T6_TOKENS; ++token) {
    emit_shard:
        for (unsigned shard = 0; shard < M82_SHARDS; ++shard) {
        emit_pair:
            for (unsigned pair = 0; pair < M82_PAIRS_PER_SHARD; ++pair) {
#pragma HLS PIPELINE II=1
                mage_t6_axis64_t item;
                item.data.range(31, 0) = m82_float_to_bits(output_even[shard][token][pair]);
                item.data.range(63, 32) = m82_float_to_bits(output_odd[shard][token][pair]);
                item.keep = -1; item.strb = -1;
                item.last = token == MAGE_T6_TOKENS - 1 && shard == M82_SHARDS - 1 && pair == M82_PAIRS_PER_SHARD - 1;
                rx.write(item);
            }
        }
    }
    completed_words_per_port = word_count;
}
