#include "mage_prefill_t6_arith.hpp"

#include <hls_half.h>
#include <hls_math.h>

static half t6_bits_to_half(ap_uint<16> bits) {
#pragma HLS INLINE
    fp_struct<half> value(bits);
    return value.to_half();
}

static ap_uint<16> t6_half_to_bits(half value) {
#pragma HLS INLINE
    fp_struct<half> encoded(value);
    return encoded.data();
}

ap_uint<16> mage_t6_int24_to_half_bits(ap_int<24> value) {
#pragma HLS INLINE
    const bool sign = value < 0;
    const ap_int<25> widened = value;
    const ap_uint<24> magnitude = sign
        ? (ap_uint<24>)(-widened)
        : (ap_uint<24>)widened;
    if (magnitude == 0) return 0;

    ap_uint<5> msb = 0;
    bool found = false;
i2h_find_msb:
    for (int bit = 23; bit >= 0; --bit) {
#pragma HLS UNROLL
        if (!found && magnitude[bit]) {
            msb = (ap_uint<5>)bit;
            found = true;
        }
    }

    ap_uint<6> exponent = (ap_uint<6>)msb + 15;
    ap_uint<12> significand = 0;
    if (msb <= 10) {
        significand = (ap_uint<12>)(magnitude << (10 - msb));
    } else {
        const ap_uint<5> shift = msb - 10;
        significand = (ap_uint<12>)(magnitude >> shift);
        const ap_uint<24> mask = ((ap_uint<24>)1 << shift) - 1;
        const ap_uint<24> remainder = magnitude & mask;
        const ap_uint<24> halfway = (ap_uint<24>)1 << (shift - 1);
        if (remainder > halfway ||
            (remainder == halfway && significand[0])) {
            significand += 1;
        }
        if (significand == 2048) {
            significand = 1024;
            exponent += 1;
        }
    }

    ap_uint<16> encoded = 0;
    encoded[15] = sign;
    if (exponent >= 31) {
        encoded.range(14, 10) = 31;
        encoded.range(9, 0) = 0;
    } else {
        encoded.range(14, 10) = exponent.range(4, 0);
        encoded.range(9, 0) = significand.range(9, 0);
    }
    return encoded;
}

static ap_int<27> t6_pack_weights(ap_int<5> weight0, ap_int<5> weight1) {
#pragma HLS INLINE
    const ap_int<14> upper = (ap_int<14>)weight1 - (weight0 < 0 ? 1 : 0);
    ap_int<27> packed = (ap_int<27>)upper << 13;
    packed.range(12, 0) = (ap_uint<13>)weight0;
    return packed;
}

static void t6_packed_mac2(
    ap_int<8> activation,
    ap_int<5> weight0,
    ap_int<5> weight1,
    ap_int<16> &product0,
    ap_int<16> &product1) {
#pragma HLS INLINE
    const ap_int<27> packed_weights = t6_pack_weights(weight0, weight1);
    const ap_int<45> packed_product = packed_weights * activation;
#pragma HLS BIND_OP variable=packed_product op=mul impl=dsp
    const ap_int<13> low_product = (ap_int<13>)packed_product.range(12, 0);
    ap_int<32> high_product = (ap_int<32>)(packed_product >> 13);
    if (low_product < 0) high_product += 1;
    product0 = low_product;
    product1 = high_product;
}

