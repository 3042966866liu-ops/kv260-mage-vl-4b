#include "mage_prefill_t6_runtime_full_m75c.hpp"

// Reuse the already-gated M75-B arithmetic helpers in the same translation
// unit.  They have internal linkage, so this does not export the old top as
// board-visible IP, but it keeps the exact dequant implementation identical.
#include "../mage_prefill_t6_runtime_wrapper_m75b/mage_prefill_t6_arith.cpp"

static ap_uint<32> t6c_float_to_bits(float value) {
#pragma HLS INLINE
    fp_struct<float> encoded(value);
    return encoded.data();
}

static void t6c_load_activations(
    hls::stream<mage_t6_axis128_t> &activation_tx,
    ap_uint<128> activation0[MAGE_T6C_MAX_INPUT_GROUPS][MAGE_T6_TOKENS][4],
    ap_uint<128> activation1[MAGE_T6C_MAX_INPUT_GROUPS][MAGE_T6_TOKENS][4],
    ap_uint<128> activation2[MAGE_T6C_MAX_INPUT_GROUPS][MAGE_T6_TOKENS][4],
    ap_uint<128> activation3[MAGE_T6C_MAX_INPUT_GROUPS][MAGE_T6_TOKENS][4],
    ap_uint<128> activation4[MAGE_T6C_MAX_INPUT_GROUPS][MAGE_T6_TOKENS][4],
    ap_uint<128> activation5[MAGE_T6C_MAX_INPUT_GROUPS][MAGE_T6_TOKENS][4],
    ap_uint<16> scale0[MAGE_T6C_MAX_INPUT_GROUPS][MAGE_T6_TOKENS],
    ap_uint<16> scale1[MAGE_T6C_MAX_INPUT_GROUPS][MAGE_T6_TOKENS],
    ap_uint<16> scale2[MAGE_T6C_MAX_INPUT_GROUPS][MAGE_T6_TOKENS],
    ap_uint<16> scale3[MAGE_T6C_MAX_INPUT_GROUPS][MAGE_T6_TOKENS],
    ap_uint<16> scale4[MAGE_T6C_MAX_INPUT_GROUPS][MAGE_T6_TOKENS],
    ap_uint<16> scale5[MAGE_T6C_MAX_INPUT_GROUPS][MAGE_T6_TOKENS],
    unsigned input_groups,
    ap_uint<32> &status) {
#pragma HLS INLINE off
t6c_load_group:
    for (unsigned group = 0; group < input_groups; ++group) {
    t6c_load_token:
        for (unsigned token = 0; token < MAGE_T6_TOKENS; ++token) {
        t6c_load_word:
            for (unsigned word = 0; word < 5; ++word) {
#pragma HLS PIPELINE II=2
                const mage_t6_axis128_t item = activation_tx.read();
                const bool expected_last =
                    group == input_groups - 1 && token == MAGE_T6_TOKENS - 1 && word == 4;
                if ((bool)item.last != expected_last) status = 2;
                if (word < 4) {
                    activation0[group][token][word] = item.data;
                    activation1[group][token][word] = item.data;
                    activation2[group][token][word] = item.data;
                    activation3[group][token][word] = item.data;
                    activation4[group][token][word] = item.data;
                    activation5[group][token][word] = item.data;
                } else {
                    const ap_uint<16> value = item.data.range(15, 0);
                    scale0[group][token] = value;
                    scale1[group][token] = value;
                    scale2[group][token] = value;
                    scale3[group][token] = value;
                    scale4[group][token] = value;
                    scale5[group][token] = value;
                }
            }
        }
    }
}

struct t6c_result_pair_t {
    ap_uint<64> data;
};

