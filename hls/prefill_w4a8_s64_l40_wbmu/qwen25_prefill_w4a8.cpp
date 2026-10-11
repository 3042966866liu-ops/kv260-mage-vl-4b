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

static ap_uint<16> half_to_bits(half value) {
#pragma HLS INLINE
    fp_struct<half> encoded(value);
    return encoded.data();
}

static ap_uint<8> select_code_byte(ap_uint<128> word, unsigned index) {
#pragma HLS INLINE
    return (ap_uint<8>)(word >> (8 * index));
}

typedef ap_uint<24 * PREFILL_OUTPUTS_PER_BLOCK> dot_lane_packet_t;

static void clear_outputs(
    ap_uint<32> output_accum[PREFILL_MAX_TOKENS]
                      [PREFILL_MAX_OUTPUT_BLOCKS]
                      [PREFILL_OUTPUTS_PER_BLOCK / 2],
    unsigned token_count,
    unsigned output_blocks) {
#pragma HLS INLINE off
clear_token:
    for (unsigned token = 0; token < token_count; ++token) {
    clear_block:
        for (unsigned block = 0; block < output_blocks; ++block) {
#pragma HLS PIPELINE II=1
        clear_output_pair:
            for (unsigned pair = 0; pair < PREFILL_OUTPUTS_PER_BLOCK / 2; ++pair) {
#pragma HLS UNROLL
                output_accum[token][block][pair] = 0;
            }
        }
    }
}

