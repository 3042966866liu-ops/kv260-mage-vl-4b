#include "mage_m82_groupmajor_stream.hpp"

#include <hls_math.h>

// Keep the exact arithmetic helpers and FP16 rounding path identical to the
// previously gated M75-C source.  No floating-point approximation is added.
#include "../mage_prefill_t6_runtime_wrapper_m75b/mage_prefill_t6_arith.cpp"

static ap_uint<32> m82_float_to_bits(float value) {
#pragma HLS INLINE
    fp_struct<float> encoded(value);
    return encoded.data();
}

static void m82_load_activations(
    hls::stream<mage_t6_axis128_t> &activation_tx,
    ap_uint<128> activations[M82_MAX_INPUT_GROUPS][MAGE_T6_TOKENS][4],
    ap_uint<16> scales[M82_MAX_INPUT_GROUPS][MAGE_T6_TOKENS],
    unsigned input_groups,
    ap_uint<32> &status) {
#pragma HLS INLINE off
load_group:
    for (unsigned group = 0; group < input_groups; ++group) {
    load_token:
        for (unsigned token = 0; token < MAGE_T6_TOKENS; ++token) {
        load_word:
            for (unsigned word = 0; word < 5; ++word) {
#pragma HLS PIPELINE II=2
                const mage_t6_axis128_t item = activation_tx.read();
                const bool expected_last =
                    group == input_groups - 1 && token == MAGE_T6_TOKENS - 1 && word == 4;
                if ((bool)item.last != expected_last) status = 2;
                if (word < 4) activations[group][token][word] = item.data;
                else scales[group][token] = item.data.range(15, 0);
            }
        }
    }
}

static void m82_burst_reader(
    const ap_uint<128> *memory,
    hls::stream<ap_uint<128> > &words,
    unsigned word_count) {
#pragma HLS INLINE off
read_words:
    for (unsigned word = 0; word < word_count; ++word) {
#pragma HLS PIPELINE II=1
        words.write(memory[word]);
    }
}

static void m82_dot_pair(
    const ap_uint<512> &codes,
    const ap_uint<128> activation[MAGE_T6_TOKENS][4],
    unsigned token,
    unsigned bits,
    ap_int<24> &dot0,
    ap_int<24> &dot1,
    ap_uint<16> tagged0,
    ap_uint<16> tagged1) {
#pragma HLS INLINE
    dot0 = 0;
    dot1 = 0;
    const bool orientation0 = tagged0[15];
    const bool orientation1 = tagged1[15];
    const ap_int<5> half_range = (ap_int<5>)(1 << (bits - 1));
    const ap_int<5> negative_half = (ap_int<5>)(-half_range);
    const ap_int<5> shifted_half = (ap_int<5>)(negative_half + (ap_int<5>)1);
    const ap_int<5> qmin0 = orientation0 ? shifted_half : negative_half;
    const ap_int<5> qmin1 = orientation1 ? shifted_half : negative_half;
dot_chunk:
    for (unsigned chunk = 0; chunk < 2; ++chunk) {
#pragma HLS PIPELINE II=1
        ap_uint<128> code_chunk0 = 0;
        ap_uint<128> code_chunk1 = 0;
        if (bits == 2) {
            code_chunk0.range(63, 0) = codes.range(64 * chunk + 63, 64 * chunk);
            code_chunk1.range(63, 0) = codes.range(128 + 64 * chunk + 63, 128 + 64 * chunk);
        } else if (bits == 3) {
            code_chunk0.range(95, 0) = codes.range(96 * chunk + 95, 96 * chunk);
            code_chunk1.range(95, 0) = codes.range(192 + 96 * chunk + 95, 192 + 96 * chunk);
        } else {
            code_chunk0 = codes.range(128 * chunk + 127, 128 * chunk);
            code_chunk1 = codes.range(256 + 128 * chunk + 127, 256 + 128 * chunk);
        }
        ap_uint<256> activation_bits = 0;
        activation_bits.range(127, 0) = activation[token][2 * chunk];
        activation_bits.range(255, 128) = activation[token][2 * chunk + 1];
        ap_int<20> partial0 = 0;
        ap_int<20> partial1 = 0;
    dot_lane:
        for (unsigned lane = 0; lane < MAGE_T6_MAC_LANES; ++lane) {
#pragma HLS UNROLL
            const ap_int<8> input = (ap_int<8>)activation_bits.range(8 * lane + 7, 8 * lane);
            ap_int<5> weight0;
            ap_int<5> weight1;
            if (bits == 2) {
                weight0 = (ap_uint<2>)code_chunk0.range(2 * lane + 1, 2 * lane) + qmin0;
                weight1 = (ap_uint<2>)code_chunk1.range(2 * lane + 1, 2 * lane) + qmin1;
            } else if (bits == 3) {
                weight0 = (ap_uint<3>)code_chunk0.range(3 * lane + 2, 3 * lane) + qmin0;
                weight1 = (ap_uint<3>)code_chunk1.range(3 * lane + 2, 3 * lane) + qmin1;
            } else {
                weight0 = (ap_uint<4>)code_chunk0.range(4 * lane + 3, 4 * lane) + qmin0;
                weight1 = (ap_uint<4>)code_chunk1.range(4 * lane + 3, 4 * lane) + qmin1;
            }
            ap_int<16> product0;
            ap_int<16> product1;
            t6_packed_mac2(input, weight0, weight1, product0, product1);
            partial0 += product0;
            partial1 += product1;
        }
        dot0 += partial0;
        dot1 += partial1;
    }
}