static void t6c_get_pair(
    const ap_uint<128> *memory,
    const ap_uint<128> &scale_word,
    unsigned group,
    unsigned block,
    unsigned slot,
    unsigned blocks_per_group,
    unsigned bits,
    ap_uint<512> &codes,
    ap_uint<16> &tagged0,
    ap_uint<16> &tagged1) {
#pragma HLS INLINE
    const unsigned block_words = 1 + 4 * bits;
    const unsigned base = group * blocks_per_group * block_words + block * block_words;
    if (slot == 0) {
        tagged0 = scale_word.range(15, 0);
        tagged1 = scale_word.range(31, 16);
    } else if (slot == 1) {
        tagged0 = scale_word.range(47, 32);
        tagged1 = scale_word.range(63, 48);
    } else if (slot == 2) {
        tagged0 = scale_word.range(79, 64);
        tagged1 = scale_word.range(95, 80);
    } else {
        tagged0 = scale_word.range(111, 96);
        tagged1 = scale_word.range(127, 112);
    }
    codes = 0;
t6c_load_pair_word:
    for (unsigned word = 0; word < 4; ++word) {
#pragma HLS UNROLL
        if (word < bits) {
            const ap_uint<128> code_word = memory[base + 1 + slot * bits + word];
            codes.range(128 * word + 127, 128 * word) = code_word;
        }
    }
}

