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

ap_uint<16> mage_t6_half_mul_bits_rne(ap_uint<16> a, ap_uint<16> b) {
#pragma HLS INLINE
    const ap_uint<1> sign = a[15] ^ b[15];
    const ap_uint<5> exp_a = a.range(14, 10);
    const ap_uint<5> exp_b = b.range(14, 10);
    const ap_uint<10> frac_a = a.range(9, 0);
    const ap_uint<10> frac_b = b.range(9, 0);
    const bool zero_a = exp_a == 0 && frac_a == 0;
    const bool zero_b = exp_b == 0 && frac_b == 0;
    const bool nan_a = exp_a == 31 && frac_a != 0;
    const bool nan_b = exp_b == 31 && frac_b != 0;
    const bool inf_a = exp_a == 31 && frac_a == 0;
    const bool inf_b = exp_b == 31 && frac_b == 0;

    ap_uint<16> encoded = 0;
    encoded[15] = sign;
    if (nan_a || nan_b || ((inf_a || inf_b) && (zero_a || zero_b))) {
        encoded.range(14, 10) = 31;
        encoded.range(9, 0) = 0x200; // canonical quiet NaN
        return encoded;
    }
    if (inf_a || inf_b) {
        encoded.range(14, 10) = 31;
        return encoded;
    }
    if (zero_a || zero_b) return encoded;

    const ap_uint<11> mantissa_a = exp_a == 0
        ? (ap_uint<11>)frac_a
        : (ap_uint<11>)(1024U | frac_a);
    const ap_uint<11> mantissa_b = exp_b == 0
        ? (ap_uint<11>)frac_b
        : (ap_uint<11>)(1024U | frac_b);
    ap_int<8> binary_exp_a = -24;
    ap_int<8> binary_exp_b = -24;
    if (exp_a != 0) binary_exp_a = (ap_int<8>)exp_a - (ap_int<8>)25;
    if (exp_b != 0) binary_exp_b = (ap_int<8>)exp_b - (ap_int<8>)25;
#ifdef MAGE_T6_EXACT_SHIFT_ADD
    // Express the 11x11 mantissa product as a balanced shift/add tree.  The
    // earlier BIND_OP hint was not honored after inlining and Vivado mapped
    // every exact multiplier to two DSP48s.  This form contains no multiply
    // operation and therefore reserves those DSPs for the integer array or a
    // later fused Attention stage.
    ap_uint<22> product_terms[16];
#pragma HLS ARRAY_PARTITION variable=product_terms complete dim=1
t6_hmul_partial_products:
    for (unsigned bit = 0; bit < 16; ++bit) {
#pragma HLS UNROLL
        product_terms[bit] = bit < 11 && mantissa_b[bit]
            ? (ap_uint<22>)mantissa_a << bit
            : (ap_uint<22>)0;
    }
    ap_uint<22> product_l1[8];
    ap_uint<22> product_l2[4];
    ap_uint<22> product_l3[2];
#pragma HLS ARRAY_PARTITION variable=product_l1 complete dim=1
#pragma HLS ARRAY_PARTITION variable=product_l2 complete dim=1
#pragma HLS ARRAY_PARTITION variable=product_l3 complete dim=1
t6_hmul_reduce_l1:
    for (unsigned i = 0; i < 8; ++i) {
#pragma HLS UNROLL
        product_l1[i] = product_terms[2 * i] + product_terms[2 * i + 1];
    }
t6_hmul_reduce_l2:
    for (unsigned i = 0; i < 4; ++i) {
#pragma HLS UNROLL
        product_l2[i] = product_l1[2 * i] + product_l1[2 * i + 1];
    }
t6_hmul_reduce_l3:
    for (unsigned i = 0; i < 2; ++i) {
#pragma HLS UNROLL
        product_l3[i] = product_l2[2 * i] + product_l2[2 * i + 1];
    }
    const ap_uint<22> product = product_l3[0] + product_l3[1];
#else
    const ap_uint<22> product = mantissa_a * mantissa_b;
#pragma HLS BIND_OP variable=product op=mul impl=fabric
#endif

    ap_uint<5> msb = 0;
    bool found = false;
t6_hmul_find_msb:
    for (int bit = 21; bit >= 0; --bit) {
#pragma HLS UNROLL
        if (!found && product[bit]) {
            msb = (ap_uint<5>)bit;
            found = true;
        }
    }

    ap_int<9> true_exp = (ap_int<9>)msb + binary_exp_a + binary_exp_b;
    if (true_exp > 15) {
        encoded.range(14, 10) = 31;
        return encoded;
    }

    if (true_exp >= -14) {
        const ap_int<6> shift_signed = (ap_int<6>)msb - 10;
        ap_uint<12> significand = 0;
        if (shift_signed <= 0) {
            significand = (ap_uint<12>)(product << (unsigned)(-shift_signed));
        } else {
            const ap_uint<5> shift = (ap_uint<5>)shift_signed;
            significand = (ap_uint<12>)(product >> shift);
            const ap_uint<22> mask = ((ap_uint<22>)1 << shift) - 1;
            const ap_uint<22> remainder = product & mask;
            const ap_uint<22> halfway = (ap_uint<22>)1 << (shift - 1);
            if (remainder > halfway ||
                (remainder == halfway && significand[0])) {
                significand += 1;
            }
        }
        if (significand == 2048) {
            significand = 1024;
            true_exp += 1;
        }
        if (true_exp > 15) {
            encoded.range(14, 10) = 31;
            return encoded;
        }
        encoded.range(14, 10) = (ap_uint<5>)(true_exp + 15);
        encoded.range(9, 0) = significand.range(9, 0);
        return encoded;
    }

    // Subnormal result: round product / 2^(-24) directly.  Products needing
    // a shift wider than the 22-bit mantissa product round to signed zero.
    const ap_int<9> sub_shift_signed =
        -((ap_int<9>)binary_exp_a + binary_exp_b + 24);
    ap_uint<12> subnormal = 0;
    if (sub_shift_signed <= 0) {
        subnormal = (ap_uint<12>)(product << (unsigned)(-sub_shift_signed));
    } else if (sub_shift_signed <= 22) {
        const ap_uint<5> shift = (ap_uint<5>)sub_shift_signed;
        subnormal = (ap_uint<12>)(product >> shift);
        const ap_uint<22> mask = ((ap_uint<22>)1 << shift) - 1;
        const ap_uint<22> remainder = product & mask;
        const ap_uint<22> halfway = (ap_uint<22>)1 << (shift - 1);
        if (remainder > halfway ||
            (remainder == halfway && subnormal[0])) {
            subnormal += 1;
        }
    }
    if (subnormal >= 1024) {
        encoded.range(14, 10) = 1;
        encoded.range(9, 0) = 0;
    } else {
        encoded.range(9, 0) = subnormal.range(9, 0);
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
    ap_uint<16> scales[MAGE_T6_TOKENS],
    ap_uint<32> &status) {
#pragma HLS INLINE off
#pragma HLS ARRAY_PARTITION variable=activation complete dim=1
#pragma HLS ARRAY_PARTITION variable=activation complete dim=2
#pragma HLS ARRAY_PARTITION variable=scales complete dim=1
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
                scales[token] = item.data.range(15, 0);
            }
        }
    }
}

