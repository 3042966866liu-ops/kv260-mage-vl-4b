#include "mage_prefill_t6_runtime_full_m75c.hpp"

#include <cmath>
#include <cstdint>
#include <iostream>
#include <random>

#include <hls_half.h>
#include <hls_math.h>

static ap_uint<16> tb_half_bits(half value) {
    fp_struct<half> encoded(value);
    return encoded.data();
}

static ap_uint<32> tb_float_bits(float value) {
    fp_struct<float> encoded(value);
    return encoded.data();
}

static void tb_set_code(ap_uint<512> &packed, unsigned row, unsigned lane, unsigned bits, unsigned code) {
    const unsigned base = row * MAGE_T6_GROUP_SIZE * bits + lane * bits;
    packed.range(base + bits - 1, base) = code;
}

static int run_case(unsigned bits) {
    const unsigned input_groups = 3;
    const unsigned rows_per_shard = 8;
    const unsigned blocks_per_group = rows_per_shard / 8;
    const unsigned block_words = 1 + 4 * bits;
    const unsigned shard_words = input_groups * blocks_per_group * block_words;
    std::mt19937 rng(0x4D47324BU + bits);
    std::uniform_int_distribution<int> activation_dist(-80, 80);
    std::uniform_int_distribution<int> code_dist(0, (1 << bits) - 1);
    std::uniform_int_distribution<int> orientation_dist(0, 1);

    hls::stream<mage_t6_axis128_t> tx;
    hls::stream<mage_t6_axis64_t> rx;
    ap_int<8> activations[input_groups][MAGE_T6_TOKENS][MAGE_T6_GROUP_SIZE];
    half activation_scales[input_groups][MAGE_T6_TOKENS];
    for (unsigned group = 0; group < input_groups; ++group) {
        for (unsigned token = 0; token < MAGE_T6_TOKENS; ++token) {
            ap_uint<512> packed = 0;
            for (unsigned lane = 0; lane < MAGE_T6_GROUP_SIZE; ++lane) {
                activations[group][token][lane] = activation_dist(rng);
                packed.range(8 * lane + 7, 8 * lane) = (ap_uint<8>)activations[group][token][lane];
            }
            activation_scales[group][token] = (half)(0.002f * (group + 1) * (token + 1));
            for (unsigned word = 0; word < 5; ++word) {
                mage_t6_axis128_t item;
                item.data = word < 4
                    ? packed.range(128 * word + 127, 128 * word)
                    : (ap_uint<128>)tb_half_bits(activation_scales[group][token]);
                item.keep = -1;
                item.strb = -1;
                item.last = group == input_groups - 1 &&
                            token == MAGE_T6_TOKENS - 1 &&
                            word == 4;
                tx.write(item);
            }
        }
    }

    ap_uint<128> memories[MAGE_T6_SHARDS][64];
    ap_int<5> signed_weights[MAGE_T6_SHARDS][input_groups][rows_per_shard][MAGE_T6_GROUP_SIZE];
    half weight_scales[MAGE_T6_SHARDS][input_groups][rows_per_shard];
    for (unsigned shard = 0; shard < MAGE_T6_SHARDS; ++shard) {
        for (unsigned group = 0; group < input_groups; ++group) {
            for (unsigned block = 0; block < blocks_per_group; ++block) {
                const unsigned base = group * blocks_per_group * block_words + block * block_words;
                ap_uint<128> scale_word = 0;
                ap_uint<512> pair_codes[4];
                for (unsigned slot = 0; slot < 4; ++slot) {
                    pair_codes[slot] = 0;
                    for (unsigned local_row = 0; local_row < 2; ++local_row) {
                        const unsigned row = block * 8 + slot * 2 + local_row;
                        const bool orientation = orientation_dist(rng);
                        const int qmin = -(1 << (bits - 1)) + (orientation ? 1 : 0);
                        weight_scales[shard][group][row] =
                            (half)(0.006f + 0.0005f * shard + 0.0003f * row + 0.0002f * group);
                        scale_word.range(16 * (slot * 2 + local_row) + 15, 16 * (slot * 2 + local_row)) =
                            tb_half_bits(weight_scales[shard][group][row]) | ((ap_uint<16>)orientation << 15);
                        for (unsigned lane = 0; lane < MAGE_T6_GROUP_SIZE; ++lane) {
                            const unsigned code = code_dist(rng);
                            tb_set_code(pair_codes[slot], local_row, lane, bits, code);
                            signed_weights[shard][group][row][lane] = (ap_int<5>)(qmin + (int)code);
                        }
                    }
                }
                memories[shard][base] = scale_word;
                for (unsigned slot = 0; slot < 4; ++slot) {
                    for (unsigned word = 0; word < 4; ++word) {
                        memories[shard][base + 1 + slot * bits + word] =
                            word < bits
                                ? pair_codes[slot].range(128 * word + 127, 128 * word)
                                : (ap_uint<128>)0;
                    }
                }
            }
        }
        for (unsigned word = shard_words; word < 64; ++word) memories[shard][word] = 0;
    }

    ap_uint<32> status = 0;
    ap_uint<32> build = 0;
    ap_uint<32> calls = 0;
    ap_uint<32> macros = 0;
    m75c_t6rt(
        tx, memories[0], memories[1], memories[2], memories[3], memories[4], memories[5],
        rx, input_groups, rows_per_shard, bits, status, build, calls, macros);
    const unsigned invocation = bits - 1;
    if (status != 0 || build != MAGE_T6C_BUILD_ID || calls != invocation ||
        macros != invocation * input_groups * rows_per_shard * MAGE_T6_SHARDS * MAGE_T6_TOKENS) {
        std::cerr << "counter/status failure bits=" << bits
                  << " status=" << status << " build=0x" << std::hex << build << std::dec
                  << " calls=" << calls << " macros=" << macros << std::endl;
        return 1;
    }

    for (unsigned token = 0; token < MAGE_T6_TOKENS; ++token) {
        for (unsigned shard = 0; shard < MAGE_T6_SHARDS; ++shard) {
            for (unsigned pair = 0; pair < rows_per_shard / 2; ++pair) {
                const mage_t6_axis64_t item = rx.read();
                for (unsigned local_row = 0; local_row < 2; ++local_row) {
                    const unsigned row = pair * 2 + local_row;
                    float expected = 0.0f;
                    for (unsigned group = 0; group < input_groups; ++group) {
                        int dot = 0;
                        for (unsigned lane = 0; lane < MAGE_T6_GROUP_SIZE; ++lane) {
                            dot += (int)activations[group][token][lane] *
                                   (int)signed_weights[shard][group][row][lane];
                        }
                        const ap_uint<16> dot_bits = tb_half_bits((half)dot);
                        const ap_uint<16> scaled =
                            mage_t6_half_mul_bits_rne(dot_bits, tb_half_bits(activation_scales[group][token]));
                        const ap_uint<16> weighted =
                            mage_t6_half_mul_bits_rne(scaled, tb_half_bits(weight_scales[shard][group][row]));
                        fp_struct<half> term(weighted);
                        expected += (float)term.to_half();
                    }
                    const ap_uint<32> actual_bits =
                        local_row == 0 ? item.data.range(31, 0) : item.data.range(63, 32);
                    if (actual_bits != tb_float_bits(expected)) {
                        std::cerr << "value failure bits=" << bits
                                  << " token=" << token << " shard=" << shard
                                  << " row=" << row << " actual=" << (unsigned)actual_bits
                                  << " expected=" << (unsigned)tb_float_bits(expected) << std::endl;
                        return 1;
                    }
                }
                const bool expected_last = token == MAGE_T6_TOKENS - 1 &&
                                           shard == MAGE_T6_SHARDS - 1 &&
                                           pair == rows_per_shard / 2 - 1;
                if ((bool)item.last != expected_last) {
                    std::cerr << "TLAST failure" << std::endl;
                    return 1;
                }
            }
        }
    }
    if (!rx.empty()) return 1;
    return 0;
}

int main() {
    for (unsigned bits = 2; bits <= 4; ++bits) {
        if (run_case(bits)) return 1;
    }
    std::cout << "MAGE_PREFILL_T6_RUNTIME_FULL_M75C_CSIM_PASS bits=2,3,4 input_groups=3 rows_per_shard=8 tokens=6 shards=6" << std::endl;
    return 0;
}
