#include "mage_decode_sixport.hpp"

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

static ap_int<27> pack_weights(ap_int<5> weight0, ap_int<5> weight1) {
#pragma HLS INLINE
    const ap_int<14> upper = (ap_int<14>)weight1 - (weight0 < 0 ? 1 : 0);
    ap_int<27> packed = (ap_int<27>)upper << 13;
    packed.range(12, 0) = (ap_uint<13>)weight0;
    return packed;
}

static void packed_mac2(
    ap_int<8> activation,
    ap_int<5> weight0,
    ap_int<5> weight1,
    ap_int<16> &product0,
    ap_int<16> &product1) {
#pragma HLS INLINE
    const ap_int<27> packed_weights = pack_weights(weight0, weight1);
    const ap_int<45> packed_product = packed_weights * activation;
#pragma HLS BIND_OP variable=packed_product op=mul impl=dsp
    const ap_int<13> low_product = (ap_int<13>)packed_product.range(12, 0);
    ap_int<32> high_product = (ap_int<32>)(packed_product >> 13);
    if (low_product < 0) high_product += 1;
    product0 = low_product;
    product1 = high_product;
}

static void load_activations(
    hls::stream<mage_axis128_t> &activation_tx,
    ap_uint<128> activation0[MAGE_MAX_INPUT_GROUPS][4],
    ap_uint<128> activation1[MAGE_MAX_INPUT_GROUPS][4],
    ap_uint<128> activation2[MAGE_MAX_INPUT_GROUPS][4],
    ap_uint<128> activation3[MAGE_MAX_INPUT_GROUPS][4],
    ap_uint<128> activation4[MAGE_MAX_INPUT_GROUPS][4],
    ap_uint<128> activation5[MAGE_MAX_INPUT_GROUPS][4],
    ap_uint<16> activation_scales[MAGE_MAX_INPUT_GROUPS],
    unsigned input_groups,
    ap_uint<32> &status) {
#pragma HLS INLINE off
load_group:
    for (unsigned group = 0; group < input_groups; ++group) {
    load_word:
        for (unsigned word = 0; word < 5; ++word) {
#pragma HLS PIPELINE II=1
            const mage_axis128_t item = activation_tx.read();
            const bool expected_last = group == input_groups - 1 && word == 4;
            if ((bool)item.last != expected_last) status = 2;
            if (word < 4) {
                activation0[group][word] = item.data;
                activation1[group][word] = item.data;
                activation2[group][word] = item.data;
                activation3[group][word] = item.data;
                activation4[group][word] = item.data;
                activation5[group][word] = item.data;
            } else {
                activation_scales[group] = item.data.range(15, 0);
            }
        }
    }
}

struct mage_result_t {
    ap_uint<32> data;
};

