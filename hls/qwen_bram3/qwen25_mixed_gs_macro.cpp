#include "qwen25_mixed_gs_macro.hpp"

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

static void load_weight_block(
    hls::stream<qwen_axis128_t> &tx,
    ap_uint<128> codes[QWEN_GS_OUTPUTS][QWEN_GS_CODE_WORDS_PER_OUTPUT],
    half scales[QWEN_GS_OUTPUTS],
    half zeros[QWEN_GS_OUTPUTS],
    unsigned group,
    unsigned input_groups,
    unsigned block,
    unsigned output_blocks,
    ap_uint<32> &status) {
#pragma HLS INLINE off
#pragma HLS ARRAY_PARTITION variable=codes complete dim=1
#pragma HLS ARRAY_PARTITION variable=scales complete dim=1
#pragma HLS ARRAY_PARTITION variable=zeros complete dim=1
load_weight_word:
    for (unsigned word = 0; word < QWEN_GS_WEIGHT_WORDS; ++word) {
#pragma HLS PIPELINE II=1
        const qwen_axis128_t item = tx.read();
        if (word < QWEN_GS_CODE_WORDS) {
            const unsigned output = word >> 1;
            const unsigned half_word = word & 1U;
            codes[output][half_word] = item.data;
        } else {
load_metadata:
            for (unsigned output = 0; output < QWEN_GS_OUTPUTS; ++output) {
#pragma HLS UNROLL
                const ap_uint<16> bits = item.data.range(
                    16 * output + 15, 16 * output);
                if (word == QWEN_GS_CODE_WORDS) {
                    scales[output] = bits_to_half(bits);
                } else {
                    zeros[output] = bits_to_half(bits);
                }
            }
        }
        const bool expected_last = group == input_groups - 1 &&
            block == output_blocks - 1 && word == QWEN_GS_WEIGHT_WORDS - 1;
        if ((bool)item.last != expected_last) status = 2;
    }
}

