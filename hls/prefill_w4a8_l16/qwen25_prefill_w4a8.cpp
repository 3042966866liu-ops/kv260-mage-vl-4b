#include "qwen25_prefill_w4a8.hpp"

#include <hls_half.h>
#include <hls_math.h>

static half bits_to_half(ap_uint<16> bits) {
#pragma HLS INLINE
    fp_struct<half> value(bits);
    return value.to_half();
}

static ap_uint<32> float_to_bits(float value) {
#pragma HLS INLINE
    fp_struct<float> encoded(value);
    return encoded.data();
}

static ap_uint<8> select_code_byte(ap_uint<128> word, unsigned index) {
#pragma HLS INLINE
    return (ap_uint<8>)(word >> (8 * index));
}

static void clear_outputs(
    float output_accum[PREFILL_MAX_TOKENS]
                      [PREFILL_MAX_OUTPUT_BLOCKS]
                      [PREFILL_OUTPUTS_PER_BLOCK],
    unsigned token_count,
    unsigned output_blocks) {
#pragma HLS INLINE off
clear_token:
    for (unsigned token = 0; token < token_count; ++token) {
    clear_block:
        for (unsigned block = 0; block < output_blocks; ++block) {
#pragma HLS PIPELINE II=1
        clear_output:
            for (unsigned output = 0; output < PREFILL_OUTPUTS_PER_BLOCK; ++output) {
#pragma HLS UNROLL
                output_accum[token][block][output] = 0.0f;
            }
        }
    }
}

static void load_activation_tile(
    hls::stream<prefill_axis128_t> &tx,
    ap_uint<128> activation_words[PREFILL_MAX_TOKENS][4],
    half activation_scale[PREFILL_MAX_TOKENS],
    ap_int<16> activation_sum[PREFILL_MAX_TOKENS],
    unsigned token_count,
    ap_uint<32> &status) {
#pragma HLS INLINE off
#pragma HLS ARRAY_PARTITION variable=activation_words complete dim=1
#pragma HLS ARRAY_PARTITION variable=activation_words complete dim=2
#pragma HLS ARRAY_PARTITION variable=activation_scale complete dim=1
#pragma HLS ARRAY_PARTITION variable=activation_sum complete dim=1
load_token:
    for (unsigned token = 0; token < PREFILL_MAX_TOKENS; ++token) {
        if (token < token_count) {
        load_code_word:
            for (unsigned word = 0; word < 4; ++word) {
#pragma HLS PIPELINE II=1
                const prefill_axis128_t item = tx.read();
                if ((bool)item.last) status = 2;
                // Keep the A8 payload packed.  Unpacking all 1024 bytes while
                // loading creates a large 16-way register-bank demultiplexer;
                // the MAC stage can select its two bytes directly instead.
                activation_words[token][word] = item.data;
            }
            const prefill_axis128_t metadata = tx.read();
            if ((bool)metadata.last) status = 2;
            activation_scale[token] = bits_to_half(metadata.data.range(15, 0));
            activation_sum[token] = (ap_int<16>)metadata.data.range(31, 16);
        } else {
        clear_activation:
            for (unsigned word = 0; word < 4; ++word) {
#pragma HLS UNROLL
                activation_words[token][word] = 0;
            }
            activation_scale[token] = (half)0.0f;
            activation_sum[token] = 0;
        }
    }
}

static void load_weight_block(
    hls::stream<prefill_axis128_t> &tx,
    ap_uint<128> codes[PREFILL_OUTPUTS_PER_BLOCK][2],
    half scales[PREFILL_OUTPUTS_PER_BLOCK],
    half zeros[PREFILL_OUTPUTS_PER_BLOCK],
    unsigned group,
    unsigned input_groups,
    unsigned block,
    unsigned output_blocks,
    ap_uint<32> &status) {
#pragma HLS INLINE off
#pragma HLS ARRAY_PARTITION variable=codes complete dim=0
#pragma HLS ARRAY_PARTITION variable=scales complete dim=1
#pragma HLS ARRAY_PARTITION variable=zeros complete dim=1
load_word:
    for (unsigned word = 0; word < PREFILL_WEIGHT_WORDS; ++word) {
#pragma HLS PIPELINE II=1
        const prefill_axis128_t item = tx.read();
        if (word < 16) {
            codes[word >> 1][word & 1U] = item.data;
        } else {
        load_metadata:
            for (unsigned output = 0; output < PREFILL_OUTPUTS_PER_BLOCK; ++output) {
#pragma HLS UNROLL
                const ap_uint<16> bits = item.data.range(16 * output + 15, 16 * output);
                if (word == 16) scales[output] = bits_to_half(bits);
                else zeros[output] = bits_to_half(bits);
            }
        }
        const bool expected_last = group == input_groups - 1 &&
            block == output_blocks - 1 && word == PREFILL_WEIGHT_WORDS - 1;
        if ((bool)item.last != expected_last) status = 2;
    }
}