struct t6_raw_result_t {
    ap_int<24> dot0[MAGE_T6_TOKENS];
    ap_int<24> dot1[MAGE_T6_TOKENS];
    ap_uint<16> weight_scale0;
    ap_uint<16> weight_scale1;
};

#ifdef MAGE_T6_PREDECODE_WEIGHTS
static void t6_predecode_weights(
    const ap_uint<512> &codes,
    unsigned bits,
    ap_int<5> qmin0,
    ap_int<5> qmin1,
    ap_int<5> decoded0[2][MAGE_T6_MAC_LANES],
    ap_int<5> decoded1[2][MAGE_T6_MAC_LANES]) {
#pragma HLS INLINE off
#pragma HLS ARRAY_PARTITION variable=decoded0 complete dim=1
#pragma HLS ARRAY_PARTITION variable=decoded0 complete dim=2
#pragma HLS ARRAY_PARTITION variable=decoded1 complete dim=1
#pragma HLS ARRAY_PARTITION variable=decoded1 complete dim=2
t6_predecode_chunk:
    for (unsigned chunk = 0; chunk < 2; ++chunk) {
#pragma HLS UNROLL
    t6_predecode_lane:
        for (unsigned lane = 0; lane < MAGE_T6_MAC_LANES; ++lane) {
#pragma HLS UNROLL
            const unsigned index = chunk * MAGE_T6_MAC_LANES + lane;
            ap_uint<4> raw0 = 0;
            ap_uint<4> raw1 = 0;
            if (bits == 2) {
                raw0 = codes.range(2 * index + 1, 2 * index);
                raw1 = codes.range(128 + 2 * index + 1, 128 + 2 * index);
            } else if (bits == 3) {
                raw0 = codes.range(3 * index + 2, 3 * index);
                raw1 = codes.range(192 + 3 * index + 2, 192 + 3 * index);
            } else {
                raw0 = codes.range(4 * index + 3, 4 * index);
                raw1 = codes.range(256 + 4 * index + 3, 256 + 4 * index);
            }
            decoded0[chunk][lane] = (ap_int<5>)raw0 + qmin0;
            decoded1[chunk][lane] = (ap_int<5>)raw1 + qmin1;
        }
    }
}
#endif