static void compute_weight_triplet(
    const ap_uint<128> codes0[QWEN_GS_OUTPUTS][QWEN_GS_CODE_WORDS_PER_OUTPUT],
    const ap_uint<128> codes1[QWEN_GS_OUTPUTS][QWEN_GS_CODE_WORDS_PER_OUTPUT],
    const ap_uint<128> codes2[QWEN_GS_OUTPUTS][QWEN_GS_CODE_WORDS_PER_OUTPUT],
    const half scales0[QWEN_GS_OUTPUTS],
    const half scales1[QWEN_GS_OUTPUTS],
    const half scales2[QWEN_GS_OUTPUTS],
    const half zeros0[QWEN_GS_OUTPUTS],
    const half zeros1[QWEN_GS_OUTPUTS],
    const half zeros2[QWEN_GS_OUTPUTS],
    const half activation[QWEN_GS_GROUP],
    float output_accum[QWEN_GS_OUTPUT_STORAGE][QWEN_GS_OUTPUTS],
    unsigned first_block) {
#pragma HLS INLINE off
#pragma HLS ARRAY_PARTITION variable=codes0 complete dim=1
#pragma HLS ARRAY_PARTITION variable=codes1 complete dim=1
#pragma HLS ARRAY_PARTITION variable=codes2 complete dim=1
#pragma HLS ARRAY_PARTITION variable=scales0 complete dim=1
#pragma HLS ARRAY_PARTITION variable=scales1 complete dim=1
#pragma HLS ARRAY_PARTITION variable=scales2 complete dim=1
#pragma HLS ARRAY_PARTITION variable=zeros0 complete dim=1
#pragma HLS ARRAY_PARTITION variable=zeros1 complete dim=1
#pragma HLS ARRAY_PARTITION variable=zeros2 complete dim=1
    float accum[QWEN_GS_PARALLEL_BLOCKS][QWEN_GS_OUTPUTS];
    float partial_even[QWEN_GS_PARALLEL_BLOCKS][QWEN_GS_OUTPUTS][8];
    float partial_odd[QWEN_GS_PARALLEL_BLOCKS][QWEN_GS_OUTPUTS][8];
#pragma HLS ARRAY_PARTITION variable=accum complete dim=0
#pragma HLS ARRAY_PARTITION variable=partial_even complete dim=0
#pragma HLS ARRAY_PARTITION variable=partial_odd complete dim=0

init_partials:
    for (unsigned lane = 0; lane < QWEN_GS_PARALLEL_BLOCKS; ++lane) {
#pragma HLS UNROLL
        for (unsigned output = 0; output < QWEN_GS_OUTPUTS; ++output) {
#pragma HLS UNROLL
            accum[lane][output] = 0.0f;
            for (unsigned bank = 0; bank < 8; ++bank) {
#pragma HLS UNROLL
                partial_even[lane][output][bank] = 0.0f;
                partial_odd[lane][output][bank] = 0.0f;
            }
        }
    }

mac_group:
    for (unsigned pair = 0; pair < QWEN_GS_GROUP / 2; ++pair) {
#pragma HLS PIPELINE II=1
        const unsigned input0 = 2 * pair;
        const unsigned input1 = input0 + 1;
        const unsigned accum_bank = pair & 7U;
        const unsigned code_word = pair >> 4;
        const unsigned code_byte = pair & 15U;
        const float input_value0 = (float)activation[input0];
        const float input_value1 = (float)activation[input1];
        for (unsigned output = 0; output < QWEN_GS_OUTPUTS; ++output) {
#pragma HLS UNROLL
            const ap_uint<8> packed0 =
                select_code_byte(codes0[output][code_word], code_byte);
            const ap_uint<8> packed1 =
                select_code_byte(codes1[output][code_word], code_byte);
            const ap_uint<8> packed2 =
                select_code_byte(codes2[output][code_word], code_byte);
            const ap_uint<4> code00 = packed0.range(3, 0);
            const ap_uint<4> code01 = packed0.range(7, 4);
            const ap_uint<4> code10 = packed1.range(3, 0);
            const ap_uint<4> code11 = packed1.range(7, 4);
            const ap_uint<4> code20 = packed2.range(3, 0);
            const ap_uint<4> code21 = packed2.range(7, 4);
            partial_even[0][output][accum_bank] +=
                ((float)code00 - (float)zeros0[output]) * input_value0;
            partial_odd[0][output][accum_bank] +=
                ((float)code01 - (float)zeros0[output]) * input_value1;
            partial_even[1][output][accum_bank] +=
                ((float)code10 - (float)zeros1[output]) * input_value0;
            partial_odd[1][output][accum_bank] +=
                ((float)code11 - (float)zeros1[output]) * input_value1;
            partial_even[2][output][accum_bank] +=
                ((float)code20 - (float)zeros2[output]) * input_value0;
            partial_odd[2][output][accum_bank] +=
                ((float)code21 - (float)zeros2[output]) * input_value1;
        }
    }

reduce_partial:
    for (unsigned lane = 0; lane < QWEN_GS_PARALLEL_BLOCKS; ++lane) {
#pragma HLS UNROLL
        for (unsigned output = 0; output < QWEN_GS_OUTPUTS; ++output) {
#pragma HLS UNROLL
            const float e01 = partial_even[lane][output][0] + partial_even[lane][output][1];
            const float e23 = partial_even[lane][output][2] + partial_even[lane][output][3];
            const float e45 = partial_even[lane][output][4] + partial_even[lane][output][5];
            const float e67 = partial_even[lane][output][6] + partial_even[lane][output][7];
            const float o01 = partial_odd[lane][output][0] + partial_odd[lane][output][1];
            const float o23 = partial_odd[lane][output][2] + partial_odd[lane][output][3];
            const float o45 = partial_odd[lane][output][4] + partial_odd[lane][output][5];
            const float o67 = partial_odd[lane][output][6] + partial_odd[lane][output][7];
            const float e0123 = e01 + e23;
            const float e4567 = e45 + e67;
            const float o0123 = o01 + o23;
            const float o4567 = o45 + o67;
            accum[lane][output] = (e0123 + e4567) + (o0123 + o4567);
        }
    }

accumulate_output:
    for (unsigned output = 0; output < QWEN_GS_OUTPUTS; ++output) {
#pragma HLS UNROLL
        output_accum[first_block][output] +=
            accum[0][output] * (float)scales0[output];
        output_accum[first_block + 1][output] +=
            accum[1][output] * (float)scales1[output];
        output_accum[first_block + 2][output] +=
            accum[2][output] * (float)scales2[output];
    }
}