static void compute_weight_block(
    const ap_uint<128> codes[PREFILL_OUTPUTS_PER_BLOCK][2],
    const half scales[PREFILL_OUTPUTS_PER_BLOCK],
    const half zeros[PREFILL_OUTPUTS_PER_BLOCK],
    const ap_uint<128> activation_words[PREFILL_MAX_TOKENS][4],
    const half activation_scale[PREFILL_MAX_TOKENS],
    const ap_int<16> activation_sum[PREFILL_MAX_TOKENS],
    float output_accum[PREFILL_MAX_TOKENS]
                      [PREFILL_MAX_OUTPUT_BLOCKS]
                      [PREFILL_OUTPUTS_PER_BLOCK],
    unsigned token_count,
    unsigned block) {
#pragma HLS INLINE off
#pragma HLS ARRAY_PARTITION variable=codes complete dim=0
#pragma HLS ARRAY_PARTITION variable=scales complete dim=1
#pragma HLS ARRAY_PARTITION variable=zeros complete dim=1
#pragma HLS ARRAY_PARTITION variable=activation_words complete dim=1
#pragma HLS ARRAY_PARTITION variable=activation_words complete dim=2
#pragma HLS ARRAY_PARTITION variable=activation_scale complete dim=1
#pragma HLS ARRAY_PARTITION variable=activation_sum complete dim=1
token_batch:
    for (unsigned token_base = 0; token_base < PREFILL_MAX_TOKENS;
         token_base += PREFILL_TOKEN_LANES) {
        ap_int<24> dot[PREFILL_TOKEN_LANES][PREFILL_OUTPUTS_PER_BLOCK];
#pragma HLS ARRAY_PARTITION variable=dot complete dim=0
    init_dot:
        for (unsigned lane = 0; lane < PREFILL_TOKEN_LANES; ++lane) {
#pragma HLS UNROLL
            for (unsigned output = 0; output < PREFILL_OUTPUTS_PER_BLOCK; ++output) {
#pragma HLS UNROLL
                dot[lane][output] = 0;
            }
        }
    dot_pair:
        for (unsigned pair = 0; pair < PREFILL_GROUP_SIZE / 2; ++pair) {
#pragma HLS PIPELINE II=1
            const unsigned word = pair >> 4;
            const unsigned byte = pair & 15U;
        dot_lane:
            for (unsigned lane = 0; lane < PREFILL_TOKEN_LANES; ++lane) {
#pragma HLS UNROLL
                const unsigned token = token_base + lane;
                const unsigned activation_word = pair >> 3;
                const unsigned activation_byte = 2 * (pair & 7U);
                const ap_uint<128> packed_activation =
                    activation_words[token][activation_word];
                const ap_int<8> input0 =
                    (ap_int<8>)select_code_byte(packed_activation, activation_byte);
                const ap_int<8> input1 =
                    (ap_int<8>)select_code_byte(packed_activation, activation_byte + 1);
            dot_output:
                for (unsigned output = 0; output < PREFILL_OUTPUTS_PER_BLOCK; ++output) {
#pragma HLS UNROLL
                    const ap_uint<8> packed = select_code_byte(codes[output][word], byte);
                    const ap_int<5> code0 = (ap_uint<4>)packed.range(3, 0);
                    const ap_int<5> code1 = (ap_uint<4>)packed.range(7, 4);
                    dot[lane][output] += code0 * input0 + code1 * input1;
                }
            }
        }
    update_lane:
        for (unsigned lane = 0; lane < PREFILL_TOKEN_LANES; ++lane) {
#pragma HLS PIPELINE II=1
            const unsigned token = token_base + lane;
            if (token < token_count) {
            update_output:
                for (unsigned output = 0; output < PREFILL_OUTPUTS_PER_BLOCK; ++output) {
#pragma HLS UNROLL
                    const float corrected = (float)dot[lane][output] -
                        (float)zeros[output] * (float)activation_sum[token];
                    const float contribution = corrected *
                        (float)scales[output] * (float)activation_scale[token];
                    output_accum[token][block][output] += contribution;
                }
            }
        }
    }
}