template <int SHARD_ID>
static void run_shard(
    const ap_uint<128> *memory,
    const ap_uint<128> activations[MAGE_MAX_INPUT_GROUPS][4],
    const ap_uint<16> activation_scales[MAGE_MAX_INPUT_GROUPS],
    hls::stream<mage_result_t> &result,
    unsigned input_groups,
    unsigned rows_per_shard,
    unsigned bits,
    unsigned scale_base_words) {
#pragma HLS INLINE off
    float output[MAGE_MAX_ROWS_PER_SHARD];
#pragma HLS BIND_STORAGE variable=output type=ram_2p impl=bram latency=2
clear_output:
    for (unsigned row = 0; row < rows_per_shard; ++row) {
#pragma HLS PIPELINE II=1
        output[row] = 0.0f;
    }

group_loop:
    for (unsigned group = 0; group < input_groups; ++group) {
        ap_int<8> activation[MAGE_GROUP_SIZE];
#pragma HLS ARRAY_PARTITION variable=activation complete dim=1
    decode_activation:
        for (unsigned index = 0; index < MAGE_GROUP_SIZE; ++index) {
#pragma HLS UNROLL
            const unsigned word = index >> 4;
            const unsigned byte = index & 15U;
            activation[index] = (ap_int<8>)activations[group][word].range(
                8 * byte + 7, 8 * byte);
        }
        const float activation_scale = (float)bits_to_half(activation_scales[group]);
        ap_uint<128> scale_word = 0;
    pair_loop:
        for (unsigned pair = 0; pair < rows_per_shard / 2; ++pair) {
            if ((pair & 3U) == 0) {
                const unsigned scale_index = scale_base_words +
                    group * (rows_per_shard / 8) + pair / 4;
                scale_word = memory[scale_index];
            }
            const unsigned scale_slot = 2 * (pair & 3U);
            const ap_uint<16> tagged_scale0 = scale_word.range(
                16 * scale_slot + 15, 16 * scale_slot);
            const ap_uint<16> tagged_scale1 = scale_word.range(
                16 * (scale_slot + 1) + 15, 16 * (scale_slot + 1));
            const bool orientation0 = tagged_scale0[15];
            const bool orientation1 = tagged_scale1[15];
            const ap_uint<16> magnitude0 = tagged_scale0 & 0x7FFFU;
            const ap_uint<16> magnitude1 = tagged_scale1 & 0x7FFFU;
            const float weight_scale0 = (float)bits_to_half(magnitude0);
            const float weight_scale1 = (float)bits_to_half(magnitude1);

            ap_uint<512> packed_codes = 0;
            const unsigned code_index =
                (group * (rows_per_shard / 2) + pair) * bits;
        load_codes:
            for (unsigned word = 0; word < 4; ++word) {
#pragma HLS PIPELINE II=1
                if (word < bits) {
                    packed_codes.range(128 * word + 127, 128 * word) =
                        memory[code_index + word];
                }
            }
            ap_int<5> weights0[MAGE_GROUP_SIZE];
            ap_int<5> weights1[MAGE_GROUP_SIZE];
#pragma HLS ARRAY_PARTITION variable=weights0 complete dim=1
#pragma HLS ARRAY_PARTITION variable=weights1 complete dim=1
            const ap_int<5> qmin0 = orientation0
                ? -(1 << (bits - 1)) + 1 : -(1 << (bits - 1));
            const ap_int<5> qmin1 = orientation1
                ? -(1 << (bits - 1)) + 1 : -(1 << (bits - 1));
            if (bits == 2) {
            decode_w2:
                for (unsigned index = 0; index < MAGE_GROUP_SIZE; ++index) {
#pragma HLS UNROLL
                    weights0[index] = (ap_uint<2>)packed_codes.range(
                        2 * index + 1, 2 * index) + qmin0;
                    weights1[index] = (ap_uint<2>)packed_codes.range(
                        128 + 2 * index + 1, 128 + 2 * index) + qmin1;
                }
            } else if (bits == 3) {
            decode_w3:
                for (unsigned index = 0; index < MAGE_GROUP_SIZE; ++index) {
#pragma HLS UNROLL
                    weights0[index] = (ap_uint<3>)packed_codes.range(
                        3 * index + 2, 3 * index) + qmin0;
                    weights1[index] = (ap_uint<3>)packed_codes.range(
                        192 + 3 * index + 2, 192 + 3 * index) + qmin1;
                }
            } else {
            decode_w4:
                for (unsigned index = 0; index < MAGE_GROUP_SIZE; ++index) {
#pragma HLS UNROLL
                    weights0[index] = (ap_uint<4>)packed_codes.range(
                        4 * index + 3, 4 * index) + qmin0;
                    weights1[index] = (ap_uint<4>)packed_codes.range(
                        256 + 4 * index + 3, 256 + 4 * index) + qmin1;
                }
            }

            ap_int<24> partial0[4];
            ap_int<24> partial1[4];
#pragma HLS ARRAY_PARTITION variable=partial0 complete dim=1
#pragma HLS ARRAY_PARTITION variable=partial1 complete dim=1
        mac_chunk:
            for (unsigned chunk = 0; chunk < 4; ++chunk) {
#pragma HLS PIPELINE II=1
                ap_int<20> sum0 = 0;
                ap_int<20> sum1 = 0;
            mac_lane:
                for (unsigned lane = 0; lane < MAGE_MAC_LANES; ++lane) {
#pragma HLS UNROLL
                    const unsigned index = chunk * MAGE_MAC_LANES + lane;
                    ap_int<16> product0;
                    ap_int<16> product1;
                    packed_mac2(
                        activation[index], weights0[index], weights1[index],
                        product0, product1);
                    sum0 += product0;
                    sum1 += product1;
                }
                partial0[chunk] = sum0;
                partial1[chunk] = sum1;
            }
            const ap_int<24> dot0 = partial0[0] + partial0[1] +
                                    partial0[2] + partial0[3];
            const ap_int<24> dot1 = partial1[0] + partial1[1] +
                                    partial1[2] + partial1[3];
            const unsigned row0 = 2 * pair;
            const unsigned row1 = row0 + 1;
            output[row0] += (float)dot0 * activation_scale * weight_scale0;
            output[row1] += (float)dot1 * activation_scale * weight_scale1;
        }
    }

emit_output:
    for (unsigned row = 0; row < rows_per_shard; ++row) {
#pragma HLS PIPELINE II=1
        mage_result_t item;
        item.data = float_to_bits(output[row]);
        result.write(item);
    }
}