static void t6_load_activations(
    hls::stream<mage_t6_axis128_t> &activation_tx,
    ap_uint<128> activation[MAGE_T6_SHARDS][MAGE_T6_TOKENS][4],
    ap_uint<16> scales[MAGE_T6_SHARDS][MAGE_T6_TOKENS],
    ap_uint<32> &status) {
#pragma HLS INLINE off
#pragma HLS ARRAY_PARTITION variable=activation complete dim=1
#pragma HLS ARRAY_PARTITION variable=activation complete dim=2
#pragma HLS ARRAY_PARTITION variable=scales complete dim=1
#pragma HLS ARRAY_PARTITION variable=scales complete dim=2
t6_load_token:
    for (unsigned token = 0; token < MAGE_T6_TOKENS; ++token) {
    t6_load_word:
        for (unsigned word = 0; word < 5; ++word) {
#pragma HLS PIPELINE II=1
            const mage_t6_axis128_t item = activation_tx.read();
            const bool expected_last = token == MAGE_T6_TOKENS - 1 && word == 4;
            if ((bool)item.last != expected_last) status = 2;
            if (word < 4) {
            t6_replicate_activation:
                for (unsigned shard = 0; shard < MAGE_T6_SHARDS; ++shard) {
#pragma HLS UNROLL
                    activation[shard][token][word] = item.data;
                }
            } else {
                const ap_uint<16> scale = item.data.range(15, 0);
            t6_replicate_scale:
                for (unsigned shard = 0; shard < MAGE_T6_SHARDS; ++shard) {
#pragma HLS UNROLL
                    scales[shard][token] = scale;
                }
            }
        }
    }
}

struct t6_result_t {
    ap_uint<32> output0[MAGE_T6_TOKENS];
    ap_uint<32> output1[MAGE_T6_TOKENS];
};

template <int SHARD_ID>
static void t6_run_shard(
    const ap_uint<128> *memory,
    const ap_uint<128> activation[MAGE_T6_TOKENS][4],
    const ap_uint<16> activation_scales[MAGE_T6_TOKENS],
    hls::stream<t6_result_t> &result_stream,
    unsigned bits) {
#pragma HLS INLINE off
#pragma HLS ARRAY_PARTITION variable=activation complete dim=1
#pragma HLS ARRAY_PARTITION variable=activation_scales complete dim=1
    const ap_uint<128> tagged_scales = memory[0];
    ap_uint<512> codes = 0;
t6_load_code_word:
    for (unsigned word = 0; word < 4; ++word) {
#pragma HLS PIPELINE II=1
        if (word < bits) {
            codes.range(128 * word + 127, 128 * word) = memory[1 + word];
        }
    }

    ap_int<24> dot0[MAGE_T6_TOKENS];
    ap_int<24> dot1[MAGE_T6_TOKENS];
#pragma HLS ARRAY_PARTITION variable=dot0 complete dim=1
#pragma HLS ARRAY_PARTITION variable=dot1 complete dim=1
t6_clear_dot:
    for (unsigned token = 0; token < MAGE_T6_TOKENS; ++token) {
#pragma HLS UNROLL
        dot0[token] = 0;
        dot1[token] = 0;
    }

    const ap_uint<16> tagged0 = tagged_scales.range(15, 0);
    const ap_uint<16> tagged1 = tagged_scales.range(31, 16);
    const bool orientation0 = tagged0[15];
    const bool orientation1 = tagged1[15];
    const ap_int<5> half_range = (ap_int<5>)(1 << (bits - 1));
    const ap_int<5> negative_half = (ap_int<5>)(-half_range);
    const ap_int<5> shifted_half = (ap_int<5>)(negative_half + (ap_int<5>)1);
    const ap_int<5> qmin0 = orientation0 ? shifted_half : negative_half;
    const ap_int<5> qmin1 = orientation1 ? shifted_half : negative_half;
t6_chunk:
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
    t6_token:
        for (unsigned token = 0; token < MAGE_T6_TOKENS; ++token) {
#pragma HLS UNROLL
            ap_uint<256> activation_bits = 0;
            activation_bits.range(127, 0) = activation[token][2 * chunk];
            activation_bits.range(255, 128) = activation[token][2 * chunk + 1];
            ap_int<20> partial0 = 0;
            ap_int<20> partial1 = 0;
        t6_lane:
            for (unsigned lane = 0; lane < MAGE_T6_MAC_LANES; ++lane) {
#pragma HLS UNROLL
                const ap_int<8> input = (ap_int<8>)activation_bits.range(
                    8 * lane + 7, 8 * lane);
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
            dot0[token] += partial0;
            dot1[token] += partial1;
        }
    }

    const half weight_scale0 = t6_bits_to_half(tagged0 & 0x7FFFU);
    const half weight_scale1 = t6_bits_to_half(tagged1 & 0x7FFFU);
    t6_result_t result;
#pragma HLS ARRAY_PARTITION variable=result.output0 complete dim=1
#pragma HLS ARRAY_PARTITION variable=result.output1 complete dim=1
t6_dequant_token:
    for (unsigned token = 0; token < MAGE_T6_TOKENS; ++token) {
#pragma HLS UNROLL
        const half activation_scale = t6_bits_to_half(activation_scales[token]);
        const half dot_half0 = t6_bits_to_half(
            mage_t6_int24_to_half_bits(dot0[token]));
        const half dot_half1 = t6_bits_to_half(
            mage_t6_int24_to_half_bits(dot1[token]));
        const half scaled0 = dot_half0 * activation_scale;
        const half scaled1 = dot_half1 * activation_scale;
        const half output0 = scaled0 * weight_scale0;
        const half output1 = scaled1 * weight_scale1;
        result.output0[token] = (ap_uint<32>)t6_half_to_bits(output0);
        result.output1[token] = (ap_uint<32>)t6_half_to_bits(output1);
    }
    result_stream.write(result);
}