static void write_outputs(
    hls::stream<prefill_axis64_t> &rx,
    const float output_accum[PREFILL_MAX_TOKENS]
                            [PREFILL_MAX_OUTPUT_BLOCKS]
                            [PREFILL_OUTPUTS_PER_BLOCK],
    unsigned token_count,
    unsigned output_blocks) {
#pragma HLS INLINE off
write_token:
    for (unsigned token = 0; token < token_count; ++token) {
    write_block:
        for (unsigned block = 0; block < output_blocks; ++block) {
        write_word:
            for (unsigned word = 0; word < PREFILL_RESULT_WORDS; ++word) {
#pragma HLS PIPELINE II=1
                prefill_axis64_t item;
                const unsigned output0 = 2 * word;
                const unsigned output1 = output0 + 1;
                item.data.range(31, 0) = float_to_bits(output_accum[token][block][output0]);
                item.data.range(63, 32) = float_to_bits(output_accum[token][block][output1]);
                item.keep = -1;
                item.strb = -1;
                item.last = token == token_count - 1 &&
                    block == output_blocks - 1 && word == PREFILL_RESULT_WORDS - 1;
                rx.write(item);
            }
        }
    }
}

void qwen25_prefill_w4a8(
    hls::stream<prefill_axis128_t> &tx,
    hls::stream<prefill_axis64_t> &rx,
    unsigned token_count,
    unsigned input_groups,
    unsigned output_blocks,
    ap_uint<32> &status,
    ap_uint<32> &build_id,
    ap_uint<32> &call_count,
    ap_uint<32> &processed_macros) {
#pragma HLS INTERFACE axis port=tx
#pragma HLS INTERFACE axis port=rx
#pragma HLS INTERFACE s_axilite port=token_count bundle=control
#pragma HLS INTERFACE s_axilite port=input_groups bundle=control
#pragma HLS INTERFACE s_axilite port=output_blocks bundle=control
#pragma HLS INTERFACE s_axilite port=status bundle=control
#pragma HLS INTERFACE s_axilite port=build_id bundle=control
#pragma HLS INTERFACE s_axilite port=call_count bundle=control
#pragma HLS INTERFACE s_axilite port=processed_macros bundle=control
#pragma HLS INTERFACE s_axilite port=return bundle=control

    static ap_uint<32> calls = 0;
    static ap_uint<32> macros = 0;
    static float output_accum[PREFILL_MAX_TOKENS]
                             [PREFILL_MAX_OUTPUT_BLOCKS]
                             [PREFILL_OUTPUTS_PER_BLOCK];
#pragma HLS ARRAY_PARTITION variable=output_accum complete dim=3
#pragma HLS BIND_STORAGE variable=output_accum type=ram_2p impl=uram latency=2

    status = 0;
    build_id = PREFILL_BUILD_ID;
    if (token_count < 1 || token_count > PREFILL_MAX_TOKENS ||
        input_groups < 1 || input_groups > PREFILL_MAX_INPUT_GROUPS ||
        output_blocks < 1 || output_blocks > PREFILL_MAX_OUTPUT_BLOCKS) {
        status = 1;
        call_count = calls;
        processed_macros = macros;
        return;
    }

    clear_outputs(output_accum, token_count, output_blocks);
group_loop:
    for (unsigned group = 0; group < input_groups; ++group) {
        ap_uint<128> activation_words[PREFILL_MAX_TOKENS][4];
        half activation_scale[PREFILL_MAX_TOKENS];
        ap_int<16> activation_sum[PREFILL_MAX_TOKENS];
#pragma HLS ARRAY_PARTITION variable=activation_words complete dim=1
#pragma HLS ARRAY_PARTITION variable=activation_words complete dim=2
#pragma HLS ARRAY_PARTITION variable=activation_scale complete dim=1
#pragma HLS ARRAY_PARTITION variable=activation_sum complete dim=1
        load_activation_tile(
            tx, activation_words, activation_scale, activation_sum, token_count, status);
    block_loop:
        for (unsigned block = 0; block < output_blocks; ++block) {
            ap_uint<128> codes[PREFILL_OUTPUTS_PER_BLOCK][2];
            half scales[PREFILL_OUTPUTS_PER_BLOCK];
            half zeros[PREFILL_OUTPUTS_PER_BLOCK];
#pragma HLS ARRAY_PARTITION variable=codes complete dim=0
#pragma HLS ARRAY_PARTITION variable=scales complete dim=1
#pragma HLS ARRAY_PARTITION variable=zeros complete dim=1
            load_weight_block(
                tx, codes, scales, zeros, group, input_groups,
                block, output_blocks, status);
            compute_weight_block(
                codes, scales, zeros, activation_words, activation_scale,
                activation_sum, output_accum, token_count, block);
        }
    }
    write_outputs(rx, output_accum, token_count, output_blocks);
    calls += 1;
    macros += token_count * input_groups * output_blocks;
    call_count = calls;
    processed_macros = macros;
}