template <int SHARD_ID>
static void t6_run_shard(
    const ap_uint<128> *memory,
    const ap_uint<128> activation[MAGE_T6_TOKENS][4],
    hls::stream<t6_raw_result_t> &result_stream,
    unsigned bits) {
#pragma HLS INLINE off
#pragma HLS ARRAY_PARTITION variable=activation complete dim=1
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
#ifdef MAGE_T6_PREDECODE_WEIGHTS
    // Decode each packed code once per shard and retain it in a fully
    // partitioned register bank.  Six token lanes then share these values
    // instead of replicating the dynamic W2/W3/W4 decode cone six times.
    ap_int<5> decoded0[2][MAGE_T6_MAC_LANES];
    ap_int<5> decoded1[2][MAGE_T6_MAC_LANES];
#pragma HLS ARRAY_PARTITION variable=decoded0 complete dim=1
#pragma HLS ARRAY_PARTITION variable=decoded0 complete dim=2
#pragma HLS ARRAY_PARTITION variable=decoded1 complete dim=1
#pragma HLS ARRAY_PARTITION variable=decoded1 complete dim=2
    t6_predecode_weights(codes, bits, qmin0, qmin1, decoded0, decoded1);
#endif
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
#ifdef MAGE_T6_PREDECODE_WEIGHTS
                weight0 = decoded0[chunk][lane];
                weight1 = decoded1[chunk][lane];
#else
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
#endif
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

    t6_raw_result_t result;
#pragma HLS ARRAY_PARTITION variable=result.dot0 complete dim=1
#pragma HLS ARRAY_PARTITION variable=result.dot1 complete dim=1
t6_copy_dot:
    for (unsigned token = 0; token < MAGE_T6_TOKENS; ++token) {
#pragma HLS UNROLL
        result.dot0[token] = dot0[token];
        result.dot1[token] = dot1[token];
    }
    result.weight_scale0 = tagged0 & 0x7FFFU;
    result.weight_scale1 = tagged1 & 0x7FFFU;
    result_stream.write(result);
}