static void merge_results(
    hls::stream<mage_result_t> results[6],
    hls::stream<mage_axis64_t> &rx,
    unsigned rows_per_shard) {
#pragma HLS INLINE off
merge_shard:
    for (unsigned shard = 0; shard < 6; ++shard) {
    merge_pair:
        for (unsigned pair = 0; pair < rows_per_shard / 2; ++pair) {
#pragma HLS PIPELINE II=1
            mage_axis64_t item;
            item.data.range(31, 0) = results[shard].read().data;
            item.data.range(63, 32) = results[shard].read().data;
            item.keep = -1;
            item.strb = -1;
            item.last = shard == 5 && pair == rows_per_shard / 2 - 1;
            rx.write(item);
        }
    }
}

static void run_sixport(
    const ap_uint<128> *shard0,
    const ap_uint<128> *shard1,
    const ap_uint<128> *shard2,
    const ap_uint<128> *shard3,
    const ap_uint<128> *shard4,
    const ap_uint<128> *shard5,
    const ap_uint<128> activation0[MAGE_MAX_INPUT_GROUPS][4],
    const ap_uint<128> activation1[MAGE_MAX_INPUT_GROUPS][4],
    const ap_uint<128> activation2[MAGE_MAX_INPUT_GROUPS][4],
    const ap_uint<128> activation3[MAGE_MAX_INPUT_GROUPS][4],
    const ap_uint<128> activation4[MAGE_MAX_INPUT_GROUPS][4],
    const ap_uint<128> activation5[MAGE_MAX_INPUT_GROUPS][4],
    const ap_uint<16> activation_scales[MAGE_MAX_INPUT_GROUPS],
    hls::stream<mage_axis64_t> &rx,
    unsigned input_groups,
    unsigned rows_per_shard,
    unsigned bits,
    unsigned scale_base_words) {
#pragma HLS INLINE off
#pragma HLS DATAFLOW
    hls::stream<mage_result_t> results[6];
#pragma HLS STREAM variable=results depth=32
    run_shard<0>(shard0, activation0, activation_scales, results[0], input_groups, rows_per_shard, bits, scale_base_words);
    run_shard<1>(shard1, activation1, activation_scales, results[1], input_groups, rows_per_shard, bits, scale_base_words);
    run_shard<2>(shard2, activation2, activation_scales, results[2], input_groups, rows_per_shard, bits, scale_base_words);
    run_shard<3>(shard3, activation3, activation_scales, results[3], input_groups, rows_per_shard, bits, scale_base_words);
    run_shard<4>(shard4, activation4, activation_scales, results[4], input_groups, rows_per_shard, bits, scale_base_words);
    run_shard<5>(shard5, activation5, activation_scales, results[5], input_groups, rows_per_shard, bits, scale_base_words);
    merge_results(results, rx, rows_per_shard);
}