static void clear_weight_block(
    ap_uint<128> codes[QWEN_GS_OUTPUTS][QWEN_GS_CODE_WORDS_PER_OUTPUT],
    half scales[QWEN_GS_OUTPUTS],
    half zeros[QWEN_GS_OUTPUTS]) {
#pragma HLS INLINE
#pragma HLS ARRAY_PARTITION variable=codes complete dim=1
#pragma HLS ARRAY_PARTITION variable=scales complete dim=1
#pragma HLS ARRAY_PARTITION variable=zeros complete dim=1
clear_outputs:
    for (unsigned output = 0; output < QWEN_GS_OUTPUTS; ++output) {
#pragma HLS UNROLL
        codes[output][0] = 0;
        codes[output][1] = 0;
        scales[output] = 0;
        zeros[output] = 0;
    }
}

static void load_weight_triplet(
    hls::stream<qwen_axis128_t> &tx,
    ap_uint<128> codes[QWEN_GS_PARALLEL_BLOCKS]
                       [QWEN_GS_OUTPUTS]
                       [QWEN_GS_CODE_WORDS_PER_OUTPUT],
    half scales[QWEN_GS_PARALLEL_BLOCKS][QWEN_GS_OUTPUTS],
    half zeros[QWEN_GS_PARALLEL_BLOCKS][QWEN_GS_OUTPUTS],
    unsigned group,
    unsigned input_groups,
    unsigned first_block,
    unsigned output_blocks,
    ap_uint<32> &status) {
#pragma HLS INLINE off
#pragma HLS ARRAY_PARTITION variable=codes complete dim=1
#pragma HLS ARRAY_PARTITION variable=codes complete dim=2
#pragma HLS ARRAY_PARTITION variable=scales complete dim=0
#pragma HLS ARRAY_PARTITION variable=zeros complete dim=0
    load_weight_block(tx, codes[0], scales[0], zeros[0], group,
                      input_groups, first_block, output_blocks, status);
    if (first_block + 1 < output_blocks) {
        load_weight_block(tx, codes[1], scales[1], zeros[1], group,
                          input_groups, first_block + 1, output_blocks, status);
    } else {
        clear_weight_block(codes[1], scales[1], zeros[1]);
    }
    if (first_block + 2 < output_blocks) {
        load_weight_block(tx, codes[2], scales[2], zeros[2], group,
                          input_groups, first_block + 2, output_blocks, status);
    } else {
        clear_weight_block(codes[2], scales[2], zeros[2]);
    }
}

static void load_and_compute_triplet(
    hls::stream<qwen_axis128_t> &tx,
    ap_uint<128> next_codes[QWEN_GS_PARALLEL_BLOCKS]
                            [QWEN_GS_OUTPUTS]
                            [QWEN_GS_CODE_WORDS_PER_OUTPUT],
    half next_scales[QWEN_GS_PARALLEL_BLOCKS][QWEN_GS_OUTPUTS],
    half next_zeros[QWEN_GS_PARALLEL_BLOCKS][QWEN_GS_OUTPUTS],
    const ap_uint<128> current_codes[QWEN_GS_PARALLEL_BLOCKS]
                                  [QWEN_GS_OUTPUTS]
                                  [QWEN_GS_CODE_WORDS_PER_OUTPUT],
    const half current_scales[QWEN_GS_PARALLEL_BLOCKS][QWEN_GS_OUTPUTS],
    const half current_zeros[QWEN_GS_PARALLEL_BLOCKS][QWEN_GS_OUTPUTS],
    const half activation[QWEN_GS_GROUP],
    float output_accum[QWEN_GS_OUTPUT_STORAGE][QWEN_GS_OUTPUTS],
    unsigned group,
    unsigned input_groups,
    unsigned next_first_block,
    unsigned output_blocks,
    unsigned current_first_block,
    bool load_next,
    ap_uint<32> &status) {
#pragma HLS INLINE off
#pragma HLS DATAFLOW
#pragma HLS ARRAY_PARTITION variable=next_codes complete dim=1
#pragma HLS ARRAY_PARTITION variable=next_codes complete dim=2
#pragma HLS ARRAY_PARTITION variable=current_codes complete dim=1
#pragma HLS ARRAY_PARTITION variable=current_codes complete dim=2
    if (load_next) {
        load_weight_triplet(tx, next_codes, next_scales, next_zeros,
                            group, input_groups, next_first_block,
                            output_blocks, status);
    }
    compute_weight_triplet(
        current_codes[0], current_codes[1], current_codes[2],
        current_scales[0], current_scales[1], current_scales[2],
        current_zeros[0], current_zeros[1], current_zeros[2],
        activation, output_accum, current_first_block);
}

