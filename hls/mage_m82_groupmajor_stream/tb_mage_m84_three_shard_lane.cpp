#include "mage_m84_three_shard_lane.hpp"

#include <iostream>
#include <hls_half.h>
#include <hls_math.h>

static ap_uint<16> m84_tb_half_bits(half value) { fp_struct<half> encoded(value); return encoded.data(); }
static ap_uint<32> m84_tb_float_bits(float value) { fp_struct<float> encoded(value); return encoded.data(); }

static void m84_tb_set_code(ap_uint<512> &packed, unsigned row, unsigned lane,
                            unsigned bits, unsigned code) {
    const unsigned base = row * MAGE_T6_GROUP_SIZE * bits + lane * bits;
    packed.range(base + bits - 1, base) = code;
}

static int m84_run_case(unsigned bits) {
    const unsigned groups = 3, words_per_group = 1 + 4 * bits;
    hls::stream<mage_t6_axis128_t> tx; hls::stream<mage_t6_axis64_t> rx;
    ap_int<8> activations[groups][MAGE_T6_TOKENS][MAGE_T6_GROUP_SIZE];
    half activation_scales[groups][MAGE_T6_TOKENS];
    for (unsigned group = 0; group < groups; ++group) for (unsigned token = 0; token < MAGE_T6_TOKENS; ++token) {
        ap_uint<512> packed = 0;
        for (unsigned lane = 0; lane < MAGE_T6_GROUP_SIZE; ++lane) {
            activations[group][token][lane] = (int)((group * 17 + token * 11 + lane * 5) % 127) - 63;
            packed.range(8 * lane + 7, 8 * lane) = (ap_uint<8>)activations[group][token][lane];
        }
        activation_scales[group][token] = (half)(0.002f * (group + 1) * (token + 1));
        for (unsigned word = 0; word < 5; ++word) {
            mage_t6_axis128_t item;
            item.data = word < 4 ? packed.range(128 * word + 127, 128 * word) : (ap_uint<128>)m84_tb_half_bits(activation_scales[group][token]);
            item.keep = -1; item.strb = -1; item.last = group == groups - 1 && token == MAGE_T6_TOKENS - 1 && word == 4; tx.write(item);
        }
    }
    ap_uint<128> memories[M84_SHARDS][64];
    ap_int<5> weights[M84_SHARDS][groups][M82_ROWS_PER_SHARD][MAGE_T6_GROUP_SIZE];
    half weight_scales[M84_SHARDS][groups][M82_ROWS_PER_SHARD];
    for (unsigned shard = 0; shard < M84_SHARDS; ++shard) {
        for (unsigned group = 0; group < groups; ++group) {
            const unsigned base = group * words_per_group; ap_uint<128> scale_word = 0; ap_uint<512> pairs[4];
            for (unsigned slot = 0; slot < 4; ++slot) {
                pairs[slot] = 0;
                for (unsigned local_row = 0; local_row < 2; ++local_row) {
                    const unsigned row = slot * 2 + local_row; const bool orientation = ((shard + group + row) & 1U) != 0;
                    const int qmin = -(1 << (bits - 1)) + (orientation ? 1 : 0);
                    weight_scales[shard][group][row] = (half)(0.004f + 0.0003f * shard + 0.0002f * group + 0.0001f * row);
                    scale_word.range(16 * row + 15, 16 * row) = m84_tb_half_bits(weight_scales[shard][group][row]) | ((ap_uint<16>)orientation << 15);
                    for (unsigned lane = 0; lane < MAGE_T6_GROUP_SIZE; ++lane) {
                        const unsigned code = (shard * 13 + group * 7 + row * 3 + lane) & ((1U << bits) - 1U);
                        m84_tb_set_code(pairs[slot], local_row, lane, bits, code); weights[shard][group][row][lane] = qmin + (int)code;
                    }
                }
            }
            memories[shard][base] = scale_word;
            for (unsigned slot = 0; slot < 4; ++slot) for (unsigned word = 0; word < bits; ++word)
                memories[shard][base + 1 + slot * bits + word] = pairs[slot].range(128 * word + 127, 128 * word);
        }
        for (unsigned word = groups * words_per_group; word < 64; ++word) memories[shard][word] = 0;
    }
    ap_uint<32> status = 0, build = 0, completed = 0;
    mage_m84_three_shard_lane(tx, memories[0], memories[1], memories[2], rx, groups, bits, status, build, completed);
    if (status != 0 || build != M84_EXPECT_BUILD_ID || completed != groups * words_per_group) return 1;
    for (unsigned token = 0; token < MAGE_T6_TOKENS; ++token) for (unsigned shard = 0; shard < M84_SHARDS; ++shard) for (unsigned pair = 0; pair < M82_PAIRS_PER_SHARD; ++pair) {
        const mage_t6_axis64_t item = rx.read();
        for (unsigned local_row = 0; local_row < 2; ++local_row) {
            const unsigned row = pair * 2 + local_row; float expected = 0.0f;
            for (unsigned group = 0; group < groups; ++group) {
                int dot = 0; for (unsigned lane = 0; lane < MAGE_T6_GROUP_SIZE; ++lane) dot += (int)activations[group][token][lane] * (int)weights[shard][group][row][lane];
                const ap_uint<16> scaled = mage_t6_half_mul_bits_rne(m84_tb_half_bits((half)dot), m84_tb_half_bits(activation_scales[group][token]));
                fp_struct<half> term(mage_t6_half_mul_bits_rne(scaled, m84_tb_half_bits(weight_scales[shard][group][row]))); expected += (float)term.to_half();
            }
            const ap_uint<32> actual = local_row == 0 ? item.data.range(31, 0) : item.data.range(63, 32);
            if (actual != m84_tb_float_bits(expected)) return 1;
        }
        const bool expected_last = token == MAGE_T6_TOKENS - 1 && shard == M84_SHARDS - 1 && pair == M82_PAIRS_PER_SHARD - 1;
        if ((bool)item.last != expected_last) return 1;
    }
    return rx.empty() ? 0 : 1;
}

int main() {
    for (unsigned bits = 2; bits <= 4; ++bits) if (m84_run_case(bits)) return 1;
    std::cout << "M84_THREESHARD_EXACT_CSIM_PASS bits=2,3,4 groups=3 rows=8 tokens=6 shards=3" << std::endl;
    return 0;
}