static void m82_consume_shard(
    hls::stream<ap_uint<128> > &words,
    const ap_uint<128> activations[M82_MAX_INPUT_GROUPS][MAGE_T6_TOKENS][4],
    const ap_uint<16> activation_scales[M82_MAX_INPUT_GROUPS][MAGE_T6_TOKENS],
    float output_even[MAGE_T6_TOKENS][M82_PAIRS_PER_SHARD],
    float output_odd[MAGE_T6_TOKENS][M82_PAIRS_PER_SHARD],
    unsigned input_groups,
    unsigned bits) {
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
                m82_dot_pair(codes, activations[group], token, bits, dot0, dot1, tagged0, tagged1);
                const ap_uint<16> dot0_bits = t6_half_to_bits((half)dot0);
                const ap_uint<16> dot1_bits = t6_half_to_bits((half)dot1);
                const ap_uint<16> scaled0 = mage_t6_half_mul_bits_rne(dot0_bits, activation_scales[group][token]);
                const ap_uint<16> scaled1 = mage_t6_half_mul_bits_rne(dot1_bits, activation_scales[group][token]);
                const ap_uint<16> term0 = mage_t6_half_mul_bits_rne(scaled0, tagged0 & 0x7FFFU);
                const ap_uint<16> term1 = mage_t6_half_mul_bits_rne(scaled1, tagged1 & 0x7FFFU);
                output_even[token][slot] += (float)t6_bits_to_half(term0);
                output_odd[token][slot] += (float)t6_bits_to_half(term1);
            }
        }
    }
}

static void m82_worker(
    hls::stream<ap_uint<128> > &words0, hls::stream<ap_uint<128> > &words1,
    hls::stream<ap_uint<128> > &words2, hls::stream<ap_uint<128> > &words3,
    hls::stream<ap_uint<128> > &words4, hls::stream<ap_uint<128> > &words5,
    const ap_uint<128> activations[M82_MAX_INPUT_GROUPS][MAGE_T6_TOKENS][4],
    const ap_uint<16> activation_scales[M82_MAX_INPUT_GROUPS][MAGE_T6_TOKENS],
    float output_even[M82_SHARDS][MAGE_T6_TOKENS][M82_PAIRS_PER_SHARD],
    float output_odd[M82_SHARDS][MAGE_T6_TOKENS][M82_PAIRS_PER_SHARD],
    unsigned input_groups, unsigned bits) {
#pragma HLS INLINE off
    m82_consume_shard(words0, activations, activation_scales, output_even[0], output_odd[0], input_groups, bits);
    m82_consume_shard(words1, activations, activation_scales, output_even[1], output_odd[1], input_groups, bits);
    m82_consume_shard(words2, activations, activation_scales, output_even[2], output_odd[2], input_groups, bits);
    m82_consume_shard(words3, activations, activation_scales, output_even[3], output_odd[3], input_groups, bits);
    m82_consume_shard(words4, activations, activation_scales, output_even[4], output_odd[4], input_groups, bits);
    m82_consume_shard(words5, activations, activation_scales, output_even[5], output_odd[5], input_groups, bits);
}

static void m82_readers_and_worker(
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
    m82_burst_reader(shard0, words0, word_count);
    m82_burst_reader(shard1, words1, word_count);
    m82_burst_reader(shard2, words2, word_count);
    m82_burst_reader(shard3, words3, word_count);
    m82_burst_reader(shard4, words4, word_count);
    m82_burst_reader(shard5, words5, word_count);
    m82_worker(words0, words1, words2, words3, words4, words5, activations, activation_scales,
               output_even, output_odd, input_groups, bits);
}

void mage_m82_groupmajor_stream(
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
    status = 0;
    build_id = M82A_BUILD_ID;
    completed_words_per_port = 0;
    if (input_groups < 1 || input_groups > M82_MAX_INPUT_GROUPS || (bits != 2 && bits != 3 && bits != 4)) {
        status = 1;
        return;
    }
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
    const unsigned words_per_group = 1 + 4 * bits;
    const unsigned word_count = input_groups * words_per_group;
    m82_readers_and_worker(shard0, shard1, shard2, shard3, shard4, shard5,
                           activations, activation_scales, output_even, output_odd,
                           word_count, input_groups, bits);
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
                item.keep = -1;
                item.strb = -1;
                item.last = token == MAGE_T6_TOKENS - 1 && shard == M82_SHARDS - 1 && pair == M82_PAIRS_PER_SHARD - 1;
                rx.write(item);
            }
        }
    }
    completed_words_per_port = word_count;
}