void mage_decode_sixport(
    hls::stream<mage_axis128_t> &activation_tx,
    const ap_uint<128> *shard0,
    const ap_uint<128> *shard1,
    const ap_uint<128> *shard2,
    const ap_uint<128> *shard3,
    const ap_uint<128> *shard4,
    const ap_uint<128> *shard5,
    hls::stream<mage_axis64_t> &rx,
    unsigned input_groups,
    unsigned rows_per_shard,
    unsigned bits,
    unsigned scale_base_words,
    ap_uint<32> &status,
    ap_uint<32> &build_id,
    ap_uint<32> &call_count,
    ap_uint<32> &processed_macros) {
#pragma HLS INTERFACE axis port=activation_tx
#pragma HLS INTERFACE m_axi port=shard0 offset=slave bundle=weights0 depth=262144 max_read_burst_length=64 num_read_outstanding=16
#pragma HLS INTERFACE m_axi port=shard1 offset=slave bundle=weights1 depth=262144 max_read_burst_length=64 num_read_outstanding=16
#pragma HLS INTERFACE m_axi port=shard2 offset=slave bundle=weights2 depth=262144 max_read_burst_length=64 num_read_outstanding=16
#pragma HLS INTERFACE m_axi port=shard3 offset=slave bundle=weights3 depth=262144 max_read_burst_length=64 num_read_outstanding=16
#pragma HLS INTERFACE m_axi port=shard4 offset=slave bundle=weights4 depth=262144 max_read_burst_length=64 num_read_outstanding=16
#pragma HLS INTERFACE m_axi port=shard5 offset=slave bundle=weights5 depth=262144 max_read_burst_length=64 num_read_outstanding=16
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
#pragma HLS INTERFACE s_axilite port=scale_base_words bundle=control
#pragma HLS INTERFACE s_axilite port=status bundle=control
#pragma HLS INTERFACE s_axilite port=build_id bundle=control
#pragma HLS INTERFACE s_axilite port=call_count bundle=control
#pragma HLS INTERFACE s_axilite port=processed_macros bundle=control
#pragma HLS INTERFACE s_axilite port=return bundle=control

    static ap_uint<32> calls = 0;
    static ap_uint<32> macros = 0;
    status = 0;
    build_id = MAGE_SIXPORT_BUILD_ID;
    call_count = calls;
    processed_macros = macros;
    if (input_groups < 1 || input_groups > MAGE_MAX_INPUT_GROUPS ||
        rows_per_shard < 8 || rows_per_shard > MAGE_MAX_ROWS_PER_SHARD ||
        (rows_per_shard & 7U) != 0 || (bits != 2 && bits != 3 && bits != 4)) {
        status = 1;
        return;
    }

    ap_uint<128> activation0[MAGE_MAX_INPUT_GROUPS][4];
    ap_uint<128> activation1[MAGE_MAX_INPUT_GROUPS][4];
    ap_uint<128> activation2[MAGE_MAX_INPUT_GROUPS][4];
    ap_uint<128> activation3[MAGE_MAX_INPUT_GROUPS][4];
    ap_uint<128> activation4[MAGE_MAX_INPUT_GROUPS][4];
    ap_uint<128> activation5[MAGE_MAX_INPUT_GROUPS][4];
    ap_uint<16> activation_scales[MAGE_MAX_INPUT_GROUPS];
#pragma HLS BIND_STORAGE variable=activation0 type=ram_2p impl=uram latency=2
#pragma HLS BIND_STORAGE variable=activation1 type=ram_2p impl=uram latency=2
#pragma HLS BIND_STORAGE variable=activation2 type=ram_2p impl=uram latency=2
#pragma HLS BIND_STORAGE variable=activation3 type=ram_2p impl=uram latency=2
#pragma HLS BIND_STORAGE variable=activation4 type=ram_2p impl=uram latency=2
#pragma HLS BIND_STORAGE variable=activation5 type=ram_2p impl=uram latency=2

    load_activations(
        activation_tx,
        activation0, activation1, activation2,
        activation3, activation4, activation5,
        activation_scales, input_groups, status);
    run_sixport(
        shard0, shard1, shard2, shard3, shard4, shard5,
        activation0, activation1, activation2,
        activation3, activation4, activation5,
        activation_scales, rx,
        input_groups, rows_per_shard, bits, scale_base_words);
    calls += 1;
    macros += input_groups * rows_per_shard * 6;
    call_count = calls;
    processed_macros = macros;
}