static void t6c_dot_pair(
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
t6c_dot_chunk:
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
    t6c_dot_lane:
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

template <int SHARD_ID>
static void t6c_run_shard(
    const ap_uint<128> *memory,
    const ap_uint<128> activation[MAGE_T6C_MAX_INPUT_GROUPS][MAGE_T6_TOKENS][4],
    const ap_uint<16> activation_scales[MAGE_T6C_MAX_INPUT_GROUPS][MAGE_T6_TOKENS],
    hls::stream<t6c_result_pair_t> &results,
    unsigned input_groups,
    unsigned rows_per_shard,
    unsigned bits) {
#pragma HLS INLINE off
    float output_even[MAGE_T6_TOKENS][MAGE_T6C_MAX_ROWS_PER_SHARD / 2];
    float output_odd[MAGE_T6_TOKENS][MAGE_T6C_MAX_ROWS_PER_SHARD / 2];
#pragma HLS ARRAY_PARTITION variable=output_even complete dim=1
#pragma HLS ARRAY_PARTITION variable=output_odd complete dim=1
#pragma HLS BIND_STORAGE variable=output_even type=ram_2p impl=bram latency=2
#pragma HLS BIND_STORAGE variable=output_odd type=ram_2p impl=bram latency=2
    const unsigned pairs_per_shard = rows_per_shard / 2;
    const unsigned blocks_per_group = rows_per_shard / 8;
    const unsigned block_words = 1 + 4 * bits;
t6c_clear_token:
    for (unsigned token = 0; token < MAGE_T6_TOKENS; ++token) {
    t6c_clear_pair:
        for (unsigned pair = 0; pair < pairs_per_shard; ++pair) {
#pragma HLS PIPELINE II=1
            output_even[token][pair] = 0.0f;
            output_odd[token][pair] = 0.0f;
        }
    }
t6c_group:
    for (unsigned group = 0; group < input_groups; ++group) {
    t6c_block:
        for (unsigned block = 0; block < blocks_per_group; ++block) {
            const unsigned base = group * blocks_per_group * block_words + block * block_words;
            const ap_uint<128> scale_word = memory[base];
        t6c_slot:
            for (unsigned slot = 0; slot < 4; ++slot) {
                ap_uint<512> codes;
                ap_uint<16> tagged0;
                ap_uint<16> tagged1;
                t6c_get_pair(memory, scale_word, group, block, slot, blocks_per_group, bits, codes, tagged0, tagged1);
                const unsigned pair = block * 4 + slot;
            t6c_token:
                for (unsigned token = 0; token < MAGE_T6_TOKENS; ++token) {
#pragma HLS PIPELINE II=2
#pragma HLS DEPENDENCE variable=output_even inter false
#pragma HLS DEPENDENCE variable=output_odd inter false
                    ap_int<24> dot0;
                    ap_int<24> dot1;
                    t6c_dot_pair(codes, activation[group], token, bits, dot0, dot1, tagged0, tagged1);
                    const ap_uint<16> dot0_bits = t6_half_to_bits((half)dot0);
                    const ap_uint<16> dot1_bits = t6_half_to_bits((half)dot1);
                    const ap_uint<16> scaled0 =
                        mage_t6_half_mul_bits_rne(dot0_bits, activation_scales[group][token]);
                    const ap_uint<16> scaled1 =
                        mage_t6_half_mul_bits_rne(dot1_bits, activation_scales[group][token]);
                    const ap_uint<16> term0_bits =
                        mage_t6_half_mul_bits_rne(scaled0, tagged0 & 0x7FFFU);
                    const ap_uint<16> term1_bits =
                        mage_t6_half_mul_bits_rne(scaled1, tagged1 & 0x7FFFU);
                    output_even[token][pair] += (float)t6_bits_to_half(term0_bits);
                    output_odd[token][pair] += (float)t6_bits_to_half(term1_bits);
                }
            }
        }
    }
t6c_emit_token:
    for (unsigned token = 0; token < MAGE_T6_TOKENS; ++token) {
    t6c_emit_pair:
        for (unsigned pair = 0; pair < pairs_per_shard; ++pair) {
#pragma HLS PIPELINE II=1
            t6c_result_pair_t item;
            item.data.range(31, 0) = t6c_float_to_bits(output_even[token][pair]);
            item.data.range(63, 32) = t6c_float_to_bits(output_odd[token][pair]);
            results.write(item);
        }
    }
}

static void t6c_merge_results(
    hls::stream<t6c_result_pair_t> results[MAGE_T6_SHARDS],
    hls::stream<mage_t6_axis64_t> &rx,
    unsigned rows_per_shard) {
#pragma HLS INLINE off
#pragma HLS ARRAY_PARTITION variable=results complete dim=1
    const unsigned pairs_per_shard = rows_per_shard / 2;
t6c_merge_token:
    for (unsigned token = 0; token < MAGE_T6_TOKENS; ++token) {
    t6c_merge_shard:
        for (unsigned shard = 0; shard < MAGE_T6_SHARDS; ++shard) {
        t6c_merge_pair:
            for (unsigned pair = 0; pair < pairs_per_shard; ++pair) {
#pragma HLS PIPELINE II=1
                mage_t6_axis64_t item;
                item.data = results[shard].read().data;
                item.keep = -1;
                item.strb = -1;
                item.last =
                    token == MAGE_T6_TOKENS - 1 &&
                    shard == MAGE_T6_SHARDS - 1 &&
                    pair == pairs_per_shard - 1;
                rx.write(item);
            }
        }
    }
}

static void t6c_six_shards(
    const ap_uint<128> *shard0,
    const ap_uint<128> *shard1,
    const ap_uint<128> *shard2,
    const ap_uint<128> *shard3,
    const ap_uint<128> *shard4,
    const ap_uint<128> *shard5,
    const ap_uint<128> activation0[MAGE_T6C_MAX_INPUT_GROUPS][MAGE_T6_TOKENS][4],
    const ap_uint<128> activation1[MAGE_T6C_MAX_INPUT_GROUPS][MAGE_T6_TOKENS][4],
    const ap_uint<128> activation2[MAGE_T6C_MAX_INPUT_GROUPS][MAGE_T6_TOKENS][4],
    const ap_uint<128> activation3[MAGE_T6C_MAX_INPUT_GROUPS][MAGE_T6_TOKENS][4],
    const ap_uint<128> activation4[MAGE_T6C_MAX_INPUT_GROUPS][MAGE_T6_TOKENS][4],
    const ap_uint<128> activation5[MAGE_T6C_MAX_INPUT_GROUPS][MAGE_T6_TOKENS][4],
    const ap_uint<16> scale0[MAGE_T6C_MAX_INPUT_GROUPS][MAGE_T6_TOKENS],
    const ap_uint<16> scale1[MAGE_T6C_MAX_INPUT_GROUPS][MAGE_T6_TOKENS],
    const ap_uint<16> scale2[MAGE_T6C_MAX_INPUT_GROUPS][MAGE_T6_TOKENS],
    const ap_uint<16> scale3[MAGE_T6C_MAX_INPUT_GROUPS][MAGE_T6_TOKENS],
    const ap_uint<16> scale4[MAGE_T6C_MAX_INPUT_GROUPS][MAGE_T6_TOKENS],
    const ap_uint<16> scale5[MAGE_T6C_MAX_INPUT_GROUPS][MAGE_T6_TOKENS],
    hls::stream<mage_t6_axis64_t> &rx,
    unsigned input_groups,
    unsigned rows_per_shard,
    unsigned bits) {
#pragma HLS INLINE off
#pragma HLS DATAFLOW
    hls::stream<t6c_result_pair_t> results[MAGE_T6_SHARDS];
#pragma HLS ARRAY_PARTITION variable=results complete dim=1
#pragma HLS STREAM variable=results depth=32
    t6c_run_shard<0>(shard0, activation0, scale0, results[0], input_groups, rows_per_shard, bits);
    t6c_run_shard<1>(shard1, activation1, scale1, results[1], input_groups, rows_per_shard, bits);
    t6c_run_shard<2>(shard2, activation2, scale2, results[2], input_groups, rows_per_shard, bits);
    t6c_run_shard<3>(shard3, activation3, scale3, results[3], input_groups, rows_per_shard, bits);
    t6c_run_shard<4>(shard4, activation4, scale4, results[4], input_groups, rows_per_shard, bits);
    t6c_run_shard<5>(shard5, activation5, scale5, results[5], input_groups, rows_per_shard, bits);
    t6c_merge_results(results, rx, rows_per_shard);
}

void m75c_t6rt(
    hls::stream<mage_t6_axis128_t> &activation_tx,
    const ap_uint<128> *shard0,
    const ap_uint<128> *shard1,
    const ap_uint<128> *shard2,
    const ap_uint<128> *shard3,
    const ap_uint<128> *shard4,
    const ap_uint<128> *shard5,
    hls::stream<mage_t6_axis64_t> &rx,
    unsigned input_groups,
    unsigned rows_per_shard,
    unsigned bits,
    ap_uint<32> &status,
    ap_uint<32> &build_id,
    ap_uint<32> &call_count,
    ap_uint<32> &processed_macros) {
#pragma HLS INTERFACE axis port=activation_tx
#pragma HLS INTERFACE m_axi port=shard0 offset=slave bundle=weights0 depth=524288 max_read_burst_length=64 num_read_outstanding=16
#pragma HLS INTERFACE m_axi port=shard1 offset=slave bundle=weights1 depth=524288 max_read_burst_length=64 num_read_outstanding=16
#pragma HLS INTERFACE m_axi port=shard2 offset=slave bundle=weights2 depth=524288 max_read_burst_length=64 num_read_outstanding=16
#pragma HLS INTERFACE m_axi port=shard3 offset=slave bundle=weights3 depth=524288 max_read_burst_length=64 num_read_outstanding=16
#pragma HLS INTERFACE m_axi port=shard4 offset=slave bundle=weights4 depth=524288 max_read_burst_length=64 num_read_outstanding=16
#pragma HLS INTERFACE m_axi port=shard5 offset=slave bundle=weights5 depth=524288 max_read_burst_length=64 num_read_outstanding=16
#pragma HLS INTERFACE axis port=rx
#pragma HLS INTERFACE s_axilite port=shard0 bundle=control
#pragma HLS INTERFACE s_axilite port=shard1 bundle=control
#pragma HLS INTERFACE s_axilite port=shard2 bundle=control
#pragma HLS INTERFACE s_axilite port=shard3 bundle=control
#pragma HLS INTERFACE s_axilite port=shard4 bundle=control
#pragma HLS INTERFACE s_axilite port=shard5 bundle=control
#pragma HLS INTERFACE s_axilite port=input_groups bundle=control
#pragma HLS INTERFACE s_axilite port=rows_per_shard bundle=control
#pragma HLS INTERFACE s_axilite port=bits bundle=control
#pragma HLS INTERFACE s_axilite port=status bundle=control
#pragma HLS INTERFACE s_axilite port=build_id bundle=control
#pragma HLS INTERFACE s_axilite port=call_count bundle=control
#pragma HLS INTERFACE s_axilite port=processed_macros bundle=control
#pragma HLS INTERFACE s_axilite port=return bundle=control
    static ap_uint<32> calls = 0;
    static ap_uint<32> macros = 0;
    status = 0;
    build_id = MAGE_T6C_BUILD_ID;
    call_count = calls;
    processed_macros = macros;
    if (input_groups < 1 || input_groups > MAGE_T6C_MAX_INPUT_GROUPS ||
        rows_per_shard < 8 || rows_per_shard > MAGE_T6C_MAX_ROWS_PER_SHARD ||
        (rows_per_shard & 7U) != 0 || (bits != 2 && bits != 3 && bits != 4)) {
        status = 1;
        return;
    }

    ap_uint<128> activation0[MAGE_T6C_MAX_INPUT_GROUPS][MAGE_T6_TOKENS][4];
    ap_uint<128> activation1[MAGE_T6C_MAX_INPUT_GROUPS][MAGE_T6_TOKENS][4];
    ap_uint<128> activation2[MAGE_T6C_MAX_INPUT_GROUPS][MAGE_T6_TOKENS][4];
    ap_uint<128> activation3[MAGE_T6C_MAX_INPUT_GROUPS][MAGE_T6_TOKENS][4];
    ap_uint<128> activation4[MAGE_T6C_MAX_INPUT_GROUPS][MAGE_T6_TOKENS][4];
    ap_uint<128> activation5[MAGE_T6C_MAX_INPUT_GROUPS][MAGE_T6_TOKENS][4];
    ap_uint<16> scale0[MAGE_T6C_MAX_INPUT_GROUPS][MAGE_T6_TOKENS];
    ap_uint<16> scale1[MAGE_T6C_MAX_INPUT_GROUPS][MAGE_T6_TOKENS];
    ap_uint<16> scale2[MAGE_T6C_MAX_INPUT_GROUPS][MAGE_T6_TOKENS];
    ap_uint<16> scale3[MAGE_T6C_MAX_INPUT_GROUPS][MAGE_T6_TOKENS];
    ap_uint<16> scale4[MAGE_T6C_MAX_INPUT_GROUPS][MAGE_T6_TOKENS];
    ap_uint<16> scale5[MAGE_T6C_MAX_INPUT_GROUPS][MAGE_T6_TOKENS];
#pragma HLS BIND_STORAGE variable=activation0 type=ram_2p impl=uram latency=2
#pragma HLS BIND_STORAGE variable=activation1 type=ram_2p impl=uram latency=2
#pragma HLS BIND_STORAGE variable=activation2 type=ram_2p impl=uram latency=2
#pragma HLS BIND_STORAGE variable=activation3 type=ram_2p impl=uram latency=2
#pragma HLS BIND_STORAGE variable=activation4 type=ram_2p impl=uram latency=2
#pragma HLS BIND_STORAGE variable=activation5 type=ram_2p impl=uram latency=2
#pragma HLS BIND_STORAGE variable=scale0 type=ram_2p impl=bram latency=2
#pragma HLS BIND_STORAGE variable=scale1 type=ram_2p impl=bram latency=2
#pragma HLS BIND_STORAGE variable=scale2 type=ram_2p impl=bram latency=2
#pragma HLS BIND_STORAGE variable=scale3 type=ram_2p impl=bram latency=2
#pragma HLS BIND_STORAGE variable=scale4 type=ram_2p impl=bram latency=2
#pragma HLS BIND_STORAGE variable=scale5 type=ram_2p impl=bram latency=2

    t6c_load_activations(
        activation_tx,
        activation0, activation1, activation2, activation3, activation4, activation5,
        scale0, scale1, scale2, scale3, scale4, scale5,
        input_groups, status);
    t6c_six_shards(
        shard0, shard1, shard2, shard3, shard4, shard5,
        activation0, activation1, activation2, activation3, activation4, activation5,
        scale0, scale1, scale2, scale3, scale4, scale5,
        rx, input_groups, rows_per_shard, bits);
    calls += 1;
    macros += input_groups * rows_per_shard * MAGE_T6_SHARDS * MAGE_T6_TOKENS;
    call_count = calls;
    processed_macros = macros;
}
