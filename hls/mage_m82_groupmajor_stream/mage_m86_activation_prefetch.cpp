#include "mage_m86_activation_prefetch.hpp"

// Reuse M82's bit-exact decoder, AXI burst reader, dot product and FP16
// rounding helpers. M86 changes only where each group's activations are read:
// URAM is drained into a fully partitioned local register cache before the
// original dot/scale/accumulate order consumes them.
#include "mage_m82_groupmajor_stream.cpp"

#ifndef M86_DOT_FUNCTION
#define M86_DOT_FUNCTION m82_dot_pair
#endif

static void m86_inline_terms(
    ap_int<24> dot0, ap_int<24> dot1, ap_uint<16> activation_scale,
    ap_uint<16> tagged0, ap_uint<16> tagged1, float &term0_out,
    float &term1_out) {
#pragma HLS INLINE
    const ap_uint<16> dot0_bits = t6_half_to_bits((half)dot0);
    const ap_uint<16> dot1_bits = t6_half_to_bits((half)dot1);
    const ap_uint<16> scaled0 = mage_t6_half_mul_bits_rne(dot0_bits, activation_scale);
    const ap_uint<16> scaled1 = mage_t6_half_mul_bits_rne(dot1_bits, activation_scale);
    const ap_uint<16> term0 = mage_t6_half_mul_bits_rne(scaled0, tagged0 & 0x7FFFU);
    const ap_uint<16> term1 = mage_t6_half_mul_bits_rne(scaled1, tagged1 & 0x7FFFU);
    term0_out = (float)t6_bits_to_half(term0);
    term1_out = (float)t6_bits_to_half(term1);
}

#ifndef M86_TERM_FUNCTION
#define M86_TERM_FUNCTION m86_inline_terms
#endif

static void m86_consume_shard_prefetch(
    hls::stream<ap_uint<128> > &words,
    const ap_uint<128> activations[M82_MAX_INPUT_GROUPS][MAGE_T6_TOKENS][4],
    const ap_uint<16> activation_scales[M82_MAX_INPUT_GROUPS][MAGE_T6_TOKENS],
    float output_even[MAGE_T6_TOKENS][M82_PAIRS_PER_SHARD],
    float output_odd[MAGE_T6_TOKENS][M82_PAIRS_PER_SHARD],
    unsigned input_groups, unsigned bits) {
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
consume_group:
    for (unsigned group = 0; group < input_groups; ++group) {
        ap_uint<128> activation_cache[MAGE_T6_TOKENS][4];
        ap_uint<16> scale_cache[MAGE_T6_TOKENS];
#pragma HLS ARRAY_PARTITION variable=activation_cache complete dim=0
#pragma HLS ARRAY_PARTITION variable=scale_cache complete dim=1
prefetch_token:
        for (unsigned token = 0; token < MAGE_T6_TOKENS; ++token) {
        prefetch_word:
            for (unsigned word = 0; word < 4; ++word) {
#pragma HLS PIPELINE II=1
                activation_cache[token][word] = activations[group][token][word];
            }
            scale_cache[token] = activation_scales[group][token];
        }
        const ap_uint<128> scale_word = words.read();
    consume_slot:
        for (unsigned slot = 0; slot < 4; ++slot) {
            ap_uint<512> codes = 0;
        consume_code_word:
            for (unsigned word = 0; word < 4; ++word) {
#pragma HLS PIPELINE II=1
                if (word < bits) codes.range(128 * word + 127, 128 * word) = words.read();
            }
            ap_uint<16> tagged0 = scale_word.range(32 * slot + 15, 32 * slot);
            ap_uint<16> tagged1 = scale_word.range(32 * slot + 31, 32 * slot + 16);
        consume_token:
            for (unsigned token = 0; token < MAGE_T6_TOKENS; ++token) {
#pragma HLS PIPELINE II=2
                ap_int<24> dot0;
                ap_int<24> dot1;
                M86_DOT_FUNCTION(codes, activation_cache, token, bits, dot0, dot1, tagged0, tagged1);
                float term0;
                float term1;
                M86_TERM_FUNCTION(dot0, dot1, scale_cache[token], tagged0, tagged1, term0, term1);
                output_even[token][slot] += term0;
                output_odd[token][slot] += term1;
            }
        }
    }
}