static void process_weight_group(
    hls::stream<qwen_axis128_t> &tx,
    const half activation[QWEN_GS_GROUP],
    float output_accum[QWEN_GS_OUTPUT_STORAGE][QWEN_GS_OUTPUTS],
    unsigned group,
    unsigned input_groups,
    unsigned output_blocks,
    ap_uint<32> &status) {
#pragma HLS INLINE off
    ap_uint<128> codes_ping[QWEN_GS_PARALLEL_BLOCKS]
                            [QWEN_GS_OUTPUTS]
                            [QWEN_GS_CODE_WORDS_PER_OUTPUT];
    ap_uint<128> codes_pong[QWEN_GS_PARALLEL_BLOCKS]
                            [QWEN_GS_OUTPUTS]
                            [QWEN_GS_CODE_WORDS_PER_OUTPUT];
    half scales_ping[QWEN_GS_PARALLEL_BLOCKS][QWEN_GS_OUTPUTS];
    half scales_pong[QWEN_GS_PARALLEL_BLOCKS][QWEN_GS_OUTPUTS];
    half zeros_ping[QWEN_GS_PARALLEL_BLOCKS][QWEN_GS_OUTPUTS];
    half zeros_pong[QWEN_GS_PARALLEL_BLOCKS][QWEN_GS_OUTPUTS];
#pragma HLS ARRAY_PARTITION variable=codes_ping complete dim=1
#pragma HLS ARRAY_PARTITION variable=codes_ping complete dim=2
#pragma HLS ARRAY_PARTITION variable=codes_pong complete dim=1
#pragma HLS ARRAY_PARTITION variable=codes_pong complete dim=2
#pragma HLS BIND_STORAGE variable=codes_ping type=ram_1p impl=bram latency=1
#pragma HLS BIND_STORAGE variable=codes_pong type=ram_1p impl=bram latency=1
#pragma HLS ARRAY_PARTITION variable=scales_ping complete dim=0
#pragma HLS ARRAY_PARTITION variable=scales_pong complete dim=0
#pragma HLS ARRAY_PARTITION variable=zeros_ping complete dim=0
#pragma HLS ARRAY_PARTITION variable=zeros_pong complete dim=0

    load_weight_triplet(tx, codes_ping, scales_ping, zeros_ping,
                        group, input_groups, 0, output_blocks, status);

prefetch_compute_loop:
    for (unsigned triplet = 0;
         triplet < (output_blocks + QWEN_GS_PARALLEL_BLOCKS - 1) /
                       QWEN_GS_PARALLEL_BLOCKS;
         ++triplet) {
        const unsigned block = QWEN_GS_PARALLEL_BLOCKS * triplet;
        const bool has_next = block + QWEN_GS_PARALLEL_BLOCKS < output_blocks;
        if ((triplet & 1U) == 0) {
            load_and_compute_triplet(
                tx, codes_pong, scales_pong, zeros_pong,
                codes_ping, scales_ping, zeros_ping,
                activation, output_accum, group, input_groups,
                block + QWEN_GS_PARALLEL_BLOCKS, output_blocks,
                block, has_next, status);
        } else {
            load_and_compute_triplet(
                tx, codes_ping, scales_ping, zeros_ping,
                codes_pong, scales_pong, zeros_pong,
                activation, output_accum, group, input_groups,
                block + QWEN_GS_PARALLEL_BLOCKS, output_blocks,
                block, has_next, status);
        }
    }
}