static void t6_merge_shared_dequant(
    hls::stream<t6_raw_result_t> results[MAGE_T6_SHARDS],
    const ap_uint<16> activation_scales[MAGE_T6_TOKENS],
    hls::stream<mage_t6_axis64_t> &rx) {
#pragma HLS INLINE off
#pragma HLS ARRAY_PARTITION variable=results complete dim=1
#pragma HLS ARRAY_PARTITION variable=activation_scales complete dim=1
    t6_raw_result_t buffered[MAGE_T6_SHARDS];
#pragma HLS ARRAY_PARTITION variable=buffered complete dim=1
    ap_uint<16> output0[MAGE_T6_TOKENS][MAGE_T6_SHARDS];
    ap_uint<16> output1[MAGE_T6_TOKENS][MAGE_T6_SHARDS];
#pragma HLS ARRAY_PARTITION variable=output0 complete dim=1
#pragma HLS ARRAY_PARTITION variable=output1 complete dim=1
#ifndef MAGE_T6_DSP_FREE_DEQUANT
#pragma HLS ARRAY_PARTITION variable=output0 complete dim=2
#pragma HLS ARRAY_PARTITION variable=output1 complete dim=2
#endif
t6_read_shard:
    for (unsigned shard = 0; shard < MAGE_T6_SHARDS; ++shard) {
#pragma HLS PIPELINE II=1
        buffered[shard] = results[shard].read();
    }

#ifdef MAGE_T6_DSP_FREE_DEQUANT
// M75: keep the M74 packed MAC array unchanged, but remove every native
// half-multiply from dequant. Each token/shard item is evaluated in a
// time-shared schedule: two outputs per cycle, each preserving the original
// two-stage FP16 rounding order:
//   half(dot) * activation_scale, then * weight_scale.
// This trades dequant latency for DSP headroom needed by a later
// fused/time-shared Attention path and full-overlay integration.
t6_dspfree_dequant_token:
    for (unsigned token = 0; token < MAGE_T6_TOKENS; ++token) {
    t6_dspfree_dequant_shard:
        for (unsigned shard = 0; shard < MAGE_T6_SHARDS; ++shard) {
#pragma HLS PIPELINE II=1
            const ap_uint<16> dot0_bits = t6_half_to_bits((half)buffered[shard].dot0[token]);
            const ap_uint<16> dot1_bits = t6_half_to_bits((half)buffered[shard].dot1[token]);
            const ap_uint<16> scaled0 = mage_t6_half_mul_bits_rne(dot0_bits, activation_scales[token]);
            const ap_uint<16> scaled1 = mage_t6_half_mul_bits_rne(dot1_bits, activation_scales[token]);
            output0[token][shard] = mage_t6_half_mul_bits_rne(scaled0, buffered[shard].weight_scale0);
            output1[token][shard] = mage_t6_half_mul_bits_rne(scaled1, buffered[shard].weight_scale1);
        }
    }
#else
// Thirty-six output rows are evaluated per cycle.  Two cycles cover all six
// tokens, matching the two-cycle packed-integer group schedule while using
// half as many dequant multipliers as the fully replicated M68 structure.
t6_dequant_batch:
    for (unsigned batch = 0; batch < 2; ++batch) {
#pragma HLS PIPELINE II=1
    t6_dequant_token_lane:
        for (unsigned lane = 0; lane < MAGE_T6_DEQUANT_TOKEN_LANES; ++lane) {
#pragma HLS UNROLL
            const unsigned token = batch * MAGE_T6_DEQUANT_TOKEN_LANES + lane;
            const half activation_scale = t6_bits_to_half(activation_scales[token]);
        t6_dequant_shard:
            for (unsigned shard = 0; shard < MAGE_T6_SHARDS; ++shard) {
#pragma HLS UNROLL
                const half weight_scale0 = t6_bits_to_half(buffered[shard].weight_scale0);
                const half weight_scale1 = t6_bits_to_half(buffered[shard].weight_scale1);
                const half scaled0 = (half)buffered[shard].dot0[token] * activation_scale;
                const half scaled1 = (half)buffered[shard].dot1[token] * activation_scale;
#ifdef MAGE_T6_WEIGHT_SCALE_FABRIC_EXACT
                output0[token][shard] = mage_t6_half_mul_bits_rne(
                    t6_half_to_bits(scaled0), buffered[shard].weight_scale0);
                output1[token][shard] = mage_t6_half_mul_bits_rne(
                    t6_half_to_bits(scaled1), buffered[shard].weight_scale1);
#elif defined(MAGE_T6_WEIGHT_SCALE_HYBRID_EXACT)
                // The completely unrolled lane index is constant after HLS
                // unrolling.  Two lanes use exact fabric arithmetic and the
                // third retains the native half core: 24 fabric hmul + 48
                // native hmul total, exactly fitting the 1248-DSP device.
                if (lane < 2) {
                    output0[token][shard] = mage_t6_half_mul_bits_rne(
                        t6_half_to_bits(scaled0), buffered[shard].weight_scale0);
                    output1[token][shard] = mage_t6_half_mul_bits_rne(
                        t6_half_to_bits(scaled1), buffered[shard].weight_scale1);
                } else {
                    const half weighted0 = scaled0 * weight_scale0;
                    const half weighted1 = scaled1 * weight_scale1;
                    output0[token][shard] = t6_half_to_bits(weighted0);
                    output1[token][shard] = t6_half_to_bits(weighted1);
                }
#else
                const half weighted0 = scaled0 * weight_scale0;
                const half weighted1 = scaled1 * weight_scale1;
#ifdef MAGE_T6_WEIGHT_SCALE_FABRIC
#pragma HLS BIND_OP variable=weighted0 op=mul impl=fabric
#pragma HLS BIND_OP variable=weighted1 op=mul impl=fabric
#endif
#ifdef MAGE_T6_WEIGHT_SCALE_MEDDSP
#pragma HLS BIND_OP variable=weighted0 op=hmul impl=meddsp
#pragma HLS BIND_OP variable=weighted1 op=hmul impl=meddsp
#endif
                output0[token][shard] = t6_half_to_bits(weighted0);
                output1[token][shard] = t6_half_to_bits(weighted1);
#endif
            }
        }
    }
#endif
t6_emit_token:
    for (unsigned token = 0; token < MAGE_T6_TOKENS; ++token) {
    t6_emit_shard:
        for (unsigned shard = 0; shard < MAGE_T6_SHARDS; ++shard) {
#pragma HLS PIPELINE II=1
            mage_t6_axis64_t item;
            item.data = 0;
            item.data.range(15, 0) = output0[token][shard];
            item.data.range(47, 32) = output1[token][shard];
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
    const ap_uint<16> scales[MAGE_T6_TOKENS],
    hls::stream<mage_t6_axis64_t> &rx,
    unsigned bits) {
#pragma HLS INLINE off
#pragma HLS DATAFLOW
#pragma HLS ARRAY_PARTITION variable=activation complete dim=1
#pragma HLS ARRAY_PARTITION variable=activation complete dim=2
#pragma HLS ARRAY_PARTITION variable=scales complete dim=1
    hls::stream<t6_raw_result_t> results[MAGE_T6_SHARDS];
#pragma HLS ARRAY_PARTITION variable=results complete dim=1
#pragma HLS STREAM variable=results depth=2
    t6_run_shard<0>(shard0, activation[0], results[0], bits);
    t6_run_shard<1>(shard1, activation[1], results[1], bits);
    t6_run_shard<2>(shard2, activation[2], results[2], bits);
    t6_run_shard<3>(shard3, activation[3], results[3], bits);
    t6_run_shard<4>(shard4, activation[4], results[4], bits);
    t6_run_shard<5>(shard5, activation[5], results[5], bits);
    t6_merge_shared_dequant(results, scales, rx);
}

void m75b_t6rt(
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
    build_id = MAGE_T6_BUILD_ID;
    call_count = calls;
    processed_macros = macros;
    if (input_groups != 1 || rows_per_shard != 2) {
        status = 3;
        return;
    }
    if (bits != 2 && bits != 3 && bits != 4) {
        status = 1;
        return;
    }

    ap_uint<128> activation[MAGE_T6_SHARDS][MAGE_T6_TOKENS][4];
    ap_uint<16> scales[MAGE_T6_TOKENS];
#pragma HLS ARRAY_PARTITION variable=activation complete dim=1
#pragma HLS ARRAY_PARTITION variable=activation complete dim=2
#pragma HLS ARRAY_PARTITION variable=scales complete dim=1
    t6_load_activations(activation_tx, activation, scales, status);
    t6_six_shards(
        shard0, shard1, shard2, shard3, shard4, shard5,
        activation, scales, rx, bits);
    calls += 1;
    macros += MAGE_T6_TOKENS * MAGE_T6_SHARDS * rows_per_shard * MAGE_T6_GROUP_SIZE;
    call_count = calls;
    processed_macros = macros;
}