static void m86_read_then_consume_one(
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
    m86_consume_shard_prefetch(words, activations, activation_scales,
                               output_even, output_odd, input_groups, bits);
}

static void m86_readers_and_worker(
    const ap_uint<128> *shard0, const ap_uint<128> *shard1,
    const ap_uint<128> *shard2,
    const ap_uint<128> activations[M82_MAX_INPUT_GROUPS][MAGE_T6_TOKENS][4],
    const ap_uint<16> activation_scales[M82_MAX_INPUT_GROUPS][MAGE_T6_TOKENS],
    float output_even[M86_SHARDS][MAGE_T6_TOKENS][M82_PAIRS_PER_SHARD],
    float output_odd[M86_SHARDS][MAGE_T6_TOKENS][M82_PAIRS_PER_SHARD],
    unsigned word_count, unsigned input_groups, unsigned bits) {
#pragma HLS INLINE off
    m86_read_then_consume_one(shard0, activations, activation_scales, output_even[0], output_odd[0], word_count, input_groups, bits);
    m86_read_then_consume_one(shard1, activations, activation_scales, output_even[1], output_odd[1], word_count, input_groups, bits);
    m86_read_then_consume_one(shard2, activations, activation_scales, output_even[2], output_odd[2], word_count, input_groups, bits);
}

void mage_m86_activation_prefetch(
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
    build_id = M86_EXPECT_BUILD_ID;
    completed_words_per_port = 0;
    if (input_groups < 1 || input_groups > M82_MAX_INPUT_GROUPS ||
        (bits != 2 && bits != 3 && bits != 4)) { status = 1; return; }
    ap_uint<128> activations[M82_MAX_INPUT_GROUPS][MAGE_T6_TOKENS][4];
    ap_uint<16> activation_scales[M82_MAX_INPUT_GROUPS][MAGE_T6_TOKENS];
#pragma HLS BIND_STORAGE variable=activations type=ram_2p impl=uram latency=2
#pragma HLS BIND_STORAGE variable=activation_scales type=ram_2p impl=bram latency=2
    m82_load_activations(activation_tx, activations, activation_scales, input_groups, status);
    if (status != 0) return;
    float output_even[M86_SHARDS][MAGE_T6_TOKENS][M82_PAIRS_PER_SHARD];
    float output_odd[M86_SHARDS][MAGE_T6_TOKENS][M82_PAIRS_PER_SHARD];
#pragma HLS ARRAY_PARTITION variable=output_even complete dim=2
#pragma HLS ARRAY_PARTITION variable=output_odd complete dim=2
    const unsigned word_count = input_groups * (1 + 4 * bits);
    m86_readers_and_worker(shard0, shard1, shard2, activations, activation_scales,
                           output_even, output_odd, word_count, input_groups, bits);
emit_token:
    for (unsigned token = 0; token < MAGE_T6_TOKENS; ++token) {
    emit_shard:
        for (unsigned shard = 0; shard < M86_SHARDS; ++shard) {
        emit_pair:
            for (unsigned pair = 0; pair < M82_PAIRS_PER_SHARD; ++pair) {
#pragma HLS PIPELINE II=1
                mage_t6_axis64_t item;
                item.data.range(31, 0) = m82_float_to_bits(output_even[shard][token][pair]);
                item.data.range(63, 32) = m82_float_to_bits(output_odd[shard][token][pair]);
                item.keep = -1; item.strb = -1;
                item.last = token == MAGE_T6_TOKENS - 1 && shard == M86_SHARDS - 1 && pair == M82_PAIRS_PER_SHARD - 1;
                rx.write(item);
            }
        }
    }
    completed_words_per_port = word_count;
}