void qwen25_mixed_gs_macro(
    hls::stream<qwen_axis128_t> &tx,
    hls::stream<qwen_axis64_t> &rx,
    unsigned input_groups,
    unsigned output_blocks,
    ap_uint<32> &status,
    ap_uint<32> &build_id,
    ap_uint<32> &call_count,
    ap_uint<32> &processed_macros) {
#pragma HLS INTERFACE axis port=tx
#pragma HLS INTERFACE axis port=rx
#pragma HLS INTERFACE s_axilite port=input_groups bundle=control
#pragma HLS INTERFACE s_axilite port=output_blocks bundle=control
#pragma HLS INTERFACE s_axilite port=status bundle=control
#pragma HLS INTERFACE s_axilite port=build_id bundle=control
#pragma HLS INTERFACE s_axilite port=call_count bundle=control
#pragma HLS INTERFACE s_axilite port=processed_macros bundle=control
#pragma HLS INTERFACE s_axilite port=return bundle=control

    static ap_uint<32> persistent_call_count = 0;
    static ap_uint<32> persistent_macro_count = 0;
    half activation[QWEN_GS_GROUP];
#pragma HLS ARRAY_PARTITION variable=activation complete dim=1
    float output_accum[QWEN_GS_OUTPUT_STORAGE][QWEN_GS_OUTPUTS];
#pragma HLS ARRAY_PARTITION variable=output_accum complete dim=2

    build_id = QWEN_GS_BUILD_ID;
    call_count = persistent_call_count;
    processed_macros = persistent_macro_count;
    status = 0;
    if (input_groups == 0 || input_groups > QWEN_GS_MAX_INPUT_GROUPS) {
        status = 1;
        return;
    }
    if (output_blocks == 0 || output_blocks > QWEN_GS_MAX_OUTPUT_BLOCKS ||
        input_groups * output_blocks > QWEN_GS_MAX_MACROS) {
        status = 3;
        return;
    }

init_output_accum:
    for (unsigned block = 0;
         block < ((output_blocks + QWEN_GS_PARALLEL_BLOCKS - 1) /
                  QWEN_GS_PARALLEL_BLOCKS) * QWEN_GS_PARALLEL_BLOCKS;
         ++block) {
#pragma HLS PIPELINE II=1
        for (unsigned output = 0; output < QWEN_GS_OUTPUTS; ++output) {
#pragma HLS UNROLL
            output_accum[block][output] = 0.0f;
        }
    }

input_group_loop:
    for (unsigned group = 0; group < input_groups; ++group) {
read_activation:
        for (unsigned word = 0; word < QWEN_GS_ACTIVATION_WORDS; ++word) {
#pragma HLS PIPELINE II=1
            const qwen_axis128_t item = tx.read();
            for (unsigned lane = 0; lane < 8; ++lane) {
#pragma HLS UNROLL
                activation[8 * word + lane] = bits_to_half(
                    item.data.range(16 * lane + 15, 16 * lane));
            }
            if ((bool)item.last) status = 2;
        }

        process_weight_group(tx, activation, output_accum,
                             group, input_groups, output_blocks, status);
    }

write_result_blocks:
    for (unsigned block = 0; block < output_blocks; ++block) {
write_result_words:
        for (unsigned word = 0; word < QWEN_GS_RESULT_WORDS; ++word) {
#pragma HLS PIPELINE II=1
            qwen_axis64_t item;
            item.data = 0;
            item.keep = -1;
            item.strb = -1;
            item.last = block == output_blocks - 1 &&
                        word == QWEN_GS_RESULT_WORDS - 1;
            const unsigned output0 = 2 * word;
            const unsigned output1 = output0 + 1;
            item.data.range(31, 0) = float_to_bits(output_accum[block][output0]);
            item.data.range(63, 32) = float_to_bits(output_accum[block][output1]);
            rx.write(item);
        }
    }
    if (status == 0) {
        persistent_call_count++;
        persistent_macro_count += input_groups * output_blocks;
        call_count = persistent_call_count;
        processed_macros = persistent_macro_count;
    }
}