static void load_activation_tile(
    hls::stream<prefill_axis128_t> &tx,
    ap_uint<128> activation_words[PREFILL_TOKEN_LANES][PREFILL_ACTIVATION_SLOTS],
    half activation_scale[PREFILL_TOKEN_LANES][PREFILL_TOKEN_BATCHES],
    ap_int<16> activation_sum[PREFILL_TOKEN_LANES][PREFILL_TOKEN_BATCHES],
    unsigned token_count,
    ap_uint<32> &status) {
#pragma HLS INLINE off
#pragma HLS ARRAY_PARTITION variable=activation_words complete dim=1
#pragma HLS ARRAY_PARTITION variable=activation_scale complete dim=1
#pragma HLS ARRAY_PARTITION variable=activation_sum complete dim=1
load_token:
    for (unsigned token = 0;
         token < PREFILL_TOKEN_BATCHES * PREFILL_TOKEN_LANES;
         ++token) {
        const unsigned lane = token % PREFILL_TOKEN_LANES;
        const unsigned batch = token / PREFILL_TOKEN_LANES;
        if (token < token_count) {
        load_code_word:
            for (unsigned word = 0; word < 4; ++word) {
#pragma HLS PIPELINE II=1
                const prefill_axis128_t item = tx.read();
                if ((bool)item.last) status = 2;
                // Keep the A8 payload packed.  Unpacking all 1024 bytes while
                // loading creates a large 16-way register-bank demultiplexer;
                // the MAC stage can select its two bytes directly instead.
                activation_words[lane][batch * 4 + word] = item.data;
            }
            const prefill_axis128_t metadata = tx.read();
            if ((bool)metadata.last) status = 2;
            activation_scale[lane][batch] = bits_to_half(metadata.data.range(15, 0));
            activation_sum[lane][batch] = (ap_int<16>)metadata.data.range(31, 16);
        } else {
        clear_activation:
            for (unsigned word = 0; word < 4; ++word) {
#pragma HLS UNROLL
                activation_words[lane][batch * 4 + word] = 0;
            }
            activation_scale[lane][batch] = (half)0.0f;
            activation_sum[lane][batch] = 0;
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

static void produce_dot_batches(
    const ap_uint<128> codes[PREFILL_OUTPUTS_PER_BLOCK][2],
    const ap_uint<128> activation_words[PREFILL_TOKEN_LANES][PREFILL_ACTIVATION_SLOTS],
    hls::stream<dot_lane_packet_t> dot_stream[PREFILL_TOKEN_LANES],
    unsigned token_count) {
#pragma HLS INLINE off
#pragma HLS ARRAY_PARTITION variable=codes complete dim=0
#pragma HLS ARRAY_PARTITION variable=activation_words complete dim=1
#pragma HLS ARRAY_PARTITION variable=dot_stream complete dim=1
produce_batch:
    for (unsigned batch = 0; batch < PREFILL_TOKEN_BATCHES; ++batch) {
        const unsigned token_base = batch * PREFILL_TOKEN_LANES;
        if (token_base >= token_count) continue;
        ap_int<24> dot[PREFILL_TOKEN_LANES][PREFILL_OUTPUTS_PER_BLOCK];
#pragma HLS ARRAY_PARTITION variable=dot complete dim=0
    produce_init_dot:
        for (unsigned lane = 0; lane < PREFILL_TOKEN_LANES; ++lane) {
#pragma HLS UNROLL
            for (unsigned output = 0; output < PREFILL_OUTPUTS_PER_BLOCK; ++output) {
#pragma HLS UNROLL
                dot[lane][output] = 0;
            }
        }
    produce_dot_pair:
        for (unsigned pair = 0; pair < PREFILL_GROUP_SIZE / 2; ++pair) {
#pragma HLS PIPELINE II=1
            const unsigned word = pair >> 4;
            const unsigned byte = pair & 15U;
        produce_dot_lane:
            for (unsigned lane = 0; lane < PREFILL_TOKEN_LANES; ++lane) {
#pragma HLS UNROLL
                const unsigned activation_word = pair >> 3;
                const unsigned activation_byte = 2 * (pair & 7U);
                const ap_uint<128> packed_activation =
                    activation_words[lane][batch * 4 + activation_word];
                const ap_int<8> input0 =
                    (ap_int<8>)select_code_byte(packed_activation, activation_byte);
                const ap_int<8> input1 =
                    (ap_int<8>)select_code_byte(packed_activation, activation_byte + 1);
            produce_dot_output:
                for (unsigned output = 0; output < PREFILL_OUTPUTS_PER_BLOCK; ++output) {
#pragma HLS UNROLL
                    const ap_uint<8> packed = select_code_byte(codes[output][word], byte);
                    const ap_int<5> code0 = (ap_uint<4>)packed.range(3, 0);
                    const ap_int<5> code1 = (ap_uint<4>)packed.range(7, 4);
                    dot[lane][output] += code0 * input0 + code1 * input1;
                }
            }
        }
    produce_emit_lane:
        for (unsigned lane = 0; lane < PREFILL_TOKEN_LANES; ++lane) {
#pragma HLS UNROLL
            dot_lane_packet_t packet = 0;
        produce_emit_output:
            for (unsigned output = 0; output < PREFILL_OUTPUTS_PER_BLOCK; ++output) {
#pragma HLS UNROLL
                packet.range(24 * output + 23, 24 * output) =
                    (ap_uint<24>)dot[lane][output];
            }
            dot_stream[lane].write(packet);
        }
    }
}

static void consume_dot_batches(
    const half scales[PREFILL_OUTPUTS_PER_BLOCK],
    const half zeros[PREFILL_OUTPUTS_PER_BLOCK],
    const half activation_scale[PREFILL_TOKEN_LANES][PREFILL_TOKEN_BATCHES],
    const ap_int<16> activation_sum[PREFILL_TOKEN_LANES][PREFILL_TOKEN_BATCHES],
    hls::stream<dot_lane_packet_t> dot_stream[PREFILL_TOKEN_LANES],
    ap_uint<32> output_accum[PREFILL_MAX_TOKENS]
                              [PREFILL_MAX_OUTPUT_BLOCKS]
                              [PREFILL_OUTPUTS_PER_BLOCK / 2],
    unsigned token_count,
    unsigned block) {
#pragma HLS INLINE off
#pragma HLS ARRAY_PARTITION variable=scales complete dim=1
#pragma HLS ARRAY_PARTITION variable=zeros complete dim=1
#pragma HLS ARRAY_PARTITION variable=activation_scale complete dim=1
#pragma HLS ARRAY_PARTITION variable=activation_sum complete dim=1
#pragma HLS ARRAY_PARTITION variable=dot_stream complete dim=1
consume_batch:
    for (unsigned batch = 0; batch < PREFILL_TOKEN_BATCHES; ++batch) {
        const unsigned token_base = batch * PREFILL_TOKEN_LANES;
        if (token_base >= token_count) continue;
    consume_lane:
        for (unsigned lane = 0; lane < PREFILL_TOKEN_LANES; ++lane) {
#pragma HLS PIPELINE II=1
            const unsigned token = token_base + lane;
            const dot_lane_packet_t packet = dot_stream[lane].read();
            ap_int<24> dot[PREFILL_OUTPUTS_PER_BLOCK];
#pragma HLS ARRAY_PARTITION variable=dot complete dim=1
        consume_read_output:
            for (unsigned output = 0; output < PREFILL_OUTPUTS_PER_BLOCK; ++output) {
#pragma HLS UNROLL
                dot[output] = (ap_int<24>)packet.range(
                    24 * output + 23, 24 * output);
            }
            if (token < token_count) {
            consume_update_pair:
                for (unsigned pair = 0; pair < PREFILL_OUTPUTS_PER_BLOCK / 2; ++pair) {
#pragma HLS UNROLL
                    ap_uint<32> packed = output_accum[token][block][pair];
                consume_update_half:
                    for (unsigned half_lane = 0; half_lane < 2; ++half_lane) {
#pragma HLS UNROLL
                        const unsigned output = 2 * pair + half_lane;
                        const half accumulator = bits_to_half(
                            packed.range(16 * half_lane + 15, 16 * half_lane));
                        const float corrected = (float)dot[output] -
                            (float)zeros[output] * (float)activation_sum[lane][batch];
                        const float contribution = corrected *
                            (float)scales[output] * (float)activation_scale[lane][batch];
                        const half updated = (half)((float)accumulator + contribution);
                        packed.range(16 * half_lane + 15, 16 * half_lane) =
                            half_to_bits(updated);
                    }
                    output_accum[token][block][pair] = packed;
                }
            }
        }
    }
}

static void compute_weight_block(
    const ap_uint<128> codes[PREFILL_OUTPUTS_PER_BLOCK][2],
    const half scales[PREFILL_OUTPUTS_PER_BLOCK],
    const half zeros[PREFILL_OUTPUTS_PER_BLOCK],
    const ap_uint<128> activation_words[PREFILL_TOKEN_LANES][PREFILL_ACTIVATION_SLOTS],
    const half activation_scale[PREFILL_TOKEN_LANES][PREFILL_TOKEN_BATCHES],
    const ap_int<16> activation_sum[PREFILL_TOKEN_LANES][PREFILL_TOKEN_BATCHES],
    ap_uint<32> output_accum[PREFILL_MAX_TOKENS]
                              [PREFILL_MAX_OUTPUT_BLOCKS]
                              [PREFILL_OUTPUTS_PER_BLOCK / 2],
    unsigned token_count,
    unsigned block) {
#pragma HLS INLINE off
#pragma HLS DATAFLOW
    hls::stream<dot_lane_packet_t> dot_stream[PREFILL_TOKEN_LANES];
#pragma HLS ARRAY_PARTITION variable=dot_stream complete dim=1
#pragma HLS STREAM variable=dot_stream depth=2
    produce_dot_batches(codes, activation_words, dot_stream, token_count);
    consume_dot_batches(
        scales, zeros, activation_scale, activation_sum, dot_stream,
        output_accum, token_count, block);
}

static void load_and_compute_weight_block(
    hls::stream<prefill_axis128_t> &tx,
    ap_uint<128> next_codes[PREFILL_OUTPUTS_PER_BLOCK][2],
    half next_scales[PREFILL_OUTPUTS_PER_BLOCK],
    half next_zeros[PREFILL_OUTPUTS_PER_BLOCK],
    const ap_uint<128> current_codes[PREFILL_OUTPUTS_PER_BLOCK][2],
    const half current_scales[PREFILL_OUTPUTS_PER_BLOCK],
    const half current_zeros[PREFILL_OUTPUTS_PER_BLOCK],
    const ap_uint<128> activation_words[PREFILL_TOKEN_LANES][PREFILL_ACTIVATION_SLOTS],
    const half activation_scale[PREFILL_TOKEN_LANES][PREFILL_TOKEN_BATCHES],
    const ap_int<16> activation_sum[PREFILL_TOKEN_LANES][PREFILL_TOKEN_BATCHES],
    ap_uint<32> output_accum[PREFILL_MAX_TOKENS]
                              [PREFILL_MAX_OUTPUT_BLOCKS]
                              [PREFILL_OUTPUTS_PER_BLOCK / 2],
    unsigned token_count,
    unsigned group,
    unsigned input_groups,
    unsigned current_block,
    unsigned output_blocks,
    bool load_next,
    ap_uint<32> &status) {
#pragma HLS INLINE off
#pragma HLS DATAFLOW
#pragma HLS ARRAY_PARTITION variable=next_codes complete dim=0
#pragma HLS ARRAY_PARTITION variable=next_scales complete dim=1
#pragma HLS ARRAY_PARTITION variable=next_zeros complete dim=1
#pragma HLS ARRAY_PARTITION variable=current_codes complete dim=0
#pragma HLS ARRAY_PARTITION variable=current_scales complete dim=1
#pragma HLS ARRAY_PARTITION variable=current_zeros complete dim=1
    if (load_next) {
        load_weight_block(
            tx, next_codes, next_scales, next_zeros, group, input_groups,
            current_block + 1, output_blocks, status);
    }
    compute_weight_block(
        current_codes, current_scales, current_zeros, activation_words,
        activation_scale, activation_sum, output_accum, token_count,
        current_block);
}

static void write_outputs(
    hls::stream<prefill_axis64_t> &rx,
    const ap_uint<32> output_accum[PREFILL_MAX_TOKENS]
                            [PREFILL_MAX_OUTPUT_BLOCKS]
                            [PREFILL_OUTPUTS_PER_BLOCK / 2],
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
                const ap_uint<32> packed = output_accum[token][block][word];
                const half output0 = bits_to_half(packed.range(15, 0));
                const half output1 = bits_to_half(packed.range(31, 16));
                item.data.range(31, 0) = float_to_bits(
                    (float)output0);
                item.data.range(63, 32) = float_to_bits(
                    (float)output1);
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
    static ap_uint<32> output_accum[PREFILL_MAX_TOKENS]
                             [PREFILL_MAX_OUTPUT_BLOCKS]
                             [PREFILL_OUTPUTS_PER_BLOCK / 2];
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
        ap_uint<128> activation_words[PREFILL_TOKEN_LANES][PREFILL_ACTIVATION_SLOTS];
        half activation_scale[PREFILL_TOKEN_LANES][PREFILL_TOKEN_BATCHES];
        ap_int<16> activation_sum[PREFILL_TOKEN_LANES][PREFILL_TOKEN_BATCHES];
#pragma HLS ARRAY_PARTITION variable=activation_words complete dim=1
#pragma HLS BIND_STORAGE variable=activation_words type=ram_2p impl=lutram latency=2
#pragma HLS ARRAY_PARTITION variable=activation_scale complete dim=1
#pragma HLS ARRAY_PARTITION variable=activation_sum complete dim=1
        load_activation_tile(
            tx, activation_words, activation_scale, activation_sum, token_count, status);
        ap_uint<128> codes_ping[PREFILL_OUTPUTS_PER_BLOCK][2];
        ap_uint<128> codes_pong[PREFILL_OUTPUTS_PER_BLOCK][2];
        half scales_ping[PREFILL_OUTPUTS_PER_BLOCK];
        half scales_pong[PREFILL_OUTPUTS_PER_BLOCK];
        half zeros_ping[PREFILL_OUTPUTS_PER_BLOCK];
        half zeros_pong[PREFILL_OUTPUTS_PER_BLOCK];
#pragma HLS ARRAY_PARTITION variable=codes_ping complete dim=0
#pragma HLS ARRAY_PARTITION variable=codes_pong complete dim=0
#pragma HLS ARRAY_PARTITION variable=scales_ping complete dim=1
#pragma HLS ARRAY_PARTITION variable=scales_pong complete dim=1
#pragma HLS ARRAY_PARTITION variable=zeros_ping complete dim=1
#pragma HLS ARRAY_PARTITION variable=zeros_pong complete dim=1
        load_weight_block(
            tx, codes_ping, scales_ping, zeros_ping, group, input_groups,
            0, output_blocks, status);
    prefetch_compute_block_loop:
        for (unsigned block = 0; block < output_blocks; ++block) {
            const bool has_next = block + 1 < output_blocks;
            if ((block & 1U) == 0) {
                load_and_compute_weight_block(
                    tx, codes_pong, scales_pong, zeros_pong,
                    codes_ping, scales_ping, zeros_ping,
                    activation_words, activation_scale, activation_sum,
                    output_accum, token_count, group, input_groups, block,
                    output_blocks, has_next, status);
            } else {
                load_and_compute_weight_block(
                    tx, codes_ping, scales_ping, zeros_ping,
                    codes_pong, scales_pong, zeros_pong,
                    activation_words, activation_scale, activation_sum,
                    output_accum, token_count, group, input_groups, block,
                    output_blocks, has_next, status);
            }
        }
    }
    write_outputs(rx, output_accum, token_count, output_blocks);
    calls += 1;
    macros += token_count * input_groups * output_blocks;
    call_count = calls;
    processed_macros = macros;
}