static void t6_merge(
    hls::stream<t6_result_t> results[MAGE_T6_SHARDS],
    hls::stream<mage_t6_axis64_t> &rx) {
#pragma HLS INLINE off
    t6_result_t buffered[MAGE_T6_SHARDS];
#pragma HLS ARRAY_PARTITION variable=buffered complete dim=1
t6_read_shard:
    for (unsigned shard = 0; shard < MAGE_T6_SHARDS; ++shard) {
#pragma HLS PIPELINE II=1
        buffered[shard] = results[shard].read();
    }
t6_emit_token:
    for (unsigned token = 0; token < MAGE_T6_TOKENS; ++token) {
    t6_emit_shard:
        for (unsigned shard = 0; shard < MAGE_T6_SHARDS; ++shard) {
#pragma HLS PIPELINE II=1
            mage_t6_axis64_t item;
            item.data.range(31, 0) = buffered[shard].output0[token];
            item.data.range(63, 32) = buffered[shard].output1[token];
            item.keep = -1;
            item.strb = -1;
            item.last = token == MAGE_T6_TOKENS - 1 && shard == MAGE_T6_SHARDS - 1;
            rx.write(item);
        }
    }
}

static void t6_six_shards(
    const ap_uint<128> *shard0,
    const ap_uint<128> *shard1,
    const ap_uint<128> *shard2,
    const ap_uint<128> *shard3,
    const ap_uint<128> *shard4,
    const ap_uint<128> *shard5,
    const ap_uint<128> activation[MAGE_T6_SHARDS][MAGE_T6_TOKENS][4],
    const ap_uint<16> scales[MAGE_T6_SHARDS][MAGE_T6_TOKENS],
    hls::stream<mage_t6_axis64_t> &rx,
    unsigned bits) {
#pragma HLS INLINE off
#pragma HLS DATAFLOW
#pragma HLS ARRAY_PARTITION variable=activation complete dim=1
#pragma HLS ARRAY_PARTITION variable=activation complete dim=2
#pragma HLS ARRAY_PARTITION variable=scales complete dim=1
#pragma HLS ARRAY_PARTITION variable=scales complete dim=2
    hls::stream<t6_result_t> results[MAGE_T6_SHARDS];
#pragma HLS ARRAY_PARTITION variable=results complete dim=1
#pragma HLS STREAM variable=results depth=2
    t6_run_shard<0>(shard0, activation[0], scales[0], results[0], bits);
    t6_run_shard<1>(shard1, activation[1], scales[1], results[1], bits);
    t6_run_shard<2>(shard2, activation[2], scales[2], results[2], bits);
    t6_run_shard<3>(shard3, activation[3], scales[3], results[3], bits);
    t6_run_shard<4>(shard4, activation[4], scales[4], results[4], bits);
    t6_run_shard<5>(shard5, activation[5], scales[5], results[5], bits);
    t6_merge(results, rx);
}

void mage_prefill_t6_arith(
    hls::stream<mage_t6_axis128_t> &activation_tx,
    const ap_uint<128> *shard0,
    const ap_uint<128> *shard1,
    const ap_uint<128> *shard2,
    const ap_uint<128> *shard3,
    const ap_uint<128> *shard4,
    const ap_uint<128> *shard5,
    hls::stream<mage_t6_axis64_t> &rx,
    unsigned bits,
    ap_uint<32> &status,
    ap_uint<32> &build_id,
    ap_uint<32> &call_count,
    ap_uint<32> &processed_macros) {
#pragma HLS INTERFACE axis port=activation_tx
#pragma HLS INTERFACE m_axi port=shard0 offset=slave bundle=weights0 depth=5
#pragma HLS INTERFACE m_axi port=shard1 offset=slave bundle=weights1 depth=5
#pragma HLS INTERFACE m_axi port=shard2 offset=slave bundle=weights2 depth=5
#pragma HLS INTERFACE m_axi port=shard3 offset=slave bundle=weights3 depth=5
#pragma HLS INTERFACE m_axi port=shard4 offset=slave bundle=weights4 depth=5
#pragma HLS INTERFACE m_axi port=shard5 offset=slave bundle=weights5 depth=5
#pragma HLS INTERFACE axis port=rx
#pragma HLS INTERFACE s_axilite port=shard0 bundle=control
#pragma HLS INTERFACE s_axilite port=shard1 bundle=control
#pragma HLS INTERFACE s_axilite port=shard2 bundle=control
#pragma HLS INTERFACE s_axilite port=shard3 bundle=control
#pragma HLS INTERFACE s_axilite port=shard4 bundle=control
#pragma HLS INTERFACE s_axilite port=shard5 bundle=control
#pragma HLS INTERFACE s_axilite port=bits bundle=control
#pragma HLS INTERFACE s_axilite port=status bundle=control
#pragma HLS INTERFACE s_axilite port=build_id bundle=control
#pragma HLS INTERFACE s_axilite port=call_count bundle=control
#pragma HLS INTERFACE s_axilite port=processed_macros bundle=control
#pragma HLS INTERFACE s_axilite port=return bundle=control
    static ap_uint<32> calls = 0;
    static ap_uint<32> macros = 0;
    status = 0;
    build_id = MAGE_T6_BUILD_ID;
    call_count = calls;
    processed_macros = macros;
    if (bits != 2 && bits != 3 && bits != 4) {
        status = 1;
        return;
    }

    ap_uint<128> activation[MAGE_T6_SHARDS][MAGE_T6_TOKENS][4];
    ap_uint<16> scales[MAGE_T6_SHARDS][MAGE_T6_TOKENS];
#pragma HLS ARRAY_PARTITION variable=activation complete dim=1
#pragma HLS ARRAY_PARTITION variable=activation complete dim=2
#pragma HLS ARRAY_PARTITION variable=scales complete dim=1
#pragma HLS ARRAY_PARTITION variable=scales complete dim=2
    t6_load_activations(activation_tx, activation, scales, status);
    t6_six_shards(
        shard0, shard1, shard2, shard3, shard4, shard5,
        activation, scales, rx, bits);
    calls += 1;
    macros += MAGE_T6_TOKENS * MAGE_T6_SHARDS * 2 * MAGE_T6_GROUP_SIZE;
    call_count = calls;
    processed_macros = macros;
}
